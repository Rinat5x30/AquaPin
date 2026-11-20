from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("demo/<slug:slug>/", views.demo, name="demo"),
    path("pin/", views.pin, name="pin"),
    path("lang/<str:code>/", views.set_language, name="set_language"),
    path("fields/<uuid:field_id>/", views.field_detail, name="field"),
    path("fields/<uuid:field_id>/status/", views.field_status, name="field_status"),
    path("fields/<uuid:field_id>/retry/", views.field_retry, name="field_retry"),
    path("fields/<uuid:field_id>/delete/", views.field_delete, name="field_delete"),
    path("fields/<uuid:field_id>/asset/<path:path>", views.field_asset, name="field_asset"),
    path("api/fields/<uuid:field_id>/", views.field_api, name="field_api"),
    path("tg/webhook/", views.telegram_webhook, name="telegram_webhook"),
    path("healthz", views.health, name="health"),
]
