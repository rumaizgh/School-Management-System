import math
from decimal import Decimal

from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status, permissions
from rest_framework.exceptions import PermissionDenied, NotAuthenticated, AuthenticationFailed
from rest_framework.response import Response
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
        return getattr(request.user, 'user_type', None) in ['admin', 'superadmin']


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
        if getattr(request.user, 'institute', None):
            return request.user.institute

        inst_id = request.query_params.get('institute_id') or request.data.get('institute_id')
        if inst_id:
            try:
                return Institute.objects.get(id=inst_id)
            except Institute.DoesNotExist:
                return None

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
            limit = int(request.query_params.get('limit', 20))
            if limit < 1:
                limit = 20
            elif limit > 50:
                limit = 50
        except ValueError:
            limit = 20

        total_records = qs.count()
        total_pages = math.ceil(total_records / limit) if total_records > 0 else 1
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_qs = qs[start_idx:end_idx]
        has_next = page < total_pages

        serializer = TransactionSerializer(paginated_qs, many=True)

        return Response({
            "status": "success",
            "data": {
                "total_records": total_records,
                "page": page,
                "limit": limit,
                "total_pages": total_pages,
                "has_next": has_next,
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
