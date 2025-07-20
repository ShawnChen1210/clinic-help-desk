from django.db import models
from django.contrib.auth.models import User, AbstractUser

class UserSheet(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE) #one user can have many entries in this Model
    sheet_id = models.CharField(max_length=100)
    sheet_name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.sheet_id
# Create your models here.