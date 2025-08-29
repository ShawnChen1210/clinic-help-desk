from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from api import views as api_views

urlpatterns = [
    # 1. Your specific, high-priority URLs
    path('admin/', admin.site.urls),
    path('api/', include('api.api_urls')),
    path('registration/', include('django.contrib.auth.urls')),
    path('registration/', include('registration.urls')),

    # 2. A catch-all for your React app, prefixed with 'chd-app/'
    # This will match '/chd-app/', '/chd-app/dashboard', '/chd-app/some/other/route'
    re_path(r'^chd-app/.*$', api_views.chd_app),

    # 3. The root URL for your Django-rendered homepage
    path('', include('api.urls')),
]

# This part for serving static files in development stays the same
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)