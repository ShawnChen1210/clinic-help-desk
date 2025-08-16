from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import TemplateView
from django.conf import settings
from django.views.static import serve
from django.views.decorators.csrf import ensure_csrf_cookie


#    This creates a view that will always set the CSRF cookie.
react_app_view = ensure_csrf_cookie(TemplateView.as_view(template_name='index.html'))

urlpatterns = [
    # Your specific paths (admin, api) should come first
    path('admin/', admin.site.urls),
    path('api/', include('api.api_urls')),

    # Other apps
    path('', include('api.urls')),
    path('registration/', include('django.contrib.auth.urls')),
    path('registration/', include('registration.urls')),

    # Rules for React static files (like manifest.json)
    re_path(r'^(?P<path>manifest\.json|favicon\.ico|robots\.txt|logo192\.png|logo512\.png)$',
            serve, {'document_root': settings.BASE_DIR / 'frontend/build'}),

    re_path(r'^.*$', react_app_view),
]