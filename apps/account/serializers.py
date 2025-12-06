from rest_framework import serializers
from .models import UserData
from apps.subject.models import Subject

class UserDataSerializer(serializers.ModelSerializer):
    subject = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Subject.objects.all(),
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
