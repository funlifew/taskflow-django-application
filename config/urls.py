"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include('apps.accounts.urls', namespace='accounts')),
    path('dashboard/', include('apps.dashboard.urls', namespace='dashboard')),
    path('workspaces/<int:workspace_pk>/boards/<int:board_pk>/columns/<int:column_pk>/tasks/', include('apps.tasks.urls', namespace='tasks')),
    path('workspaces/<int:workspace_pk>/boards/<int:board_pk>/columns/', include('apps.columns.urls', namespace='columns')),
    path('workspaces/<int:workspace_pk>/boards/', include('apps.boards.urls', namespace='boards')),
    path('workspaces/', include('apps.workspaces.urls', namespace='workspaces')),
    path("", TemplateView.as_view(template_name="landing.html"), name="landing"),
]

if settings.DEBUG:
    urlpatterns += [
        path("__debug__/", include('debug_toolbar.urls')),
    ]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)