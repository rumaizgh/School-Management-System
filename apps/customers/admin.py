from django.contrib import admin
from .models import Client, Domain

class DomainInline(admin.TabularInline):
    model = Domain
    extra = 1
    max_num = 1  # Standard multi-tenancy usually has one primary domain per school

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'schema_name', 'created_on')
    search_fields = ('name', 'schema_name')
    inlines = [DomainInline]

@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ('domain', 'tenant', 'is_primary')
    search_fields = ('domain',)
