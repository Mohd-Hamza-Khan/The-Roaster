# from django.urls import path, include
# from rest_framework.routers import DefaultRouter
# from .views import MatchRequestViewSet, MatchingAPIView, ChatMessageViewSet

# # Create a router and register our ViewSets with it.
# router = DefaultRouter()
# router.register(r'match-requests', MatchRequestViewSet, basename='matchrequest')

# # Nested router for chat messages (e.g., /api/match-requests/1/chat/)
# nested_router = DefaultRouter()
# nested_router.register(r'chat', ChatMessageViewSet, basename='chatmessage')


# urlpatterns = [
#     # Core Model APIs
#     path('', include(router.urls)),
    
#     # Custom Matching API
#     path('matchmaking/', MatchingAPIView.as_view(), name='matchmaking'),
    
#     # Nested Chat API (e.g. /api/match-requests/{pk}/chat/)
#     path('match-requests/<int:match_request_pk>/', include(nested_router.urls)),
# ]


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


# Specific endpoints and router generated URLs
urlpatterns = [
    # The core matchmaking logic endpoint
    path('matchmaking/', MatchingAPIView.as_view(), name='matchmaking'),
    
    # Router URLs for match-requests, chat messages, and availability
    path('', include(router.urls)),
]
