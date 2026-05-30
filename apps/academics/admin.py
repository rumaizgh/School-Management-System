from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import *


@admin.register(Batch, TimeTable, Fee, Payment, Mark)
class AcademicsAdmin(ImportExportModelAdmin):
    pass