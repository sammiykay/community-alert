from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from community.models import CustomUser, Alert, Notification, PushNotificationDevice
from .push_service import push_service
import math


class NotificationService:
    """Service for handling notifications"""
    
    @staticmethod
    def send_alert_notification(alert, notification_types=['email', 'push']):
        """Send notification about new alert to community members"""
        try:
            # Find users who should be notified (community members)
            users_to_notify = NotificationService.get_community_members(alert.community)
            
            email_sent = 0
            push_sent = 0
            
            for user in users_to_notify:
                # Send email notification
                if 'email' in notification_types and user.email_notifications:
                    success = NotificationService.send_email_notification(user, alert)
                    if success:
                        email_sent += 1
                
                # Send push notification
                if 'push' in notification_types and user.push_notifications:
                    success = NotificationService.send_push_notification(user, alert)
                    if success:
                        push_sent += 1
            
            total_sent = email_sent + push_sent
            print(f"Sent {email_sent} email and {push_sent} push notifications for alert: {alert.title}")
            return total_sent
            
        except Exception as e:
            print(f"Error sending notifications: {e}")
            return 0
    
    @staticmethod
    def get_community_members(community):
        """Get all active members of a community who want notifications"""
        return CustomUser.objects.filter(
            communities=community,
            email_notifications=True,
            is_active=True
        )
    
    @staticmethod
    def send_email_notification(user, alert):
        """Send email notification to user about alert"""
        try:
            subject = f"[Community Alert] {alert.get_severity_display()}: {alert.title}"
            
            message = f"""
Dear {user.get_full_name() or user.username},

A new {alert.get_severity_display().lower()} security alert has been reported in your community:

ALERT DETAILS:
Title: {alert.title}
Category: {alert.category.name}
Severity: {alert.get_severity_display()}
Location: {alert.address or 'No specific address provided'}
Community: {alert.community.name}
Reported: {alert.created_at.strftime("%B %d, %Y at %I:%M %p")}

DESCRIPTION:
{alert.description}

WHAT TO DO:
• Stay alert and aware of your surroundings
• Report any additional information to local authorities if relevant
• If this is an emergency, call emergency services immediately

View full details and community discussion at:
{settings.BASE_URL if hasattr(settings, 'BASE_URL') else 'http://localhost:8000'}/alerts/{alert.id}/

---
Community Alert System - {alert.community.name}
To adjust your notification preferences, visit your profile settings.
            """
            
            # Create notification record
            notification = Notification.objects.create(
                alert=alert,
                user=user,
                notification_type='email',
                title=subject,
                message=message,
                status='pending'
            )
            
            # Send email (only if email settings are configured)
            if settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False
                )
                
                notification.status = 'sent'
                notification.sent_at = timezone.now()
            else:
                notification.status = 'failed'
                notification.message = "Email configuration not available"
                
            notification.save()
            return notification.status == 'sent'
            
        except Exception as e:
            print(f"Failed to send email to {user.email}: {e}")
            return False
    
    @staticmethod
    def send_push_notification(user, alert):
        """Send push notification to user about alert"""
        try:
            if not push_service.is_available():
                print("Push notification service not available")
                return False
            
            # Prepare notification content
            severity_emoji = {
                'low': '🟢',
                'medium': '🟡', 
                'high': '🟠',
                'critical': '🔴'
            }
            
            emoji = severity_emoji.get(alert.severity, '⚠️')
            title = f"{emoji} {alert.get_severity_display()} Alert"
            body = f"{alert.community.name}: {alert.title}"
            
            success = push_service.send_push_notification(user, title, body, alert=alert)
            return success
            
        except Exception as e:
            print(f"Failed to send push notification to {user.username}: {e}")
            return False


