from django.urls import path
from .views import (
    BalanceSheetSummaryView,
    TransactionListView,
    TransactionDetailView,
    ExportStatementView,
    CategoriesListView,
)

urlpatterns = [
    # 1. Balance Sheet Summary (Hero KPI Card)
    path('balance-sheet/', BalanceSheetSummaryView.as_view(), name='finance-balance-sheet'),

    # 2. Transaction Ledger List (GET) & Record Creation (POST)
    path('transactions/', TransactionListView.as_view(), name='finance-transactions-list-create'),

    # 3. Transaction Details: Edit (PATCH/PUT) & Delete (DELETE)
    path('transactions/<str:id>/', TransactionDetailView.as_view(), name='finance-transaction-detail'),

    # 4. Statement Excel Export (.xlsx)
    path('export/', ExportStatementView.as_view(), name='finance-export-excel'),

    # 5. Metadata for Mobile UI Chips (Categories & Payment Methods)
    path('categories/', CategoriesListView.as_view(), name='finance-categories'),
]
