from rest_framework.views import APIView
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .serializers import UserDataSerializer
from rest_framework.permissions import AllowAny
from .models import UserData
from apps.academics.permissions import IsAdmin


# class UserDataViewSet(viewsets.ModelViewSet):
#     queryset = UserData.objects.all()
#     serializer_class = UserDataSerializer
#     permission_classes = [IsAdmin]

class UserDataView(APIView):
    def post(self,request):
        serializer = UserDataSerializer(data = request.data)
        if (serializer.is_valid()):
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors)
    
    def patch(self,request,id):
        objects = UserData.objects.get(id = id)
        serializer = UserDataSerializer(objects, data = request.data, partial = True)
        if (serializer.is_valid()):
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors)

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        user = authenticate(request, email=email, password=password)

        if user is None:
            return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return Response({"detail": "User account is disabled."}, status=status.HTTP_403_FORBIDDEN)

        user_role = user.user_type 

        refresh = RefreshToken.for_user(user)
        user_data = UserDataSerializer(user).data

        return Response({
            'user': user_data,
            'role': user_role,
            'refresh': str(refresh),
            'access': str(refresh.access_token)
        })

class ViewAllTeachers(APIView):
    permission_classes = [AllowAny]

    def get(self,request, id=None):
        if id:
            teachers = UserData.objects.filter(user_type='teacher',id = id)
            serializer = UserDataSerializer(teachers, many = True)
            return Response(serializer.data)
        teachers = UserData.objects.filter(user_type = 'teacher')
        serializer = UserDataSerializer(teachers, many = True)
        return Response(serializer.data)
    
class ViewAllStudents(APIView):
    permission_classes = [AllowAny]

    def get(self, request, id=None):
        if id:
            students = UserData.objects.filter(user_type='student', id = id)
            serializer = UserDataSerializer(students, many=True)
            return Response(serializer.data)
        
        students = UserData.objects.filter(user_type='student')
        serializer = UserDataSerializer(students, many = True)
        return Response(serializer.data)