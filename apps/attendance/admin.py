from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import *

# Register your models here.
# admin.site.register(AttendanceSession)
# admin.site.register(AttendanceRecord)

@admin.register(AttendanceSession, AttendanceRecord)
class AttendanceAdmin(ImportExportModelAdmin):
    pass