from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
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

class DashboardCountAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_counts = UserData.objects.aggregate(
            total_students=Count('id', filter=Q(user_type='student', is_active=True)),
            total_teachers=Count('id', filter=Q(user_type='teacher', is_active=True)),
        )

        class_count = Batch.objects.count()
        subject_count = Subject.objects.count()

        return Response({
            "status": True,
            "data": {
                "students": user_counts['total_students'],
                "teachers": user_counts['total_teachers'],
                "classes": class_count,
                "subjects": subject_count
            }
        })

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
        user_data = UserDataSerializer(user).data

        return Response({
            'user': user_data,
            'role': user_role,
            'refresh': str(refresh),
            'access': str(refresh.access_token)
        })

class ViewAllTeachers(APIView):
    permission_classes = [AllowAny]

    def get(self,request, id=None):
        if id:
            teachers = UserData.objects.filter(user_type='teacher',id = id, is_active = True)
            serializer = UserDataSerializer(teachers, many = True)
            return Response(serializer.data)
        teachers = UserData.objects.filter(user_type = 'teacher', is_active = True)
        serializer = UserDataSerializer(teachers, many = True)
        return Response(serializer.data)
    
class ViewAllStudents(ListAPIView):
    serializer_class = UserDataSerializer
    pagination_class = CustomPagination

    def get_queryset(self):
        return UserData.objects.filter(user_type='student', is_active=True)
    
class CreateStudent(APIView):
    permission_classes = [IsAuthenticated,IsAdmin]

    def get(self,request):
        batches = Batch.objects.all()
        serializer = BatchSerializer(batches, many=True)
        return Response({"batches": serializer.data})

    def post(self,request):
        serializer = UserCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data,  status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)  
    
    def patch(self, request, id):
        user = get_object_or_404(UserData, id=id, user_type="student")

        serializer = UserDataSerializer(
            user,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors)
    
    def delete(self, request, id):
        user = get_object_or_404(UserData, id=id, user_type="student")

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
    
    def post(self,request):
        serializer = UserCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user_type="teacher")
            return Response(serializer.data,  status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)   
    
    def patch(self, request, id):
        user = get_object_or_404(UserData, id=id, user_type="teacher")

        serializer = UserDataSerializer(
            user,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors)
    
    def delete(self, request, id):
        user = get_object_or_404(UserData, id=id, user_type="teacher")

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