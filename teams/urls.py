# from django.urls import path
# from django.contrib.auth.decorators import login_required
# from django.shortcuts import render
# from .views import (
#     DashboardView, 
#     TeamCreateView, 
#     TeamUpdateView,
#     AvailabilityManagementView,
#     MatchRequestDetailView
# )

# app_name = 'teams'
# urlpatterns = [
#     # Main Dashboard
#     path('dashboard/', login_required(DashboardView.as_view()), name='dashboard'),
    
#     # Team Management Views
#     path('team/create/', TeamCreateView.as_view(), name='team_create'),
#     path('team/edit/<int:pk>/', TeamUpdateView.as_view(), name='team_edit'),
    
#     # Availability Management
#     path('team/availability/<int:pk>/', login_required(AvailabilityManagementView.as_view()), name='availability_manage'),
    
#     # Match Finder (uses a simple function-based wrapper to render a static template)
#     path('match-finder/', login_required(lambda request: render(request, 'teams/match_finder.html')), name='match_finder'),

#     # Match Request Details & Chat
#     path('request/<int:pk>/', login_required(MatchRequestDetailView.as_view()), name='match_request_detail'),
# ]

from django.urls import path
from .views import (
    # Auth Views
    RegisterView,
    CustomLoginView,
    CustomLogoutView,
    
    # App Views
    ProfileView,
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
    path('dashboard/', DashboardView.as_view(), name='dashboard'), 
    
    # Team CRUD
    path('team/create/', TeamCreateView.as_view(), name='team_create'),
    path('team/<int:pk>/edit/', TeamUpdateView.as_view(), name='team_edit'),
    
    # Availability
    path('team/<int:pk>/availability/', AvailabilityManagementView.as_view(), name='availability_manage'),
    
    # Matchmaking & Requests
    path('match/find/', MatchFinderView.as_view(), name='match_finder'),
    path('match/request/<int:pk>/', MatchRequestDetailView.as_view(), name='match_request_detail'),
]

