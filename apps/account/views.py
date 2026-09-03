from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from apps.account.filters import get_institute_scoped_object_or_404, InstituteFilterBackend
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from apps.academics.models import Batch
from apps.subject.models import Subject
from .serializers import UserDataSerializer, UserCreateSerializer
from apps.academics.serializers import BatchSerializer
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import UserData
from apps.academics.permissions import IsAdmin,IsTeacherOrAdmin
from rest_framework.generics import ListAPIView
from .pagination import CustomPagination
from django.db.models import Count, Q
from .resources import UserDataResource
from apps.notifications.models import NotificationHistory

class DashboardCountAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        institute = user.institute

        if user.is_superuser and not institute:
            user_counts = UserData.objects.aggregate(
                total_students=Count('id', filter=Q(user_type='student', is_active=True)),
                total_teachers=Count('id', filter=Q(user_type='teacher', is_active=True)),
            )
            class_count = Batch.objects.count()
            subject_count = Subject.objects.count()
        else:
            user_counts = UserData.objects.filter(institute=institute).aggregate(
                total_students=Count('id', filter=Q(user_type='student', is_active=True)),
                total_teachers=Count('id', filter=Q(user_type='teacher', is_active=True)),
            )
            class_count = Batch.objects.filter(institute=institute).count()
            subject_count = Subject.objects.filter(institute=institute).count()

        unread_count = NotificationHistory.objects.filter(user=user, is_read=False).count()

        return Response({
            "status": True,
            "data": {
                "students": user_counts['total_students'],
                "teachers": user_counts['total_teachers'],
                "classes": class_count,
                "subjects": subject_count,
                "unread_count": unread_count
            }
        })


class TeacherDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        institute = getattr(user, 'institute', None)

        # Unread notification count for the logged-in teacher
        unread_count = NotificationHistory.objects.filter(user=user, is_read=False).count()

        # Teacher specific metrics
        if user.user_type == 'teacher':
            assigned_subjects = Subject.objects.filter(teacher=user)
            if institute:
                assigned_subjects = assigned_subjects.filter(institute=institute)
            subject_count = assigned_subjects.count()

            assigned_batches = Batch.objects.filter(subjects__teacher=user).distinct()
            if institute:
                assigned_batches = assigned_batches.filter(institute=institute)
            class_count = assigned_batches.count()

            student_qs = UserData.objects.filter(
                user_type='student',
                is_active=True,
                classs__in=assigned_batches
            ).distinct()
            if institute:
                student_qs = student_qs.filter(institute=institute)
            student_count = student_qs.count()
        else:
            if user.is_superuser and not institute:
                student_count = UserData.objects.filter(user_type='student', is_active=True).count()
                class_count = Batch.objects.count()
                subject_count = Subject.objects.count()
            else:
                student_count = UserData.objects.filter(institute=institute, user_type='student', is_active=True).count()
                class_count = Batch.objects.filter(institute=institute).count()
                subject_count = Subject.objects.filter(institute=institute).count()

        return Response({
            "status": True,
            "data": {
                "unread_count": unread_count,
                "total_students": student_count,
                "total_classes": class_count,
                "total_subjects": subject_count,
            }
        }, status=status.HTTP_200_OK)

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        user = authenticate(request, email=email, password=password)

        if user is None:
            return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return Response({"detail": "User account is disabled."}, status=status.HTTP_403_FORBIDDEN)

        user_role = user.user_type 

        refresh = RefreshToken.for_user(user)
        # Bind user's institute and user_type to JWT custom claims
        refresh['institute_id'] = user.institute.id if user.institute else None
        refresh['user_type'] = user.user_type
        
        user_data = UserDataSerializer(user).data

        return Response({
            'user': user_data,
            'role': user_role,
            'refresh': str(refresh),
            'access': str(refresh.access_token)
        })

class ViewAllTeachers(ListAPIView):
    serializer_class = UserDataSerializer
    permission_classes = [IsAuthenticated]
    # Disable pagination so the JS client receives a plain array
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        queryset = UserData.objects.filter(user_type='teacher', is_active=True)
        queryset = InstituteFilterBackend().filter_queryset(self.request, queryset, self)

        # Scope to the requesting admin's institute
        if not user.is_superuser and user.institute:
            queryset = queryset.filter(institute=user.institute)

        id = self.kwargs.get('id')
        if id:
            queryset = queryset.filter(id=id)

        gender = self.request.GET.get('gender')
        if gender:
            queryset = queryset.filter(gender__iexact=gender)

        ordering = self.request.GET.get('ordering')
        if ordering:
            ordering_map = {
                'created_at': 'date_joined',
                '-created_at': '-date_joined',
                'name': 'name',
                '-name': '-name',
                'first_name': 'name',
                '-first_name': '-name',
                'id': 'id',
                '-id': '-id',
            }
            queryset = queryset.order_by(ordering_map.get(ordering, ordering))
        else:
            queryset = queryset.order_by('-id')

        return queryset

