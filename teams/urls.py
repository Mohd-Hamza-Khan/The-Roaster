from django.urls import path
from .views import (
    # Auth Views
    RegisterView,
    CustomLoginView,
    CustomLogoutView,
    
    # App Views
    ProfileView,
    HomeView,
    DashboardView, 
    TeamCreateView, 
    TeamUpdateView, 
    AvailabilityManagementView,
    MatchFinderView,
    MatchRequestDetailView,
)

app_name = 'teams'

urlpatterns = [
    # --- Auth Routes ---
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    path('profile/', ProfileView.as_view(), name='profile'),    # --- Main App & Team Management Routes (Require Login) ---
    
    # The home page for the app
    path('', HomeView.as_view(), name='home'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'), 
    
    # Team CRUD
    path('team/create/', TeamCreateView.as_view(), name='team_create'),
    path('team/<int:pk>/edit/', TeamUpdateView.as_view(), name='team_edit'),
    path('match-requests/<int:pk>/', MatchRequestDetailView.as_view(), name='match_request_detail'),
    
    # Availability
    path('team/<int:pk>/availability/', AvailabilityManagementView.as_view(), name='availability_manage'),
    
    # Matchmaking & Requests
    path('match/find/', MatchFinderView.as_view(), name='match_finder'),
]
