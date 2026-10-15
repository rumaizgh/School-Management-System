import math
from decimal import Decimal

from django.db.models import Q, Sum, Value, DecimalField
from django.db.models.functions import Coalesce, TruncDate
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status, permissions
from rest_framework.exceptions import PermissionDenied, NotAuthenticated, AuthenticationFailed
from rest_framework.response import Response
from rest_framework.utils.urls import replace_query_param
from rest_framework.views import APIView

from apps.academics.models import Institute
from .models import InstitutionalTransaction
from .serializers import (
    TransactionSerializer,
    format_validation_error_response,
)
from .services import (
    resolve_period_dates,
    get_balance_sheet_summary,
    generate_financial_excel_report,
    CATEGORIES_METADATA,
    PAYMENT_METHODS_METADATA,
)


class IsInstitutionalAdmin(permissions.BasePermission):
    """
    Ensures that only authenticated administrators and superadministrators
    can view or modify institutional finances.
    """
    message = "You do not have administrative permissions to modify institutional finances."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return (
            getattr(request.user, 'user_type', None) in ['admin', 'superadmin'] or
            getattr(request.user, 'is_superuser', False)
        )


class FinanceBaseAPIView(APIView):
    """
    Base view for Finance endpoints enforcing administrative permissions
    and standard error payloads.
    """
    permission_classes = [IsInstitutionalAdmin]

    def handle_exception(self, exc):
        if isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
            return Response({
                "status": "error",
                "code": "PERMISSION_DENIED",
                "message": "You do not have administrative permissions to modify institutional finances."
            }, status=status.HTTP_401_UNAUTHORIZED)

        if isinstance(exc, PermissionDenied):
            return Response({
                "status": "error",
                "code": "PERMISSION_DENIED",
                "message": "You do not have administrative permissions to modify institutional finances."
            }, status=status.HTTP_403_FORBIDDEN)

        return super().handle_exception(exc)

    def get_institute(self, request):
        """
        Resolves the institute for the authenticated user.
        For superadmins with no institute attached, permits institute_id override or defaults.
        """
        is_super = getattr(request.user, 'is_superuser', False) or getattr(request.user, 'user_type', None) == 'superadmin'

        inst_id = request.query_params.get('institute_id')
        if not inst_id and request.method in ['POST', 'PUT', 'PATCH']:
            try:
                inst_id = request.data.get('institute_id')
            except Exception:
                inst_id = None

        if inst_id is not None and str(inst_id).strip().lower() not in ['', 'null', 'undefined', 'none']:
            try:
                clean_id = int(str(inst_id).strip())
                return Institute.objects.get(id=clean_id)
            except (ValueError, TypeError, Institute.DoesNotExist):
                if not is_super and getattr(request.user, 'institute', None):
                    return request.user.institute
                return None

        if getattr(request.user, 'institute', None):
            return request.user.institute

        # Fallback for superadmin
        return Institute.objects.first()


class BalanceSheetSummaryView(FinanceBaseAPIView):
    """
    GET /api/finance/balance-sheet/
    Hero KPI Card summary with zero-math breakdown for the selected period.
    """

    def get(self, request):
        institute = self.get_institute(request)
        period = request.query_params.get('period', 'this_month')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        period_info = resolve_period_dates(
            period=period,
            start_date_str=start_date,
            end_date_str=end_date
        )

        data = get_balance_sheet_summary(institute, period_info)

        return Response({
            "status": "success",
            "data": data
        }, status=status.HTTP_200_OK)


