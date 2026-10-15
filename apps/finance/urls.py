from django.urls import re_path
from .views import (
    BalanceSheetSummaryView,
    TransactionListView,
    TransactionDetailView,
    ExportStatementView,
    CategoriesListView,
)

urlpatterns = [
    # 1. Balance Sheet Summary (Hero KPI Card)
    re_path(r'^balance-sheet/?$', BalanceSheetSummaryView.as_view(), name='finance-balance-sheet'),

    # 2. Transaction Ledger List (GET) & Record Creation (POST)
    re_path(r'^transactions/?$', TransactionListView.as_view(), name='finance-transactions-list-create'),

    # 3. Transaction Details: Retrieve (GET), Edit (PATCH/PUT) & Delete (DELETE)
    re_path(r'^transactions/(?P<id>[^/]+)/?$', TransactionDetailView.as_view(), name='finance-transaction-detail'),

    # 4. Statement Excel Export (.xlsx)
    re_path(r'^export/?$', ExportStatementView.as_view(), name='finance-export-excel'),

    # 5. Metadata for Mobile UI Chips (Categories & Payment Methods)
    re_path(r'^categories/?$', CategoriesListView.as_view(), name='finance-categories'),
]
