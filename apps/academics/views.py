from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import Batch, Fee, Payment
from .serializers import BatchSerializer,PaymentSerializer,FeeSerializer
from apps.account.serializers import UserDataSerializer
from apps.academics.serializers import TimeTableSerializer
from .permissions import IsAdmin,IsTeacher
from django.shortcuts import get_object_or_404
from rest_framework import status
from apps.account.models import UserData
from apps.academics.models import TimeTable
from apps.subject.models import Subject
from .resources import FeeResource
from django.http import HttpResponse
from django.db.models import Count, Q, Sum
from apps.account.pagination import CustomPagination


class CreateClass(APIView):
    permission_classes=[IsAdmin]    

    def post(self,request):
        serializer=BatchSerializer(data = request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data,  status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get(self,request,id=None):
        if id:
            batch=get_object_or_404(Batch, id=id)
            serializer = BatchSerializer(batch)
            return Response(serializer.data)
        
        batches=Batch.objects.all()
        serializer=BatchSerializer(batches,many=True)
        return Response(serializer.data)
    
    def patch(self,request,id):
        batch=get_object_or_404(Batch,id=id)
        serializer=BatchSerializer(batch,data=request.data,partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors)
    
    def delete(self,request,id):
        batch = get_object_or_404(Batch,id=id)
        batch.delete()
        return Response({"message": "Batch deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
    
class ViewAllClassTeacher(APIView):
    permission_classes=[IsTeacher]
    def get(self,request,id=None):
        teacher = request.user
        classs = Batch.objects.filter(subjects__teacher=teacher).distinct()
        serializer = BatchSerializer(classs,many=True)
        return Response(serializer.data)
    
class ViewStudentsByClass(APIView):
    def get(self, request, id):
        classs = get_object_or_404(Batch,id=id)
        students = UserData.objects.filter(classs=classs, user_type="student", is_active = True)
        serializer = UserDataSerializer(students, many=True)
        return Response(serializer.data)
    
class ViewTeachersByClass(APIView):
    def get(self, request, id):
        classs = get_object_or_404(Batch,id=id)
        teachers = UserData.objects.filter(classs=classs, user_type="teacher", is_active = True)
        serializer = UserDataSerializer(teachers, many=True)
        return Response(serializer.data)
     
class TimeTablesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id=None):
        user = request.user

        if id:
            user = get_object_or_404(UserData, id=id)

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

        serializer = TimeTableSerializer(timetables, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = TimeTableSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data,  status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, id):
        timetable=get_object_or_404(TimeTable,id=id)
        serializer = TimeTableSerializer(timetable, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self,request,id):
        timetable = get_object_or_404(TimeTable,id=id)
        timetable.delete()
        return Response({"message": "TimeTable deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
    
class PaymentListCreateAPIView(APIView):

    def get(self, request):
        student = request.GET.get('student')

        payments = Payment.objects.filter(fee__student__user_type="student")

        if student:
            payments = payments.filter(fee__student_id=student)

        serializer = PaymentSerializer(payments, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = PaymentSerializer(data=request.data)
        if serializer.is_valid():
            payment = serializer.save()

            fee = payment.fee
            total_paid = sum(p.amount for p in fee.payments.all())

            fee.paid_amount = total_paid
            fee.balance_amount = fee.amount - total_paid
            fee.paid = total_paid >= fee.amount
            fee.save()

            return Response(serializer.data, status=201)

        return Response(serializer.errors, status=400)
    
class FeeListCreateAPIView(APIView):

    def get(self, request, id=None):
        if id:
            fees = Fee.objects.get(id=id,student__user_type="student")
            serializer = FeeSerializer(fees)
            return Response(serializer.data)
        fees = Fee.objects.all().order_by("-id")
        serializer = FeeSerializer(fees, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = FeeSerializer(data=request.data)
        if serializer.is_valid():
            fee = serializer.save()

            if fee.student.user_type != "student":
                return Response(
                    {"error": "Fee can be created only for students"},status=400)

            return Response(serializer.data, status=201)

        return Response(serializer.errors, status=400)
    
    def patch(self, request, id):
        fee=get_object_or_404(Fee,id=id)
        serializer = FeeSerializer(fee, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class ViewFee(APIView):
    def get(self, request, classs_id):
        fees = Fee.objects.filter(batch=classs_id)

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

        paginator = CustomPagination()
        paginated_payments = paginator.paginate_queryset(payments, request)

        serializer = PaymentSerializer(paginated_payments, many=True)
        return paginator.get_paginated_response(serializer.data)
    
    def post(self, request):
        serializer = PaymentSerializer(data=request.data)

        if serializer.is_valid():
            fee = serializer.validated_data['fee']
            amount = serializer.validated_data['amount']

            if amount > fee.balance():
                return Response(
                    {"error": "Amount exceeds remaining balance"},
                    status=400
                )

            serializer.save()
            return Response(serializer.data, status=201)

        return Response(serializer.errors, status=400)
    
class ViewFeeByStudent(APIView):
    def get(self, request, student_id=None):
        if student_id:
            fees = Fee.objects.filter(
                student_id=student_id,
                student__user_type="student"
            ).order_by("-id")

            serializer = FeeSerializer(fees, many=True)
            return Response(serializer.data)

        fees = Fee.objects.all().order_by("-id")
        serializer = FeeSerializer(fees, many=True)
        return Response(serializer.data)

class ExportFee(APIView):
    def get(self, request):
        fees = Fee.objects.all()

        dataset = FeeResource().export(queryset=fees)

        response = HttpResponse(
            dataset.export('xlsx'),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

        response['Content-Disposition'] = 'attachment; filename="fees.xlsx"'

        return response