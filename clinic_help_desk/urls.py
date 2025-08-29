# In your main project's urls.py

from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.contrib.staticfiles.urls import staticfiles_urlpatterns # Import this
from api import views as api_views

urlpatterns = [
    # 1. Your specific, high-priority URLs
    path('admin/', admin.site.urls),
    path('api/', include('api.api_urls')),
    path('registration/', include('django.contrib.auth.urls')),
    path('registration/', include('registration.urls')),

    # 2. The catch-all for your React app, prefixed with 'chd-app/'
    re_path(r'^chd-app/.*$', api_views.chd_app),

    # 3. The root URL for your Django-rendered homepage
    path('', include('api.urls')),
]

# 4. This block adds the necessary URL patterns for serving static files
#    (like your Tailwind CSS) during development. It is ignored in production.
if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()