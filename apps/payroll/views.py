from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404

from apps.account.models import UserData
from apps.account.filters import InstituteFilterBackend, get_institute_scoped_object_or_404
from apps.notifications.services import send_salary_disbursement_notification

from .models import TeacherSalary, SalaryPayment
from .serializers import (
    SalaryConfigCreateSerializer,
    SalaryDetailSerializer,
    SalaryPaymentSerializer,
)


class SalaryConfigView(APIView):
    """
    POST   /api/payroll/teachers/{teacher_id}/salary-config/
        → Create or update salary configuration for a teacher for a specific month.

    GET    /api/payroll/teachers/{teacher_id}/salary-config/?month=YYYY-MM
        → Retrieve full payroll breakdown for that teacher and month.
    """
    permission_classes = [IsAuthenticated]

    def _get_teacher(self, request, teacher_id):
        """Return teacher scoped to the requesting admin's institute."""
        return get_institute_scoped_object_or_404(
            UserData, request, id=teacher_id, user_type='teacher'
        )

    def post(self, request, teacher_id):
        teacher = self._get_teacher(request, teacher_id)

        serializer = SalaryConfigCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        month = serializer.validated_data['month']

        # Update or create — unique per (teacher, month)
        salary, created = TeacherSalary.objects.update_or_create(
            teacher=teacher,
            month=month,
            defaults={
                **serializer.validated_data,
                'institute': request.user.institute,
                'status': 'configured',
            }
        )

        # Mark teacher as having a salary configuration
        if not teacher.has_salary_config:
            teacher.has_salary_config = True
            teacher.save(update_fields=['has_salary_config'])

        return Response({
            "success": True,
            "message": "Salary structure assigned successfully.",
            "data": {
                "teacher_id": teacher.id,
                "status": salary.status,
                "pay_type": salary.pay_type,
                "net_salary": salary.net_salary,
                "balance": salary.balance,
            }
        }, status=status.HTTP_200_OK)

    def get(self, request, teacher_id):
        teacher = self._get_teacher(request, teacher_id)

        month = request.GET.get('month')
        if not month:
            return Response(
                {"error": "Query parameter 'month' is required (format: YYYY-MM)."},
                status=status.HTTP_400_BAD_REQUEST
            )

        salary = get_object_or_404(TeacherSalary, teacher=teacher, month=month)
        serializer = SalaryDetailSerializer(salary)

        return Response({"success": True, "data": serializer.data})


class DisbursePaymentView(APIView):
    """
    POST /api/payroll/disburse/
        → Record a salary disbursement payment for a teacher.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SalaryPaymentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Verify the salary record belongs to the requesting user's institute
        salary = serializer.validated_data['salary']
        if (
            not request.user.is_superuser
            and salary.institute
            and salary.institute != request.user.institute
        ):
            return Response(
                {"error": "You do not have permission to disburse this salary."},
                status=status.HTTP_403_FORBIDDEN
            )

        payment = serializer.save()

        # Reload salary to get updated balance
        salary.refresh_from_db()

        # Send FCM + save notification history
        send_salary_disbursement_notification(payment)

        return Response({
            "success": True,
            "message": "Salary payment recorded successfully.",
            "data": {
                "id": payment.id,
                "salary_id": payment.salary_id,
                "amount": float(payment.amount),
                "payment_method": payment.payment_method,
                "transaction_id": payment.transaction_id,
                "updated_balance": salary.balance,
                "payment_status": salary.payment_status,
            }
        }, status=status.HTTP_201_CREATED)


class PayrollHistoryView(APIView):
    """
    GET /api/payroll/history/?search=&month=
        → Returns all salary payment transactions for the institute.
        Supports filtering by teacher name (search) and month.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = SalaryPayment.objects.select_related('teacher', 'salary').order_by('-paid_on')

        # Institute scoping
        if not request.user.is_superuser and request.user.institute:
            qs = qs.filter(salary__institute=request.user.institute)

        # Filter by month
        month = request.GET.get('month')
        if month:
            qs = qs.filter(salary__month=month)

        # Filter by teacher name (search)
        search = request.GET.get('search')
        if search:
            qs = qs.filter(teacher__name__icontains=search)

        serializer = SalaryPaymentSerializer(qs, many=True)
        return Response({
            "success": True,
            "count": qs.count(),
            "data": serializer.data
        })


class TeacherPaymentHistoryView(APIView):
    """
    GET /api/account/teachers/{teacher_id}/payments/
        → Returns all salary payment transactions for a specific teacher.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, teacher_id):
        teacher = get_institute_scoped_object_or_404(
            UserData, request, id=teacher_id, user_type='teacher'
        )

        payments = SalaryPayment.objects.filter(teacher=teacher).select_related('salary').order_by('-paid_on')
        serializer = SalaryPaymentSerializer(payments, many=True)

        return Response({
            "success": True,
            "count": payments.count(),
            "data": serializer.data
        })
