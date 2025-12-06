from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import Subject
from .serializers import SubjectSerializer
from .permissions import IsAdmin

class AddSubject(APIView):
    def get(self,request,id):
        subject = Subject.objects.get(id=id)
        serializer = SubjectSerializer(subject)
        return Response(serializer.data)

    def post(self,request,id):
        serializer = SubjectSerializer(data = request.data)
        if (serializer.is_valid()):
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors)