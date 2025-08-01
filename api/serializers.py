from rest_framework import serializers
from help_desk.models import *

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'

class UserSheetSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSheet
        fields = '__all__'