class ViewAllStudents(ListAPIView):
    serializer_class = UserDataSerializer
    permission_classes = [IsAuthenticated]
    # Disable pagination so the JS client receives a plain array
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        queryset = UserData.objects.filter(user_type='student', is_active=True)
        queryset = InstituteFilterBackend().filter_queryset(self.request, queryset, self)

        # Scope to the requesting admin's institute
        if not user.is_superuser and user.institute:
            queryset = queryset.filter(institute=user.institute)

        id = self.kwargs.get('id')
        if id:
            queryset = queryset.filter(id=id)

        gender = self.request.GET.get('gender')
        if gender:
            queryset = queryset.filter(gender__iexact=gender)

        ordering = self.request.GET.get('ordering')
        if ordering:
            ordering_map = {
                'created_at': 'date_joined',
                '-created_at': '-date_joined',
                'name': 'name',
                '-name': '-name',
                'first_name': 'name',
                '-first_name': '-name',
                'id': 'id',
                '-id': '-id',
            }
            queryset = queryset.order_by(ordering_map.get(ordering, ordering))
        else:
            queryset = queryset.order_by('-id')

        return queryset
    
class CreateStudent(APIView):
    permission_classes = [IsAuthenticated,IsAdmin]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self,request):
        user = request.user
        if user.is_superuser and not user.institute:
            batches = Batch.objects.all()
        else:
            batches = Batch.objects.filter(institute=user.institute)
            
        serializer = BatchSerializer(batches, many=True)
        return Response({"batches": serializer.data})

    def post(self,request):
        serializer = UserCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user_type="student", institute=request.user.institute)
            return Response(serializer.data,  status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)  
    
    def patch(self, request, id):
        user = get_institute_scoped_object_or_404(UserData, request, id=id, user_type="student")

        serializer = UserCreateSerializer(
            user,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors)
    
    def delete(self, request, id):
        user = get_institute_scoped_object_or_404(UserData, request, id=id, user_type="student")

        if not user.is_active:
            return Response(
                {"error": "Student already deactivated"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.is_active = False
        user.save(update_fields=["is_active"])

        return Response(
            {"message": "Student deactivated successfully"},
            status=status.HTTP_200_OK
        )
    
class CreateTeacher(APIView):
    permission_classes = [IsAuthenticated,IsAdmin]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def post(self,request):
        serializer = UserCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user_type="teacher", institute=request.user.institute)
            return Response(serializer.data,  status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)   
    
    def patch(self, request, id):
        user = get_institute_scoped_object_or_404(UserData, request, id=id, user_type="teacher")

        serializer = UserCreateSerializer(
            user,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors)
    
    def delete(self, request, id):
        user = get_institute_scoped_object_or_404(UserData, request, id=id, user_type="teacher")

        if not user.is_active:
            return Response(
                {"error": "Student already deactivated"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.is_active = False
        user.save(update_fields=["is_active"])

        return Response(
            {"message": "Student deactivated successfully"},
            status=status.HTTP_200_OK
        )
    
class SearchStudent(ListAPIView):
    serializer_class = UserDataSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        query = self.request.GET.get("q", "")
        qs = UserData.objects.filter(
            Q(name__icontains=query) |
            Q(email__icontains=query) |
            Q(phone__icontains=query) |
            Q(roll_no__icontains=query),
            user_type="student",
            is_active=True
        )
        return InstituteFilterBackend().filter_queryset(self.request, qs, None)
    
class SearchTeacher(ListAPIView):
    serializer_class = UserDataSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        query = self.request.GET.get("q", "")
        qs = UserData.objects.filter(
            Q(name__icontains=query) |
            Q(email__icontains=query) |
            Q(phone__icontains=query),
            user_type="teacher",
            is_active=True
        )
        return InstituteFilterBackend().filter_queryset(self.request, qs, None)


class ExportTeachers(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        teachers = UserData.objects.filter(user_type='teacher', is_active=True).prefetch_related('subject', 'classs', 'institute')
        teachers = InstituteFilterBackend().filter_queryset(request, teachers, None)

        resource = UserDataResource()
        dataset = resource.export(queryset=teachers)

        response = HttpResponse(
            dataset.export('xlsx'),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="teachers.xlsx"'
        return response


class ExportStudents(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        batch_id = request.GET.get('batch_id') or request.GET.get('class_id')
        students = UserData.objects.filter(user_type='student', is_active=True).prefetch_related('subject', 'classs', 'institute')

        if batch_id:
            students = students.filter(classs__id=batch_id)

        students = InstituteFilterBackend().filter_queryset(request, students, None)

        resource = UserDataResource()
        dataset = resource.export(queryset=students)

        response = HttpResponse(
            dataset.export('xlsx'),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        filename = f"students_batch_{batch_id}.xlsx" if batch_id else "students.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
