from rest_framework import filters
from django.db.models import Q

class InstituteFilterBackend(filters.BaseFilterBackend):
    """
    A global filter backend for Django REST Framework that automatically filters
    all querysets to the scope of the authenticated user's institute.
    """
    def filter_queryset(self, request, queryset, view):
        user = request.user
        if not user or not user.is_authenticated:
            return queryset.none()

        # Superusers with no specific institute can see all schools/records
        if user.is_superuser and not user.institute:
            return queryset

        model = queryset.model

        # 1. Direct institute relation (UserData, Batch, Subject, Fee, TimeTable, Exam, AttendanceSession)
        if hasattr(model, 'institute'):
            if user.institute:
                return queryset.filter(Q(institute=user.institute) | Q(institute__isnull=True))
            return queryset

        # 2. Indirect relations through parent models
        # E.g. Mark -> exam -> institute
        if hasattr(model, 'exam'):
            if user.institute:
                return queryset.filter(Q(exam__institute=user.institute) | Q(exam__institute__isnull=True))
            return queryset

        # E.g. Payment -> fee -> institute
        if hasattr(model, 'fee'):
            if user.institute:
                return queryset.filter(Q(fee__institute=user.institute) | Q(fee__institute__isnull=True))
            return queryset

        # E.g. AttendanceRecord -> session -> institute
        if hasattr(model, 'session'):
            if user.institute:
                return queryset.filter(Q(session__institute=user.institute) | Q(session__institute__isnull=True))
            return queryset

        # Fallback for other tables: do not filter
        return queryset


from django.shortcuts import get_object_or_404

def get_institute_scoped_object_or_404(model, request, **kwargs):
    """
    A secure get_object_or_404 helper that first filters the queryset
    by the requesting user's institute using the InstituteFilterBackend.
    """
    backend = InstituteFilterBackend()
    scoped_queryset = backend.filter_queryset(request, model.objects.all(), None)
    return get_object_or_404(scoped_queryset, **kwargs)

