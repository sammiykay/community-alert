from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # Notification management
    path('notifications/', views.user_notifications, name='user_notifications'),
    path('test-notification/', views.test_notification, name='test_notification'),
    
    # Push notification device management
    path('push/register/', views.register_device, name='register_device'),
    path('push/unregister/', views.unregister_device, name='unregister_device'),
    path('push/devices/', views.list_user_devices, name='list_user_devices'),
]