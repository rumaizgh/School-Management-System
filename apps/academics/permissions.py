from rest_framework.permissions import BasePermission

class IsTeacher(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.user_type == 'teacher')
    
class IsStudent(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.user_type == 'student')

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_superuser

class IsStudentOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            (request.user.user_type == 'student' or request.user.is_superuser)
        )
    
class IsTeacherOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            (request.user.user_type == 'teacher' or request.user.is_superuser)
        )