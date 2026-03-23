from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import Batch, Fee
from .serializers import BatchSerializer, FeeSerializer
from .permissions import IsAdmin,IsTeacher
from django.shortcuts import get_object_or_404
from rest_framework import status

class CreateClass(APIView):
    permission_classes=[IsAdmin]
    def post(self,request):
        serializer=BatchSerializer(data = request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors)
    
    def get(self,request,id=None):
        if id:
            batch=get_object_or_404(Batch, id=id)
            serializer = BatchSerializer(batch)
            return Response(serializer.data)
        
        batches=Batch.objects.all()
        serializer=BatchSerializer(batches,many=True)
        return Response(serializer.data)
    
    def patch(self,request,id):
        batch=get_object_or_404(Batch,id=id)
        serializer=BatchSerializer(batch,data=request.data,partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors)
    
    def delete(self,request,id):
        batch = get_object_or_404(Batch,id=id)
        batch.delete()
        return Response({"message": "Batch deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
    
class ViewAllClassTeacher(APIView):
    permission_classes=[IsTeacher]
    def get(self,request,id=None):
        teacher = request.user
        classs = Batch.objects.filter(subjects__teacher=teacher).distinct()
        serializer = BatchSerializer(classs,many=True)
        return Response(serializer.data)