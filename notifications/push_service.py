"""
Push Notification Service using Firebase Cloud Messaging (FCM)
"""

from django.conf import settings
from django.utils import timezone
from community.models import CustomUser, PushNotificationDevice, Notification
from pyfcm import FCMNotification
import logging
import json

logger = logging.getLogger(__name__)


class PushNotificationService:
    """Service for handling Firebase push notifications"""
    
    def __init__(self):
        self.fcm_server_key = getattr(settings, 'FCM_SERVER_KEY', '')
        self.push_service = None
        
        if self.fcm_server_key:
            try:
                self.push_service = FCMNotification(api_key=self.fcm_server_key)
            except Exception as e:
                logger.error(f"Failed to initialize FCM service: {e}")
        else:
            logger.warning("FCM_SERVER_KEY not configured - push notifications disabled")
    
    def is_available(self):
        """Check if push notification service is available"""
        return self.push_service is not None
    
    def register_device(self, user, device_token, device_type='web', device_name=''):
        """Register a device token for a user"""
        try:
            device, created = PushNotificationDevice.objects.update_or_create(
                user=user,
                device_token=device_token,
                defaults={
                    'device_type': device_type,
                    'device_name': device_name,
                    'is_active': True,
                    'last_used': timezone.now()
                }
            )
            
            if created:
                logger.info(f"Registered new device for {user.username}: {device_type}")
            else:
                logger.info(f"Updated device registration for {user.username}: {device_type}")
            
            return device
            
        except Exception as e:
            logger.error(f"Failed to register device for {user.username}: {e}")
            return None
    
    def unregister_device(self, user, device_token):
        """Unregister a device token"""
        try:
            PushNotificationDevice.objects.filter(
                user=user,
                device_token=device_token
            ).delete()
            
            logger.info(f"Unregistered device for {user.username}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unregister device for {user.username}: {e}")
            return False
    
    def get_user_devices(self, user):
        """Get all active devices for a user"""
        return PushNotificationDevice.objects.filter(
            user=user,
            is_active=True
        )
    
    def send_push_notification(self, user, title, body, data=None, alert=None):
        """Send push notification to all user devices"""
        if not self.is_available():
            logger.warning("Push notification service not available")
            return False
        
        if not user.push_notifications:
            logger.info(f"Push notifications disabled for user {user.username}")
            return False
        
        devices = self.get_user_devices(user)
        if not devices.exists():
            logger.info(f"No devices registered for user {user.username}")
            return False
        
        # Prepare notification data
        notification_data = data or {}
        if alert:
            notification_data.update({
                'alert_id': str(alert.id),
                'alert_title': alert.title,
                'alert_severity': alert.severity,
                'community': alert.community.name,
                'category': alert.category.name,
                'url': f"/alerts/{alert.id}/",
                'type': 'alert_notification'
            })
        
        success_count = 0
        failed_tokens = []
        
        device_tokens = list(devices.values_list('device_token', flat=True))
        
        try:
            # Send to multiple devices
            result = self.push_service.notify_multiple_devices(
                registration_ids=device_tokens,
                message_title=title,
                message_body=body,
                data_message=notification_data,
                sound='default',
                badge=1,
                click_action="/alerts/" if alert else "/",
                time_to_live=86400,  # 24 hours
            )
            
            # Process results
            if result and 'results' in result:
                for i, device_result in enumerate(result['results']):
                    if 'error' in device_result:
                        failed_tokens.append(device_tokens[i])
                        logger.error(f"Failed to send to device {i}: {device_result['error']}")
                    else:
                        success_count += 1
            
            # Clean up invalid tokens
            if failed_tokens:
                PushNotificationDevice.objects.filter(
                    device_token__in=failed_tokens
                ).update(is_active=False)
                
                logger.info(f"Deactivated {len(failed_tokens)} invalid device tokens")
            
            # Create notification record
            if alert:
                Notification.objects.create(
                    alert=alert,
                    user=user,
                    notification_type='push',
                    title=title,
                    message=body,
                    status='sent' if success_count > 0 else 'failed',
                    sent_at=timezone.now() if success_count > 0 else None,
                    external_id=json.dumps(result) if result else None
                )
            
            logger.info(f"Push notification sent to {success_count}/{len(device_tokens)} devices for {user.username}")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Failed to send push notification to {user.username}: {e}")
            
            # Create failed notification record
            if alert:
                Notification.objects.create(
                    alert=alert,
                    user=user,
                    notification_type='push',
                    title=title,
                    message=body,
                    status='failed'
                )
            
            return False
    
    def send_alert_notification(self, alert, users=None):
        """Send push notifications for an alert to specified users or community members"""
        if not self.is_available():
            return 0
        
        if users is None:
            # Get community members with push notifications enabled
            users = CustomUser.objects.filter(
                communities=alert.community,
                push_notifications=True,
                is_active=True
            )
        
        # Prepare notification content
        severity_emoji = {
            'low': '🟢',
            'medium': '🟡', 
            'high': '🟠',
            'critical': '🔴'
        }
        
        emoji = severity_emoji.get(alert.severity, '⚠️')
        title = f"{emoji} {alert.get_severity_display()} Alert - {alert.community.name}"
        body = f"{alert.category.name}: {alert.title}"
        
        success_count = 0
        
        for user in users:
            try:
                if self.send_push_notification(user, title, body, alert=alert):
                    success_count += 1
            except Exception as e:
                logger.error(f"Failed to send push notification to {user.username}: {e}")
        
        logger.info(f"Sent push notifications to {success_count}/{users.count()} users for alert: {alert.title}")
        return success_count
    
    def send_test_notification(self, user):
        """Send a test push notification"""
        if not self.is_available():
            return False, "Push notification service not available"
        
        if not user.push_notifications:
            return False, "Push notifications disabled for user"
        
        devices = self.get_user_devices(user)
        if not devices.exists():
            return False, "No devices registered for push notifications"
        
        title = "🔔 Test Notification"
        body = f"Hello {user.get_full_name() or user.username}! Your push notifications are working correctly."
        
        data = {
            'type': 'test_notification',
            'timestamp': timezone.now().isoformat()
        }
        
        success = self.send_push_notification(user, title, body, data=data)
        
        if success:
            return True, f"Test notification sent to {devices.count()} device(s)"
        else:
            return False, "Failed to send test notification"
    
    def cleanup_invalid_tokens(self):
        """Clean up invalid or old device tokens"""
        try:
            # Deactivate devices not used in 30 days
            cutoff_date = timezone.now() - timezone.timedelta(days=30)
            old_devices = PushNotificationDevice.objects.filter(
                last_used__lt=cutoff_date,
                is_active=True
            )
            
            count = old_devices.update(is_active=False)
            logger.info(f"Deactivated {count} old device tokens")
            
            return count
            
        except Exception as e:
            logger.error(f"Failed to cleanup device tokens: {e}")
            return 0


# Global instance
push_service = PushNotificationService()