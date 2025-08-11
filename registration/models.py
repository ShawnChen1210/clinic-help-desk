from django.db import models
from django.contrib.auth.models import User
from pygments.lexer import default


# Create your models here.
class UserProfile(models.Model): # Stores additional information regarding user in addition to django default user model
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_verified = models.BooleanField(default=False) #Only verified users get to access the dashboard and create sheets
    billing_dates = models.JSONField(default=list)
    role = models.CharField(default="member", max_length=50)

    def __str__(self):
        return str(self.user)
