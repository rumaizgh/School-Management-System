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
            "phone",
            "classs",
            "subject",
            "user_type",
        )
        extra_kwargs = {
            "user_type": {"required": True},
        }


    def validate(self, attrs):
        user_type = attrs.get("user_type")

        if user_type not in ["student", "teacher"]:
            raise serializers.ValidationError("Invalid user type.")
        
        # Student must have email 
        if user_type == "student" and not attrs.get("email"):
            raise serializers.ValidationError({"email": "Email is required for students."})
        
        # Teacher must have phone
        if user_type == "teacher" and not attrs.get("phone"):
            raise serializers.ValidationError("Phone is required for teachers.")

        return attrs

    def validate_phone(self, value):
        if len(value) < 10:
            raise serializers.ValidationError("Phone number must be at least 10 digits.")
        return value

    def create(self, validated_data):
        subjects = validated_data.pop("subject", [])
        user_type = validated_data.get("user_type")

        user = UserData.objects.create_user(**validated_data)

        # Only teachers get subjects
        if user_type == "teacher":
            user.subject.set(subjects)

        return user