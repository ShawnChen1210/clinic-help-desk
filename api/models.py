from django.db import models
from django.contrib.auth.models import User

# A new model to store a user's column preferences for a specific sheet.
class SheetColumnPreference(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    sheet_id = models.CharField(max_length=255)
    date_column = models.CharField(max_length=255)
    income_columns = models.JSONField()

    class Meta:
        unique_together = ('user', 'sheet_id')

    def __str__(self):
        return f"{self.user.username}'s preference for {self.sheet_id}"