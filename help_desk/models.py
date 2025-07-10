from django.db import models
from django.contrib.auth.models import User, AbstractUser


# Create your models here.
class UserInfo(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_email_verified = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)