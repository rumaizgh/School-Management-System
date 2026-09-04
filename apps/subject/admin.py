from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import Subject, Chapter, Topic


@admin.register(Subject)
class SubjectAdmin(ImportExportModelAdmin):
    list_display = ('id', 'subject_name', 'subject_code', 'teacher', 'classs', 'institute')


@admin.register(Chapter)
class ChapterAdmin(ImportExportModelAdmin):
    list_display = (
        'id',
        'chapter_number',
        'chapter_title',
        'subject',
        'status',
        'completion_percentage',
        'target_date',
        'completed_date',
        'reminder_enabled',
    )

@admin.register(Topic)
class TopicAdmin(ImportExportModelAdmin):
    list_display = ('id', 'title', 'chapter', 'is_completed', 'completed_date')