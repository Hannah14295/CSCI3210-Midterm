from django.contrib import admin
from django.conf import settings
from django.urls import include, path
from django.views.generic import RedirectView, TemplateView
from .views import health

urlpatterns = [
    path("health/", health, name="health"),
    path("", RedirectView.as_view(url="/api/paragraphs/", permanent=False)),
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/", include("races.urls")),
]

if settings.DEBUG:
    urlpatterns += [
        path("dev/socket/", TemplateView.as_view(template_name="races/socket_test.html"), name="socket-test"),
    ]
