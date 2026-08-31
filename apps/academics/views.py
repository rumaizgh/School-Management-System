from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import Batch, Fee, Payment, Mark, Institute, Exam
from .serializers import BatchSerializer,PaymentSerializer,FeeSerializer,MarkSerializer,InstituteSerializer, ExamSerializer, ExamAnalyticsSerializer, BulkMarkSerializer
from apps.account.serializers import UserDataSerializer
from apps.academics.serializers import TimeTableSerializer
from .permissions import IsAdmin,IsTeacher,IsTeacherOrAdmin
from django.shortcuts import get_object_or_404
from apps.account.filters import get_institute_scoped_object_or_404, InstituteFilterBackend
from rest_framework import status
from apps.account.models import UserData
from apps.academics.models import TimeTable
from apps.subject.models import Subject
from .resources import FeeResource, MarkResource
from django.http import HttpResponse
from django.db.models import Count, Q, Sum, Avg, Max, Min, F, Value, DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone
from apps.account.pagination import CustomPagination
from apps.notifications.services import (
    send_fee_assigned_notification,
    send_payment_success_notification,
    send_exam_scheduled_notification,
    send_marks_released_notification,
    send_timetable_updated_notification
)


class CreateClass(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsTeacherOrAdmin()]
        return [IsAdmin()]

    def post(self,request):
        serializer=BatchSerializer(data = request.data)
        if serializer.is_valid():
            serializer.save(institute=request.user.institute)
            return Response(serializer.data,  status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get(self,request,id=None):
        if id:
            batch = get_institute_scoped_object_or_404(Batch, request, id=id)
            serializer = BatchSerializer(batch)
            return Response(serializer.data)
        
        if request.user.user_type == 'teacher':
            batches = request.user.classs.all()
        else:
            batches = Batch.objects.all()
            
        batches = InstituteFilterBackend().filter_queryset(request, batches, None)
        serializer=BatchSerializer(batches,many=True)
        return Response(serializer.data)
    
    def patch(self,request,id):
        batch = get_institute_scoped_object_or_404(Batch, request, id=id)
        serializer=BatchSerializer(batch,data=request.data,partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors)
    
    def delete(self,request,id):
        batch = get_institute_scoped_object_or_404(Batch, request, id=id)
        batch.delete()
        return Response({"message": "Batch deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
    
class ViewAllClassTeacher(APIView):
    permission_classes=[IsTeacher]
    def get(self,request,id=None):
        teacher = request.user
        classs = Batch.objects.filter(subjects__teacher=teacher).distinct()
        serializer = BatchSerializer(classs,many=True)
        return Response(serializer.data)
    
def apply_user_filters_and_ordering(users, request):
    gender = request.GET.get('gender')
    if gender:
        users = users.filter(gender__iexact=gender)

    ordering = request.GET.get('ordering')
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
        users = users.order_by(ordering_map.get(ordering, ordering))
    else:
        users = users.order_by('-id')

    return users

class ViewStudentsByClass(APIView):
    def get(self, request, id):
        classs = get_institute_scoped_object_or_404(Batch, request, id=id)
        students = UserData.objects.filter(classs=classs, user_type="student", is_active=True)
        students = InstituteFilterBackend().filter_queryset(request, students, None)
        students = apply_user_filters_and_ordering(students, request)
        serializer = UserDataSerializer(students, many=True)
        return Response(serializer.data)

class ViewTeachersByClass(APIView):
    def get(self, request, id):
        classs = get_institute_scoped_object_or_404(Batch, request, id=id)
        teachers = UserData.objects.filter(classs=classs, user_type="teacher", is_active=True)
        teachers = InstituteFilterBackend().filter_queryset(request, teachers, None)
        teachers = apply_user_filters_and_ordering(teachers, request)
        serializer = UserDataSerializer(teachers, many=True)
        return Response(serializer.data)
     
class TimeTablesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id=None):
        user = request.user

        if id:
            user = get_institute_scoped_object_or_404(UserData, request, id=id)

        if user.user_type == 'teacher':
            if not user.is_active:
                return Response(
                    {"error": "Teacher account is inactive."},
                    status=status.HTTP_403_FORBIDDEN
                )
            timetables = TimeTable.objects.filter(teacher=user)

        elif user.user_type == 'student':
            if not user.is_active:
                return Response(
                    {"error": "Student account is inactive."},
                    status=status.HTTP_403_FORBIDDEN
                )
            student_classes = user.classs.all()

            if not student_classes.exists():
                return Response(
                    {"error": "No class assigned to this student."},
                    status=status.HTTP_404_NOT_FOUND
                )

            timetables = TimeTable.objects.filter(classs__in=student_classes)

        else:
            timetables = TimeTable.objects.all()

        is_exam = request.GET.get('is_exam')
        if is_exam is not None:
            is_exam_bool = is_exam.lower() in ['true', '1', 'yes']
            timetables = timetables.filter(is_exam=is_exam_bool)

        timetables = InstituteFilterBackend().filter_queryset(request, timetables, None)
        timetables = timetables.prefetch_related('sessions')
        serializer = TimeTableSerializer(timetables, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = TimeTableSerializer(data=request.data)
        if serializer.is_valid():
            timetable = serializer.save(institute=request.user.institute)
            send_timetable_updated_notification(timetable)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, id):
        timetable = get_institute_scoped_object_or_404(TimeTable, request, id=id)
        serializer = TimeTableSerializer(timetable, data=request.data, partial=True)
        if serializer.is_valid():
            timetable = serializer.save()
            send_timetable_updated_notification(timetable)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self,request,id):
        timetable = get_institute_scoped_object_or_404(TimeTable, request, id=id)
        timetable.delete()
        return Response({"message": "TimeTable deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
    
class PaymentListCreateAPIView(APIView):

    def get(self, request):
        student = request.GET.get('student')

        payments = Payment.objects.filter(fee__student__user_type="student")
        if student:
            payments = payments.filter(fee__student_id=student)

        payments = InstituteFilterBackend().filter_queryset(request, payments, None)
        serializer = PaymentSerializer(payments, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = PaymentSerializer(data=request.data)
        if serializer.is_valid():
            # Secure validation: verify fee belongs to the requesting user's institute
            fee = get_institute_scoped_object_or_404(Fee, request, id=serializer.validated_data['fee'].id)
            payment = serializer.save()

            fee = payment.fee
            total_paid = sum(p.amount for p in fee.payments.all())

            fee.paid_amount = total_paid
            fee.balance_amount = fee.amount - total_paid
            fee.paid = total_paid >= fee.amount
            fee.save()

            send_payment_success_notification(payment)

            return Response(serializer.data, status=201)

        return Response(serializer.errors, status=400)
    
def apply_fee_filters_and_ordering(fees, request):
    gender = request.GET.get('gender')
    if gender:
        fees = fees.filter(student__gender__iexact=gender)

    status_param = request.GET.get('status')
    if status_param:
        fees = fees.annotate(
            total_paid_sum=Coalesce(
                Sum('payments__amount'),
                Value(0, output_field=DecimalField(max_digits=10, decimal_places=2))
            )
        )
        today = timezone.localdate()
        status_lower = status_param.lower()
        if status_lower == 'paid':
            fees = fees.filter(total_paid_sum__gte=F('amount'))
        elif status_lower == 'overdue':
            fees = fees.filter(total_paid_sum__lt=F('amount'), due_date__lt=today)
        elif status_lower == 'pending':
            fees = fees.filter(total_paid_sum__lt=F('amount'), due_date__gte=today)

    ordering = request.GET.get('ordering')
    if ordering:
        ordering_map = {
            'amount': 'amount',
            '-amount': '-amount',
            'name': 'student__name',
            '-name': '-student__name',
            'first_name': 'student__name',
            '-first_name': '-student__name',
            'created_at': 'id',
            '-created_at': '-id',
            'id': 'id',
            '-id': '-id',
            'due_date': 'due_date',
            '-due_date': '-due_date',
        }
        fees = fees.order_by(ordering_map.get(ordering, ordering))
    else:
        fees = fees.order_by('-id')

    return fees


class FeeListCreateAPIView(APIView):

    def get(self, request, id=None):
        if id:
            fees = get_institute_scoped_object_or_404(Fee, request, id=id, student__user_type="student")
            serializer = FeeSerializer(fees)
            return Response(serializer.data)
        fees = Fee.objects.all()
        fees = InstituteFilterBackend().filter_queryset(request, fees, None)
        fees = apply_fee_filters_and_ordering(fees, request)
        serializer = FeeSerializer(fees, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = FeeSerializer(data=request.data)
        if serializer.is_valid():
            fee = serializer.save(institute=request.user.institute)

            if fee.student.user_type != "student":
                return Response(
                    {"error": "Fee can be created only for students"},status=400)

            send_fee_assigned_notification(fee)

            return Response(serializer.data, status=201)

        return Response(serializer.errors, status=400)
    
    def patch(self, request, id):
        fee = get_institute_scoped_object_or_404(Fee, request, id=id)
        serializer = FeeSerializer(fee, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class ViewFee(APIView):
    def get(self, request, classs_id):
        fees = Fee.objects.filter(batch=classs_id)
        fees = InstituteFilterBackend().filter_queryset(request, fees, None)
        fees = apply_fee_filters_and_ordering(fees, request)

        if not fees.exists():
            return Response(
                {"message": "No fees found for this class"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = FeeSerializer(fees, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class CreatePayment(APIView):
    def get(self, request, student_id=None):
        if student_id:
            payments = Payment.objects.filter(
                fee__student_id=student_id
            ).order_by("-id")
        else:
            payments = Payment.objects.all().order_by("-id")

        payments = InstituteFilterBackend().filter_queryset(request, payments, None)
        paginator = CustomPagination()
        paginated_payments = paginator.paginate_queryset(payments, request)

        serializer = PaymentSerializer(paginated_payments, many=True)
        return paginator.get_paginated_response(serializer.data)
    
    def post(self, request):
        serializer = PaymentSerializer(data=request.data)

        if serializer.is_valid():
            # Secure validation: verify fee belongs to the requesting user's institute
            fee = get_institute_scoped_object_or_404(Fee, request, id=serializer.validated_data['fee'].id)
            amount = serializer.validated_data['amount']

            if amount > fee.balance():
                return Response(
                    {"error": "Amount exceeds remaining balance"},
                    status=400
                )

            payment = serializer.save()
            send_payment_success_notification(payment)
            return Response(serializer.data, status=201)

        return Response(serializer.errors, status=400)
    
class ViewFeeByStudent(APIView):
    def get(self, request, student_id=None):
        if student_id:
            fees = Fee.objects.filter(
                student_id=student_id,
                student__user_type="student"
            )
        else:
            fees = Fee.objects.all()

        fees = InstituteFilterBackend().filter_queryset(request, fees, None)
        fees = apply_fee_filters_and_ordering(fees, request)
        serializer = FeeSerializer(fees, many=True, context={'request': request})
        return Response(serializer.data)

class LatestAssignedFeesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get all students with assigned fees paginated"""
        fees = Fee.objects.filter(student__user_type="student").select_related('student', 'batch')
        fees = InstituteFilterBackend().filter_queryset(request, fees, None)
        fees = fees.order_by('-id')

        paginator = CustomPagination()
        paginated_fees = paginator.paginate_queryset(fees, request)
        serializer = FeeSerializer(paginated_fees, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

class ExportFee(APIView):
    def get(self, request):
        batch_id = request.GET.get('batch_id')
        fees = Fee.objects.all()

        if batch_id:
            fees = fees.filter(batch_id=batch_id)
            
        fees = InstituteFilterBackend().filter_queryset(request, fees, None)
        dataset = FeeResource().export(queryset=fees)

        response = HttpResponse(
            dataset.export('xlsx'),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

        filename = f"fees_batch_{batch_id}.xlsx" if batch_id else "fees_all.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response
    
class FeeExportPreview(APIView):
    def get(self, request):
        batch_id = request.GET.get('batch_id')
        fees = Fee.objects.select_related(
            'student',
            'batch'
        ).all()

        if batch_id:
            fees = fees.filter(batch_id=batch_id)

        fees = InstituteFilterBackend().filter_queryset(request, fees, None)
        resource = FeeResource()
        dataset = resource.export(queryset=fees)

        return Response({
            "status": True,
            "count": fees.count(),
            "data": dataset.dict
        })

class ExportMark(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, exam_id=None):
        exam_id = exam_id or request.GET.get('exam_id')
        batch_id = request.GET.get('batch_id')
        subject_id = request.GET.get('subject_id')
        file_format = request.GET.get('format', 'xlsx').lower()

        marks = Mark.objects.select_related('exam', 'student', 'exam__batch', 'exam__subject').all()

        if exam_id:
            marks = marks.filter(exam_id=exam_id)
        if batch_id:
            marks = marks.filter(exam__batch_id=batch_id)
        if subject_id:
            marks = marks.filter(exam__subject_id=subject_id)

        marks = InstituteFilterBackend().filter_queryset(request, marks, None)
        dataset = MarkResource().export(queryset=marks)

        if file_format == 'csv':
            content_type = 'text/csv'
            export_data = dataset.export('csv')
            ext = 'csv'
        else:
            content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            export_data = dataset.export('xlsx')
            ext = 'xlsx'

        response = HttpResponse(export_data, content_type=content_type)
        if exam_id:
            exam_obj = Exam.objects.filter(id=exam_id).first()
            if exam_obj and exam_obj.exam_name:
                safe_exam_name = "".join(c if c.isalnum() or c in ('_', '-') else '_' for c in exam_obj.exam_name.strip())
                filename = f"marklist_{safe_exam_name}.{ext}"
            else:
                filename = f"marklist_exam_{exam_id}.{ext}"
        elif batch_id:
            filename = f"marklist_batch_{batch_id}.{ext}"
        else:
            filename = f"marklist_all.{ext}"

        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class MarkExportPreview(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, exam_id=None):
        exam_id = exam_id or request.GET.get('exam_id')
        batch_id = request.GET.get('batch_id')
        subject_id = request.GET.get('subject_id')

        marks = Mark.objects.select_related('exam', 'student', 'exam__batch', 'exam__subject').all()

        if exam_id:
            marks = marks.filter(exam_id=exam_id)
        if batch_id:
            marks = marks.filter(exam__batch_id=batch_id)
        if subject_id:
            marks = marks.filter(exam__subject_id=subject_id)

        marks = InstituteFilterBackend().filter_queryset(request, marks, None)
        resource = MarkResource()
        dataset = resource.export(queryset=marks)

        return Response({
            "status": True,
            "count": marks.count(),
            "data": dataset.dict
        })

class SearchPaymentHistory(APIView):

    def get(self, request, id=None):
        q = request.GET.get('q')
        if q:
            payments = Payment.objects.filter(
                fee__student__name__icontains=q
            ).order_by('-id')
            payments = InstituteFilterBackend().filter_queryset(request, payments, None)
            serializer = PaymentSerializer(payments, many=True)
            return Response(serializer.data, status=200)

        if id is None:
            return Response({"detail": "Payment id is required unless q is provided."}, status=400)

        payment = get_institute_scoped_object_or_404(Payment, request, id=id)
        serializer = PaymentSerializer(payment)
        return Response(serializer.data, status=200)


class MarkListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id=None):
        """Get all marks or a specific mark by id"""
        if id:
            mark = get_institute_scoped_object_or_404(Mark, request, id=id)
            serializer = MarkSerializer(mark, context={'request': request})
            return Response(serializer.data)
        
        marks = Mark.objects.all().order_by('-id')
        marks = InstituteFilterBackend().filter_queryset(request, marks, None)
        serializer = MarkSerializer(marks, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request):
        """Create a new mark"""
        serializer = MarkSerializer(data=request.data)
        if serializer.is_valid():
            # Validate that the student and exam belong to the same institute
            student = get_institute_scoped_object_or_404(UserData, request, id=serializer.validated_data['student'].id, user_type='student')
            exam = get_institute_scoped_object_or_404(Exam, request, id=serializer.validated_data['exam'].id)
            mark = serializer.save()
            send_marks_released_notification(mark)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MarkUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, id):
        """Update a mark (partial update)"""
        mark = get_institute_scoped_object_or_404(Mark, request, id=id)
        serializer = MarkSerializer(mark, data=request.data, partial=True)
        if serializer.is_valid():
            updated_mark = serializer.save()
            send_marks_released_notification(updated_mark)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, id):
        """Update a mark (full update)"""
        mark = get_institute_scoped_object_or_404(Mark, request, id=id)
        serializer = MarkSerializer(mark, data=request.data)
        if serializer.is_valid():
            updated_mark = serializer.save()
            send_marks_released_notification(updated_mark)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id):
        """Delete a mark"""
        mark = get_institute_scoped_object_or_404(Mark, request, id=id)
        mark.delete()
        return Response({"message": "Mark deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


class MarkByStudentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, student_id):
        """Get all marks for a specific student"""
        # Students can only view their own marks
        if request.user.user_type == 'student' and request.user.id != student_id:
            return Response({"error": "You can only view your own marks"}, status=status.HTTP_403_FORBIDDEN)

        # Validate that the student exists in the requesting user's institute scope
        student = get_institute_scoped_object_or_404(UserData, request, id=student_id, user_type='student')
        marks = Mark.objects.filter(student=student).order_by('-id')
        marks = InstituteFilterBackend().filter_queryset(request, marks, None)

        if not marks.exists():
            return Response(
                {"message": "No marks found for this student"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = MarkSerializer(marks, many=True, context={'request': request})
        return Response(serializer.data)


class MarkBySubjectAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, subject_id):
        """Get all marks for a specific subject"""
        # Validate subject scope
        subject = get_institute_scoped_object_or_404(Subject, request, id=subject_id)
        marks = Mark.objects.filter(subject=subject).order_by('-id')
        marks = InstituteFilterBackend().filter_queryset(request, marks, None)
        
        if not marks.exists():
            return Response(
                {"message": "No marks found for this subject"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = MarkSerializer(marks, many=True, context={'request': request})
        return Response(serializer.data)


class InstituteView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, id=None):
        """Get all institutes or a specific institute by id"""
        if id:
            institute = get_institute_scoped_object_or_404(Institute, request, id=id)
            serializer = InstituteSerializer(institute)
            return Response(serializer.data)
        
        institutes = Institute.objects.all()
        institutes = InstituteFilterBackend().filter_queryset(request, institutes, None)
        serializer = InstituteSerializer(institutes, many=True)
        return Response(serializer.data)

    def post(self, request):
        """Create a new institute"""
        # Allow superusers to create institutes
        if not request.user.is_superuser:
            return Response({"error": "Only superusers can create new institutes."}, status=status.HTTP_403_FORBIDDEN)
        serializer = InstituteSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, id):
        """Update an institute (partial update)"""
        institute = get_institute_scoped_object_or_404(Institute, request, id=id)
        serializer = InstituteSerializer(institute, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, id):
        """Update an institute (full update)"""
        institute = get_institute_scoped_object_or_404(Institute, request, id=id)
        serializer = InstituteSerializer(institute, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id):
        """Delete an institute"""
        # Allow superusers to delete institutes
        if not request.user.is_superuser:
            return Response({"error": "Only superusers can delete institutes."}, status=status.HTTP_403_FORBIDDEN)
        institute = get_institute_scoped_object_or_404(Institute, request, id=id)
        institute.delete()
        return Response({"message": "Institute deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

class ExamListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request, id=None):
        if id:
            exam = get_institute_scoped_object_or_404(Exam, request, id=id, is_deleted=False)
            serializer = ExamSerializer(exam)
            return Response(serializer.data)
        user = request.user
        exams = Exam.objects.filter(is_deleted=False).order_by('-id')
        exams = InstituteFilterBackend().filter_queryset(request, exams, None)
        
        if user.user_type == 'teacher':
            exams = exams.filter(subject__teacher=user)
        # elif user.user_type == 'student':
        #     student_classes = user.classs.all()
        #     exams = exams.filter(batch__in=student_classes)
        batch_id = request.GET.get('batch_id')
        subject_id = request.GET.get('subject_id')
        if batch_id:
            exams = exams.filter(batch_id=batch_id)
        if subject_id:
            exams = exams.filter(subject_id=subject_id)
            
        serializer = ExamSerializer(exams, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ExamSerializer(data=request.data)
        if serializer.is_valid():
            exam = serializer.save(institute=request.user.institute)
            send_exam_scheduled_notification(exam)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, id):
        exam = get_institute_scoped_object_or_404(Exam, request, id=id, is_deleted=False)
        serializer = ExamSerializer(exam, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id):
        exam = get_institute_scoped_object_or_404(Exam, request, id=id, is_deleted=False)
        exam.is_deleted = True
        exam.save()
        return Response({"message": "Exam deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

class ExamAnalyticsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, exam_id):
        exam = get_institute_scoped_object_or_404(Exam, request, id=exam_id, is_deleted=False)
        marks = Mark.objects.filter(exam=exam)
        marks = InstituteFilterBackend().filter_queryset(request, marks, None)
        
        total_students = marks.count()
        if total_students == 0:
            return Response({
                "exam_id": exam.id,
                "total_students_attended": 0,
                "highest_mark": None,
                "top_scorer_name": None,
                "lowest_mark": None,
                "average_mark": None,
                "pass_mark": exam.pass_mark,
                "pass_percentage": 0.0
            })
            
        highest_mark = marks.order_by('-obtained_mark').first()
        lowest_mark = marks.order_by('obtained_mark').first()
        average_mark = marks.aggregate(avg=Sum('obtained_mark'))['avg'] / total_students if total_students > 0 else 0
        
        passed_students = marks.filter(obtained_mark__gte=exam.pass_mark).count()
        pass_percentage = (passed_students / total_students) * 100 if total_students > 0 else 0
        
        if highest_mark:
            top_scorers = marks.filter(obtained_mark=highest_mark.obtained_mark)
            top_scorer_names = ", ".join([m.student.name for m in top_scorers])
        else:
            top_scorer_names = None
            
        data = {
            "exam_id": exam.id,
            "total_students_attended": total_students,
            "highest_mark": highest_mark.obtained_mark if highest_mark else None,
            "top_scorer_name": top_scorer_names,
            "lowest_mark": lowest_mark.obtained_mark if lowest_mark else None,
            "average_mark": round(average_mark, 2),
            "pass_mark": exam.pass_mark,
            "pass_percentage": round(pass_percentage, 2)
        }
        serializer = ExamAnalyticsSerializer(data)
        return Response(serializer.data)


class ExamMarksAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, exam_id):
        exam = get_institute_scoped_object_or_404(Exam, request, id=exam_id, is_deleted=False)
        marks = Mark.objects.filter(exam=exam)
        marks = InstituteFilterBackend().filter_queryset(request, marks, None)
        serializer = MarkSerializer(marks, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request, exam_id):
        exam = get_institute_scoped_object_or_404(Exam, request, id=exam_id, is_deleted=False)
        serializer = BulkMarkSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        marks_data = serializer.validated_data.get('marks', [])
        
        for item in marks_data:
            student_id = item.get('student_id')
            obtained = item.get('obtained_mark')
            
            student = get_institute_scoped_object_or_404(UserData, request, id=student_id, user_type='student')
            
            mark, created = Mark.objects.get_or_create(
                exam=exam,
                student=student,
                defaults={
                    'obtained_mark': obtained if obtained is not None else 0
                }
            )
            
            if not created:
                mark.obtained_mark = obtained if obtained is not None else 0
                mark.save()

            send_marks_released_notification(mark)

        return Response({"message": "Marks successfully updated."}, status=status.HTTP_200_OK)


class StudentExamListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        student = request.user
        if student.user_type == 'student':
            student_batches = student.classs.all()
            exams = Exam.objects.filter(batch__in=student_batches, is_deleted=False).order_by('-id')
        else:
            exams = Exam.objects.filter(is_deleted=False).order_by('-id')

        exams = InstituteFilterBackend().filter_queryset(request, exams, None)

        results = []
        for exam in exams:
            mark = Mark.objects.filter(exam=exam, student=student).first()

            obtained_mark = float(mark.obtained_mark) if (mark and mark.obtained_mark is not None) else None
            total_mark = float(exam.total_mark)
            pass_mark = float(exam.pass_mark)

            if mark and mark.obtained_mark is not None:
                is_pass = bool(mark.obtained_mark >= exam.pass_mark)
                status_str = "published"
            else:
                is_pass = False
                status_str = "Pending"

            date_str = exam.timetable.date.strftime('%Y-%m-%d') if (exam.timetable and exam.timetable.date) else None

            results.append({
                "exam_id": exam.id,
                "exam_name": exam.exam_name,
                "subject_name": exam.subject.subject_name if exam.subject else None,
                "date": date_str,
                "total_mark": total_mark,
                "obtained_mark": obtained_mark,
                "pass_mark": pass_mark,
                "is_pass": is_pass,
                "status": status_str
            })

        return Response({"results": results})


class StudentExamAnalyticsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, exam_id):
        student = request.user
        exam = get_institute_scoped_object_or_404(Exam, request, id=exam_id, is_deleted=False)
        
        mark = Mark.objects.filter(exam=exam, student=student).first()

        obtained_mark = float(mark.obtained_mark) if (mark and mark.obtained_mark is not None) else None
        total_mark = float(exam.total_mark)
        pass_mark = float(exam.pass_mark)
        is_pass = bool(mark.obtained_mark >= exam.pass_mark) if (mark and mark.obtained_mark is not None) else False

        all_marks = Mark.objects.filter(exam=exam)
        total_students = all_marks.count()

        if total_students > 0:
            avg_val = all_marks.aggregate(avg=Avg('obtained_mark'))['avg']
            max_val = all_marks.aggregate(max=Max('obtained_mark'))['max']
            min_val = all_marks.aggregate(min=Min('obtained_mark'))['min']
            passed_count = all_marks.filter(obtained_mark__gte=exam.pass_mark).count()

            average_mark = round(float(avg_val), 1) if avg_val is not None else 0.0
            highest_mark = round(float(max_val), 1) if max_val is not None else 0.0
            lowest_mark = round(float(min_val), 1) if min_val is not None else 0.0
            pass_percentage = round((passed_count / total_students) * 100, 1)
        else:
            average_mark = 0.0
            highest_mark = 0.0
            lowest_mark = 0.0
            pass_percentage = 0.0

        return Response({
            "exam_id": exam.id,
            "obtained_mark": obtained_mark,
            "total_mark": total_mark,
            "is_pass": is_pass,
            "class_analytics": {
                "average_mark": average_mark,
                "highest_mark": highest_mark,
                "lowest_mark": lowest_mark,
                "pass_percentage": pass_percentage
            }
        })