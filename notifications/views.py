from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from community.models import CustomUser, Alert, Notification
import math


class NotificationService:
    """Service for handling notifications"""
    
    @staticmethod
    def send_alert_notification(alert, notification_type='email'):
        """Send notification about new alert to relevant users"""
        try:
            # Find users who should be notified based on location and preferences
            users_to_notify = NotificationService.get_users_in_radius(
                alert.latitude, 
                alert.longitude, 
                alert.community
            )
            
            notifications_sent = 0
            
            for user in users_to_notify:
                if notification_type == 'email' and user.email_notifications:
                    success = NotificationService.send_email_notification(user, alert)
                    if success:
                        notifications_sent += 1
                        
            return notifications_sent
            
        except Exception as e:
            print(f"Error sending notifications: {e}")
            return 0
    
    @staticmethod
    def get_users_in_radius(latitude, longitude, community, max_radius_km=10):
        """Get users within notification radius of the alert location"""
        users = CustomUser.objects.filter(
            communities=community,
            email_notifications=True,
            is_active=True
        ).exclude(latitude__isnull=True, longitude__isnull=True)
        
        users_in_radius = []
        
        for user in users:
            distance = NotificationService.calculate_distance(
                float(latitude), float(longitude),
                float(user.latitude), float(user.longitude)
            )
            
            user_radius = min(user.notification_radius_km, max_radius_km)
            if distance <= user_radius:
                users_in_radius.append(user)
                
        return users_in_radius
    
    @staticmethod
    def calculate_distance(lat1, lon1, lat2, lon2):
        """Calculate distance between two points in kilometers"""
        # Simple Haversine formula approximation
        R = 6371  # Earth's radius in kilometers
        
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = (math.sin(dlat/2) * math.sin(dlat/2) + 
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
             math.sin(dlon/2) * math.sin(dlon/2))
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = R * c
        
        return distance
    
    @staticmethod
    def send_email_notification(user, alert):
        """Send email notification to user about alert"""
        try:
            subject = f"[Community Alert] {alert.get_severity_display()}: {alert.title}"
            
            message = f"""
Dear {user.get_full_name() or user.username},

A new {alert.get_severity_display().lower()} security alert has been reported in your area:

ALERT DETAILS:
Title: {alert.title}
Category: {alert.category.name}
Severity: {alert.get_severity_display()}
Location: {alert.address or f"Coordinates: {alert.latitude}, {alert.longitude}"}
Community: {alert.community.name}
Reported: {alert.created_at.strftime("%B %d, %Y at %I:%M %p")}

DESCRIPTION:
{alert.description}

WHAT TO DO:
• Stay alert and aware of your surroundings
• Report any additional information to local authorities if relevant
• If this is an emergency, call 911 immediately

View full details and community discussion at:
{settings.BASE_URL if hasattr(settings, 'BASE_URL') else 'http://localhost:8000'}/alerts/{alert.id}/

---
Community Alert System
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
        
        # Create a test notification
        notification = Notification.objects.create(
            user=user,
            notification_type='email',
            title='Test Notification - Community Alert System',
            message=f'This is a test notification for {user.get_full_name() or user.username}. Your notification settings are working correctly!',
            status='pending'
        )
        
        # Try to send test email if email is configured
        if settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD and user.email_notifications:
            success = send_mail(
                subject=notification.title,
                message=notification.message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False
            )
            
            if success:
                notification.status = 'sent'
                notification.sent_at = timezone.now()
            else:
                notification.status = 'failed'
        else:
            notification.status = 'failed'
            notification.message += ' (Email not configured or user email notifications disabled)'
            
        notification.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Test notification created',
            'notification_status': notification.status
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
    if alert.is_public and alert.severity in ['high', 'critical']:
        # Send notifications for high and critical alerts
        notifications_sent = NotificationService.send_alert_notification(alert)
        print(f"Sent {notifications_sent} notifications for alert: {alert.title}")
        return notifications_sent
    return 0
