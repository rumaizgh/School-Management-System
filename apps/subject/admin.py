from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import *

# Register your models here.
# admin.site.register(Subject)
@admin.register(Subject)
class SubjectAdmin(ImportExportModelAdmin):
    pass