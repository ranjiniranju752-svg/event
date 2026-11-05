from django.urls import path

from reviews.views import submit_review

from . import views

app_name = "perfumes"

urlpatterns = [
    path("", views.perfume_list, name="list"),
    path("<slug:slug>/", views.perfume_detail, name="detail"),
    path("<slug:slug>/reviews/", submit_review, name="reviews"),
]
