from django.db import models
from django.contrib.auth.models import User


class User(models.Model):
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, unique=True)
    username = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=200, blank=True)
    major = models.CharField(max_length=100, blank=True)
    password = models.CharField(max_length=128)  # Lưu mật khẩu đã mã hóa
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username

class Equipment(models.Model):
    name = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return self.name

class TrainingSession(models.Model):
    date = models.DateTimeField()
    description = models.TextField(blank=True)

    def __str__(self):
        return f"Session on {self.date}"