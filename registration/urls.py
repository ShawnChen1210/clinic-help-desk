from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('login_user/', views.login_user, name='login_user'),
    path('register/', views.register_user, name='register'),
    path('logout/', LogoutView.as_view(next_page='index'), name='logout'),
    path('activate/<uidb64>/<token>/', views.activate, name='activate'),
    path('members/', views.members, name='members'),
]