@login_required
@require_http_methods(["GET"])
def user_notifications(request):
    """Get user's notifications"""
    try:
        notifications = Notification.objects.filter(
            user=request.user
        ).select_related('alert').order_by('-created_at')[:50]
        
        notifications_data = [{
            'id': str(notification.id),
            'title': notification.title,
            'message': notification.message,
            'notification_type': notification.notification_type,
            'status': notification.status,
            'created_at': notification.created_at.isoformat(),
            'sent_at': notification.sent_at.isoformat() if notification.sent_at else None,
            'alert': {
                'id': str(notification.alert.id),
                'title': notification.alert.title,
                'severity': notification.alert.severity,
                'status': notification.alert.status
            } if notification.alert else None
        } for notification in notifications]
        
        return JsonResponse({
            'success': True,
            'data': notifications_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def test_notification(request):
    """Test notification system by sending a test notification"""
    try:
        user = request.user
        
        results = []
        success_count = 0
        
        # Test email notifications
        if user.email_notifications:
            if settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD:
                try:
                    email_success = send_mail(
                        subject='Test Email - Community Alert System',
                        message=f'This is a test email for {user.get_full_name() or user.username}. Your email notifications are working correctly!',
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        fail_silently=False
                    )
                    
                    if email_success:
                        results.append('✅ Email notification sent successfully')
                        success_count += 1
                        
                        # Create notification record
                        Notification.objects.create(
                            user=user,
                            notification_type='email',
                            title='Test Email - Community Alert System',
                            message='Test email sent successfully',
                            status='sent',
                            sent_at=timezone.now()
                        )
                    else:
                        results.append('❌ Email notification failed to send')
                        
                except Exception as e:
                    results.append(f'❌ Email notification error: {str(e)}')
            else:
                results.append('⚠️ Email not configured (missing credentials)')
        else:
            results.append('⚠️ Email notifications disabled by user')
        
        # Test push notifications
        if user.push_notifications:
            if push_service.is_available():
                try:
                    push_success, push_message = push_service.send_test_notification(user)
                    
                    if push_success:
                        results.append(f'✅ {push_message}')
                        success_count += 1
                    else:
                        results.append(f'❌ Push notification failed: {push_message}')
                        
                except Exception as e:
                    results.append(f'❌ Push notification error: {str(e)}')
            else:
                results.append('⚠️ Push notifications not configured (missing FCM key)')
        else:
            results.append('⚠️ Push notifications disabled by user')
        
        return JsonResponse({
            'success': success_count > 0,
            'message': f'Test completed: {success_count} notification(s) sent successfully',
            'results': results,
            'details': {
                'email_enabled': user.email_notifications,
                'push_enabled': user.push_notifications,
                'email_configured': bool(settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD),
                'push_configured': push_service.is_available(),
                'device_count': PushNotificationDevice.objects.filter(user=user, is_active=True).count()
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def trigger_alert_notifications(alert):
    """
    Trigger notifications for a new alert
    This function should be called when a new alert is created
    """
    if alert.is_public:
        # Send notifications for all public alerts regardless of severity
        notifications_sent = NotificationService.send_alert_notification(alert)
        print(f"Sent {notifications_sent} notifications for alert: {alert.title}")
        return notifications_sent
    return 0


# ============================================================================
# PUSH NOTIFICATION DEVICE MANAGEMENT
# ============================================================================

@login_required
@require_http_methods(["POST"])
def register_device(request):
    """Register a device token for push notifications"""
    try:
        import json
        
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
        
        device_token = data.get('device_token')
        device_type = data.get('device_type', 'web')
        device_name = data.get('device_name', '')
        
        if not device_token:
            return JsonResponse({
                'success': False,
                'error': 'Device token is required'
            }, status=400)
        
        device = push_service.register_device(
            user=request.user,
            device_token=device_token,
            device_type=device_type,
            device_name=device_name
        )
        
        if device:
            return JsonResponse({
                'success': True,
                'message': 'Device registered successfully',
                'device_id': device.id
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Failed to register device'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def unregister_device(request):
    """Unregister a device token"""
    try:
        import json
        
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
        
        device_token = data.get('device_token')
        
        if not device_token:
            return JsonResponse({
                'success': False,
                'error': 'Device token is required'
            }, status=400)
        
        success = push_service.unregister_device(request.user, device_token)
        
        return JsonResponse({
            'success': success,
            'message': 'Device unregistered successfully' if success else 'Failed to unregister device'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def list_user_devices(request):
    """List user's registered devices"""
    try:
        devices = PushNotificationDevice.objects.filter(
            user=request.user,
            is_active=True
        ).order_by('-last_used')
        
        devices_data = [{
            'id': device.id,
            'device_type': device.device_type,
            'device_name': device.device_name,
            'created_at': device.created_at.isoformat(),
            'last_used': device.last_used.isoformat()
        } for device in devices]
        
        return JsonResponse({
            'success': True,
            'devices': devices_data,
            'total': devices.count()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
