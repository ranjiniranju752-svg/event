from django.urls import path

from . import views

app_name = "perfumes_staff"

urlpatterns = [
    path("", views.perfume_list_staff, name="perfume_list_staff"),
    path("add/", views.perfume_add, name="perfume_add"),
    path("<int:pk>/edit/", views.perfume_edit, name="perfume_edit"),
    path("<int:pk>/delete/", views.perfume_delete, name="perfume_delete"),
    path(
        "<int:pk>/toggle-publish/",
        views.perfume_toggle_publish,
        name="perfume_toggle_publish",
    ),
]
