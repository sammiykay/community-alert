from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Home and alert listing
    path('', views.home, name='home'),
    path('alerts/', views.alert_list, name='alert_list'),
    path('alerts/<uuid:alert_id>/', views.alert_detail, name='alert_detail'),
    path('alerts/create/', views.create_alert, name='create_alert'),
    path('alerts/<uuid:alert_id>/edit/', views.edit_alert, name='edit_alert'),
    path('alerts/<uuid:alert_id>/vote/', views.vote_alert, name='vote_alert'),
    path('alerts/nearby/', views.nearby_alerts, name='nearby_alerts'),
    
    # Community pages
    path('communities/<uuid:community_id>/', views.community_detail, name='community_detail'),
    
    # User management
    path('register/', views.register, name='register'),
    path('profile/', views.user_profile, name='user_profile'),
    path('debug-headers/', views.debug_headers, name='debug_headers'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Password reset
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='registration/password_reset.html'
    ), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html'
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/password_reset_confirm.html'
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html'
    ), name='password_reset_complete'),
]