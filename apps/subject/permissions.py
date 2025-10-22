from rest_framework.permissions import BasePermission

class IsTeacher(BasePermission):
    """
    Allows access only to users with user_type='teacher'.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.user_type == 'teacher')
    
class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_superuser
