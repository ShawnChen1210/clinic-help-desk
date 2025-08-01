from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from api.serializers import UserSerializer


# Create your views here.

@api_view(['GET'])
def hello_world(request):
    return Response({"message": "Hello from Django!"})

@api_view(['GET'])
def user(request):
    serializer = UserSerializer(request.user)
    return Response(serializer.data)