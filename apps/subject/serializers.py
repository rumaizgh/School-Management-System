from rest_framework import serializers
from .models import Subject

class SubjectSerializer(serializers.ModelSerializer):
    teacher = serializers.CharField(source='teacher.name', read_only=True)

    class Meta:
        model = Subject
        fields = ['id','subject_name','subject_code','classs', 'teacher']