class TransactionListView(FinanceBaseAPIView):
    """
    GET  /api/finance/transactions/  → Paginated transaction ledger with filters & search.
    POST /api/finance/transactions/  → Create a new institutional transaction.
    """

    def get(self, request):
        institute = self.get_institute(request)
        qs = InstitutionalTransaction.objects.all()
        if institute:
            qs = qs.filter(institute=institute)

        # Filters
        tx_type = request.query_params.get('type', 'all').lower().strip()
        if tx_type in ['expense', 'income']:
            qs = qs.filter(type=tx_type)

        period = request.query_params.get('period', 'this_month')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        period_info = resolve_period_dates(
            period=period,
            start_date_str=start_date,
            end_date_str=end_date
        )

        if period_info['start_datetime']:
            qs = qs.filter(date__gte=period_info['start_datetime'])
        if period_info['end_datetime']:
            qs = qs.filter(date__lte=period_info['end_datetime'])

        category = request.query_params.get('category')
        if category and category.strip():
            qs = qs.filter(category=category.strip().lower())

        payment_method = request.query_params.get('payment_method')
        if payment_method and payment_method.strip():
            pm = payment_method.strip().lower()
            if pm == 'cheque':
                pm = 'check'
            qs = qs.filter(payment_method=pm)

        search = request.query_params.get('search')
        if search and search.strip() and search.strip() != '-':
            term = search.strip()
            qs = qs.filter(
                Q(title__icontains=term) |
                Q(reference_number__icontains=term) |
                Q(payment_reference__icontains=term)
            )

        # Ordering
        qs = qs.order_by('-date', '-id')

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

        serializer = TransactionSerializer(paginated_qs, many=True)

        # Calculate daily_summary for distinct dates present on this page
        distinct_dates = set()
        for p in paginated_qs:
            if p.date:
                d = p.date.date() if hasattr(p.date, 'date') else None
                if d:
                    distinct_dates.add(d)

        daily_summary = {}
        if distinct_dates:
            day_stats = (
                qs.filter(date__date__in=distinct_dates)
                .annotate(d=TruncDate('date'))
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
            "status": "success",
            "data": {
                "total_records": total_records,
                "page": page,
                "limit": limit,
                "total_pages": total_pages,
                "has_next": has_next,
                "daily_summary": daily_summary,
                "results": serializer.data
            }
        }, status=status.HTTP_200_OK)

    def post(self, request):
        institute = self.get_institute(request)
        if not institute:
            return Response({
                "status": "error",
                "code": "VALIDATION_ERROR",
                "message": "An associated institution is required to create financial records.",
                "errors": {"institution": ["No institution associated with this admin."]}
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer = TransactionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                format_validation_error_response(serializer.errors),
                status=status.HTTP_400_BAD_REQUEST
            )

        transaction = serializer.save(
            institute=institute,
            created_by=request.user,
            is_edited=False
        )

        response_data = TransactionSerializer(transaction).data
        # Ensure created response matches specification fields
        response_data.pop('updated_at', None)

        return Response({
            "status": "success",
            "message": "Financial record added successfully.",
            "data": response_data
        }, status=status.HTTP_201_CREATED)


class TransactionDetailView(FinanceBaseAPIView):
    """
    PATCH  /api/finance/transactions/{id}/  → Update transaction, backend sets is_edited=True.
    PUT    /api/finance/transactions/{id}/  → Update transaction, backend sets is_edited=True.
    DELETE /api/finance/transactions/{id}/  → Permanently deletes the record from ledger.
    """

    def _resolve_transaction(self, request, raw_id):
        clean_id = str(raw_id).strip()
        lookup_id = clean_id[3:] if clean_id.lower().startswith('tx-') else clean_id
        institute = self.get_institute(request)

        try:
            pk = int(lookup_id)
            qs = InstitutionalTransaction.objects.filter(id=pk)
            if institute:
                qs = qs.filter(institute=institute)
            tx = qs.get()
            return tx, None
        except (ValueError, TypeError, InstitutionalTransaction.DoesNotExist):
            return None, Response({
                "status": "error",
                "code": "NOT_FOUND",
                "message": f"Transaction with ID '{clean_id}' does not exist."
            }, status=status.HTTP_404_NOT_FOUND)

    def get(self, request, id):
        tx, err_response = self._resolve_transaction(request, id)
        if err_response:
            return err_response

        return Response({
            "status": "success",
            "data": TransactionSerializer(tx).data
        }, status=status.HTTP_200_OK)

    def patch(self, request, id):
        tx, err_response = self._resolve_transaction(request, id)
        if err_response:
            return err_response

        serializer = TransactionSerializer(tx, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(
                format_validation_error_response(serializer.errors),
                status=status.HTTP_400_BAD_REQUEST
            )

        # As specified: When updated, backend must set is_edited = True
        updated_tx = serializer.save(is_edited=True)

        return Response({
            "status": "success",
            "message": "Financial record updated successfully.",
            "data": TransactionSerializer(updated_tx).data
        }, status=status.HTTP_200_OK)

    def put(self, request, id):
        return self.patch(request, id)

    def delete(self, request, id):
        tx, err_response = self._resolve_transaction(request, id)
        if err_response:
            return err_response

        tx.delete()

        return Response({
            "status": "success",
            "message": "Financial record removed successfully."
        }, status=status.HTTP_200_OK)


class ExportStatementView(FinanceBaseAPIView):
    """
    GET /api/finance/export/
    Generates and streams an official Excel (.xlsx) financial workbook.
    """

    def get(self, request):
        institute = self.get_institute(request)
        period = request.query_params.get('period', 'this_month')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        tx_type = request.query_params.get('type', 'all').lower().strip()

        period_info = resolve_period_dates(
            period=period,
            start_date_str=start_date,
            end_date_str=end_date
        )

        qs = InstitutionalTransaction.objects.all()
        if institute:
            qs = qs.filter(institute=institute)

        if tx_type in ['expense', 'income']:
            qs = qs.filter(type=tx_type)

        if period_info['start_datetime']:
            qs = qs.filter(date__gte=period_info['start_datetime'])
        if period_info['end_datetime']:
            qs = qs.filter(date__lte=period_info['end_datetime'])

        qs = qs.order_by('-date', '-id')

        excel_buffer = generate_financial_excel_report(
            institute=institute,
            period_info=period_info,
            type_filter=tx_type,
            transactions_qs=qs
        )

        now = timezone.now()
        period_k = period_info.get('period_key')
        if period_k == 'today':
            filename = f"Institution_Ledger_Daily_{now.strftime('%Y_%m_%d')}.xlsx"
        elif period_k == 'this_week':
            filename = f"Institution_Ledger_Weekly_{now.strftime('%Y_W%W')}.xlsx"
        elif period_k == 'custom':
            s_str = start_date or 'start'
            e_str = end_date or 'end'
            filename = f"Institution_Ledger_Custom_{s_str}_to_{e_str}.xlsx"
        else:
            month_name = now.strftime('%B')
            year_val = now.year
            filename = f"Institution_Ledger_{month_name}_{year_val}.xlsx"

        response = HttpResponse(
            excel_buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class CategoriesListView(FinanceBaseAPIView):
    """
    GET /api/finance/categories/
    Returns supported categories and payment methods for mobile app UI chips.
    """

    def get(self, request):
        return Response({
            "status": "success",
            "data": {
                "payment_methods": PAYMENT_METHODS_METADATA,
                "categories": CATEGORIES_METADATA,
            }
        }, status=status.HTTP_200_OK)
