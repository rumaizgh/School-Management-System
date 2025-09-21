from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .models import UserData
from .serializers import UserDataSerializer 

# CRUD API for UserData
class UserDataViewSet(viewsets.ModelViewSet):
    queryset = UserData.objects.all()
    serializer_class = UserDataSerializer


# API for login
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        password = request.data.get('password')

        print("Email:", email)
        print("Password:", password)
        
        # Check if user exists
        try:
            user_obj = UserData.objects.get(email=email)
            print("User found:", user_obj)
            print("User is active:", user_obj.is_active)
            print("User password (hashed):", user_obj.password)
        except UserData.DoesNotExist:
            print("User does not exist")
            return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)

        # Try authentication
        user = authenticate(request, email=email, password=password)

        
        print("User authenticated:", user)

        if user is not None:
            if user.is_active:
                refresh = RefreshToken.for_user(user)
                user_data = UserDataSerializer(user).data
                return Response({
                    'user': user_data,
                    'refresh': str(refresh),
                    'access': str(refresh.access_token)
                })
            else:
                return Response({"detail": "User account is disabled."}, status=status.HTTP_403_FORBIDDEN)
        else:
            return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)