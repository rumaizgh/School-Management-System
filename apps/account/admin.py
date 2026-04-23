from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import UserData
from .resources import UserDataResource

@admin.register(UserData)
class UserDataAdmin(ImportExportModelAdmin):
    resource_classes = [UserDataResource]
