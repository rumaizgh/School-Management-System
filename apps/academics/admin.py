from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import *


@admin.register(Institute, Batch, TimeTable, Fee, Payment, Mark)
class AcademicsAdmin(ImportExportModelAdmin):
    pass