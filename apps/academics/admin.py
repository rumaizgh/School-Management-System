from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import *

# Register your models here.
# admin.site.register([Batch, TimeTable, Fee, Payment])

@admin.register(Batch, TimeTable, Fee, Payment)
class UserDataAdmin(ImportExportModelAdmin):
    pass