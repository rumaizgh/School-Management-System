from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import UserData


@admin.register(UserData)
class UserDataAdmin(ImportExportModelAdmin):
    pass
