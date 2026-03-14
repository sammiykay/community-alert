from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from notifications import views as notification_views

urlpatterns = [
    # Home and alert listing
    path('', views.home, name='home'),
    path('alerts/', views.alert_list, name='alert_list'),
    path('alerts/<uuid:alert_id>/', views.alert_detail, name='alert_detail'),
    path('alerts/create/', views.create_alert, name='create_alert'),
    path('alerts/<uuid:alert_id>/edit/', views.edit_alert, name='edit_alert'),
    path('alerts/<uuid:alert_id>/vote/', views.vote_alert, name='vote_alert'),
    path('alerts/my-communities/', views.my_community_alerts, name='my_community_alerts'),
    
    # Community pages
    path('communities/<uuid:community_id>/', views.community_detail, name='community_detail'),
    
    # Admin management
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    
    # Admin community management
    path('admin/communities/', views.manage_communities, name='manage_communities'),
    path('admin/communities/create/', views.create_community, name='create_community'),
    path('admin/communities/<uuid:community_id>/edit/', views.edit_community, name='edit_community'),
    path('admin/communities/<uuid:community_id>/toggle/', views.toggle_community_status, name='toggle_community_status'),
    
    # Admin category management
    path('admin/categories/', views.manage_categories, name='manage_categories'),
    path('admin/categories/create/', views.create_category, name='create_category'),
    path('admin/categories/<int:category_id>/edit/', views.edit_category, name='edit_category'),
    path('admin/categories/<int:category_id>/toggle/', views.toggle_category_status, name='toggle_category_status'),
    
    # Admin user management
    path('admin/users/', views.manage_users, name='manage_users'),
    path('admin/users/<int:user_id>/edit/', views.edit_user, name='edit_user'),
    
    # Superuser management
    path('superuser/', views.superuser_dashboard, name='superuser_dashboard'),
    path('superuser/admins/', views.manage_admin_users, name='manage_admin_users'),
    path('superuser/admins/create/', views.create_admin_user, name='create_admin_user'),
    path('superuser/admins/<int:user_id>/toggle/', views.toggle_admin_status, name='toggle_admin_status'),
    
    # User management
    path('register/', views.register, name='register'),
    path('profile/', views.user_profile, name='user_profile'),
    path('test-notification/', views.test_notification, name='test_notification'),
    
    # Push notification device management
    path('push/register/', notification_views.register_device, name='register_device'),
    path('push/unregister/', notification_views.unregister_device, name='unregister_device'),
    path('push/devices/', notification_views.list_user_devices, name='list_user_devices'),
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