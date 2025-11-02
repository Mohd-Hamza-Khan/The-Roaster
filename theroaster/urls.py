from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # App URLs
    path('teams/', include('teams.urls')),
    # REST Framework API URLs
    path('api/', include(('teams.api_urls', 'api'), namespace='api')),
]
