from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("gestion-django/", admin.site.urls),
    path("", include("portal.urls", namespace="portal")),
]

# Dev + Render: servir les fichiers uploadés (MEDIA).
if settings.DEBUG or settings.MEDIA_ROOT:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
