from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)  
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(email, password, **extra_fields)

class UserData(AbstractUser):

    CHOICES = [
        ('student', 'Student'),
        ('teacher', 'Teacher'),
    ]
    BATCHES = [
        ('plus_one', 'Plus_One'),
        ('plus_two', 'Plus_Two')
    ]

    username = None
    user_type = models.CharField(max_length=10, choices=CHOICES)
    name = models.CharField(max_length=100, null=True, blank=True)
    email = models.EmailField(unique = True, blank=True, null=True)
    batch_type = models.CharField(max_length=10, choices=BATCHES, null=True, blank=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    parent_name = models.CharField(max_length=100, null=True, blank=True)
    parent_contact = models.CharField(max_length=15, null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return f"{self.name} - {self.email} "
