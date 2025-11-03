from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    MatchingAPIView, 
    MatchRequestViewSet, 
    ChatMessageViewSet, 
    AvailabilityViewSet
)

# Use a router for the ViewSets (MatchRequest, ChatMessage, Availability)
router = DefaultRouter()
# Note: basename is needed since we aren't using queryset in the ChatMessageViewSet 
# or AvailabilityViewSet due to being nested/custom logic (though MatchRequest uses it)
router.register(r'match-requests', MatchRequestViewSet, basename='matchrequest')
router.register(r'messages', ChatMessageViewSet, basename='chatmessage')
router.register(r'availability', AvailabilityViewSet, basename='availability')

app_name = 'api'


# Specific endpoints and router generated URLs
urlpatterns = [
    # The core matchmaking logic endpoint
    path('matchmaking/', MatchingAPIView.as_view(), name='matchmaking'),
    
    # Router URLs for match-requests, chat messages, and availability
    path('', include(router.urls)),
]
