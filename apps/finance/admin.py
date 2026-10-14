from django.contrib import admin
from .models import InstitutionalTransaction


@admin.register(InstitutionalTransaction)
class InstitutionalTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'formatted_id',
        'title',
        'type',
        'amount',
        'category',
        'payment_method',
        'date',
        'is_edited',
        'institute',
        'created_by',
    )
    list_filter = ('type', 'category', 'payment_method', 'is_edited', 'institute', 'date')
    search_fields = ('title', 'reference_number', 'payment_reference', 'remarks')
    readonly_fields = ('is_edited', 'created_at', 'updated_at')
    ordering = ('-date', '-id')
