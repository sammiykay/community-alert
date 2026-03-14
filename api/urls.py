from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    # Alert endpoints
    path('alerts/', views.api_alerts_list, name='alerts_list'),
    path('alerts/<uuid:alert_id>/', views.api_alert_detail, name='alert_detail'),
    path('alerts/create/', views.api_create_alert, name='create_alert'),
    path('alerts/community/', views.api_community_alerts, name='community_alerts'),
    
    # Community endpoints
    path('communities/', views.api_communities_list, name='communities_list'),
    
    # Category endpoints
    path('categories/', views.api_categories_list, name='categories_list'),
    
    # User endpoints
    path('user/profile/', views.api_user_profile, name='user_profile'),
    path('test-notification/', views.api_test_notification, name='test_notification'),
    
    # System endpoints
    path('stats/', views.api_stats, name='stats'),
]