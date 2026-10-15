import math
from decimal import Decimal
from django.db.models import Sum, Q, Value, DecimalField
from django.db.models.functions import Coalesce, TruncDate
from rest_framework.utils.urls import replace_query_param

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
        serializer = SalaryDetailSerializer(salary, context={'request': request})

        return Response({"success": True, "data": serializer.data})


class DisbursePaymentView(APIView):
    """
    POST /api/payroll/disburse/
        → Record a salary disbursement payment for a teacher.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SalaryPaymentSerializer(data=request.data, context={'request': request})
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
    GET /api/payroll/history/?search=&month=&page=&limit=
        → Returns paginated salary payment transactions for the institute
        with a daily_summary dictionary for dates on that page.
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

        # Pagination
        try:
            page = int(request.query_params.get('page', 1))
            if page < 1:
                page = 1
        except ValueError:
            page = 1

        try:
            limit = int(request.query_params.get('limit') or request.query_params.get('page_size', 20))
            if limit < 1:
                limit = 20
            elif limit > 100:
                limit = 100
        except ValueError:
            limit = 20

        total_records = qs.count()
        total_pages = math.ceil(total_records / limit) if total_records > 0 else 1
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_qs = qs[start_idx:end_idx]
        has_next = page < total_pages

        serializer = SalaryPaymentSerializer(paginated_qs, many=True, context={'request': request})

        # Calculate daily_summary for distinct dates present on this page
        distinct_dates = set()
        for p in paginated_qs:
            if p.paid_on:
                d = p.paid_on.date() if hasattr(p.paid_on, 'date') else None
                if d:
                    distinct_dates.add(d)

        daily_summary = {}
        if distinct_dates:
            day_stats = (
                qs.filter(paid_on__date__in=distinct_dates)
                .annotate(d=TruncDate('paid_on'))
                .values('d')
                .annotate(
                    total=Coalesce(Sum('amount'), Value(0, output_field=DecimalField())),
                    cash=Coalesce(Sum('amount', filter=Q(payment_method__iexact='cash')), Value(0, output_field=DecimalField())),
                    bank=Coalesce(Sum('amount', filter=Q(payment_method__iexact='bank_transfer') | Q(payment_method__iexact='bank')), Value(0, output_field=DecimalField())),
                    upi=Coalesce(Sum('amount', filter=Q(payment_method__iexact='upi') | Q(payment_method__iexact='gpay')), Value(0, output_field=DecimalField())),
                    cheque=Coalesce(Sum('amount', filter=Q(payment_method__iexact='cheque') | Q(payment_method__iexact='check')), Value(0, output_field=DecimalField())),
                )
            )

            def _fmt(val):
                if val is None:
                    return 0.0
                d = Decimal(str(val))
                return float(round(d, 2))

            for stat in sorted(day_stats, key=lambda s: str(s['d']), reverse=True):
                d_key = stat['d'].strftime('%Y-%m-%d') if hasattr(stat['d'], 'strftime') else str(stat['d'])[:10]
                total = _fmt(stat['total'])
                cash = _fmt(stat['cash'])
                upi = _fmt(stat['upi'])
                bank = _fmt(stat['bank'])
                cheque = _fmt(stat['cheque'])
                other = max(0.0, round(total - (cash + upi + bank + cheque), 2))

                daily_summary[d_key] = {
                    "total": total,
                    "cash": cash,
                    "gpay": upi,
                    "upi": upi,
                    "bank_transfer": bank,
                    "bank": bank,
                    "cheque": cheque,
                    "check": cheque,
                    "other": other,
                }

        # Ensure all distinct dates are present, even if 0
        for d in sorted(distinct_dates, reverse=True):
            d_key = d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d)[:10]
            if d_key not in daily_summary:
                daily_summary[d_key] = {
                    "total": 0.0,
                    "cash": 0.0,
                    "gpay": 0.0,
                    "upi": 0.0,
                    "bank_transfer": 0.0,
                    "bank": 0.0,
                    "cheque": 0.0,
                    "check": 0.0,
                    "other": 0.0,
                }

        try:
            base_url = request.build_absolute_uri()
        except Exception:
            base_url = request.path

        next_link = replace_query_param(base_url, 'page', page + 1) if has_next else None
        prev_link = replace_query_param(base_url, 'page', page - 1) if page > 1 else None

        return Response({
            "count": total_records,
            "next": next_link,
            "previous": prev_link,
            "daily_summary": daily_summary,
            "results": serializer.data,
            "success": True,
            "data": serializer.data,
            "total_records": total_records,
            "total_pages": total_pages,
            "current_page": page,
            "page": page,
            "limit": limit
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
        serializer = SalaryPaymentSerializer(payments, many=True, context={'request': request})

        return Response({
            "success": True,
            "count": payments.count(),
            "data": serializer.data
        })
