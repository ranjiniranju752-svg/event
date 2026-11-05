"""Root URL configuration for ScentScope."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from reviews.views import track_review
from perfumes.views import home

urlpatterns = [
    path("", home, name="home"),
    path("perfumes/", include("perfumes.urls")),
    path("staff/perfumes/", include("perfumes.staff_urls")),
    path("reviews/", include("reviews.urls")),
    path("track/", track_review, name="track"),
    path("accounts/", include("accounts.urls")),
    path("staff/", include("analytics.urls")),
    path("django-admin/", admin.site.urls),
]

if settings.DEBUG:
    # Serve uploaded perfume images during development only.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
