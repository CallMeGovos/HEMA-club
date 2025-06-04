from django.contrib import admin
from .models import User, Equipment, TrainingSession

admin.site.register(User)
admin.site.register(Equipment)
admin.site.register(TrainingSession)