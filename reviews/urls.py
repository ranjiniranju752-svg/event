from django.urls import path

from . import views

app_name = "reviews"

urlpatterns = [
    path(
        "success/<slug:tracking_id>/",
        views.review_success,
        name="success",
    ),
]
