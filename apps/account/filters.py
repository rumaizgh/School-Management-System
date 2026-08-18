from rest_framework import filters

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
            return queryset.filter(institute=user.institute)

        # 2. Indirect relations through parent models
        # E.g. Mark -> exam -> institute
        if hasattr(model, 'exam'):
            return queryset.filter(exam__institute=user.institute)

        # E.g. Payment -> fee -> institute
        if hasattr(model, 'fee'):
            return queryset.filter(fee__institute=user.institute)

        # E.g. AttendanceRecord -> session -> institute
        if hasattr(model, 'session'):
            return queryset.filter(session__institute=user.institute)

        # Fallback for other tables: do not filter (or return empty if you want strict security)
        return queryset
