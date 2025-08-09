from rest_framework import serializers
from help_desk.models import *
from .models import *

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'

class UserSheetSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSheet
        fields = '__all__'

class SheetColumnPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SheetColumnPreference
        fields = ['sheet_id', 'date_column', 'income_columns']