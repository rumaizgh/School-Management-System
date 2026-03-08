from rest_framework import serializers
from apps.subject.serializers import SubjectSerializer
from .models import UserData
from apps.subject.models import Subject

class UserDataSerializer(serializers.ModelSerializer):
    subjects = SubjectSerializer(many=True, read_only=True)
    subject_ids = serializers.PrimaryKeyRelatedField(
        queryset=Subject.objects.all(),
        many=True,
        write_only=True,
        source='subjects',
        required=False
    )

    class Meta:
        model = UserData
        fields = "__all__"
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        subjects = validated_data.pop('subject', None)
        password = validated_data.pop('password', None)
        user = UserData(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        if subjects is not None:
            user.subject.set(subjects)
        return user

    def update(self, instance, validated_data):
        subjects = validated_data.pop('subject', None)
        password = validated_data.pop('password', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()

        if subjects is not None:
            instance.subject.set(subjects)
        return instance

class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = UserData
        fields = (
            "name",
            "email",
            "password",
            "classs",
            "phone",
        )
        extra_kwargs = {
            "email": {"required": True},
            "phone" :{"required" : True}
        }

    def validate_email(self, value):
        if UserData.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists.")
        return value
    
    def validate_phone(self, value):
        if len(value) < 10:
            raise serializers.ValidationError("Phone number must be at least 10 digits.")
        return value

    def create(self, validated_data):
        return UserData.objects.create_user(**validated_data)