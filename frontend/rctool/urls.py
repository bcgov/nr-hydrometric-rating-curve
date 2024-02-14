from django.urls import path
from . import views

urlpatterns = [
    #path("", views.index, name="index"),
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("rctool/tour/<int:tour_request_id>/", views.rctool_tour_intro, name="rctool_tour_intro"),
    path("rctool/import/<int:tour_request_id>/", views.rctool_import, name="rctool_import"),
    path("rctool/develop/initialize", views.rctool_develop_initialize, name="rctool_develop_initialize"),
    path("rctool/develop/", views.rctool_develop_autofit, name="rctool_develop_autofit"),
    path("rctool/export/initialize", views.rctool_export_initialize, name="rctool_export_initialize"),
    path("rctool/export/output", views.rctool_export_output, name="rctool_export_output"),
]