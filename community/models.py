from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import uuid


class Community(models.Model):
    """Represents a neighborhood or community area"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='created_communities')
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Communities"
        ordering = ['name']

    def __str__(self):
        return self.name


class CustomUser(AbstractUser):
    """Extended user model with location and community assignment"""
    ROLE_CHOICES = [
        ('member', 'Community Member'),
        ('moderator', 'Moderator'),
        ('admin', 'Administrator'),
    ]
    
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='member')
    communities = models.ManyToManyField(Community, related_name='members', blank=True)
    
    # Email verification
    email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=100, blank=True)
    
    # Notification preferences
    email_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email


class AlertCategory(models.Model):
    """Categories for different types of security alerts"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)  # CSS class or icon name
    color = models.CharField(max_length=7, default='#007bff')  # Hex color
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name_plural = "Alert Categories"
        ordering = ['name']

    def __str__(self):
        return self.name


class Alert(models.Model):
    """Main model for security alerts"""
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('resolved', 'Resolved'),
        ('false_alarm', 'False Alarm'),
        ('under_review', 'Under Review'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(AlertCategory, on_delete=models.CASCADE, related_name='alerts')
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='medium')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='active')
    
    # Community information
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='alerts')
    address = models.CharField(max_length=300, blank=True, help_text="Optional specific address or location description")
    
    # User information
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='created_alerts')
    updated_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='updated_alerts', null=True, blank=True)
    
    # Timestamps
    incident_datetime = models.DateTimeField(help_text="When the incident occurred")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    # Engagement metrics
    view_count = models.PositiveIntegerField(default=0)
    upvotes = models.PositiveIntegerField(default=0)
    downvotes = models.PositiveIntegerField(default=0)
    
    # Visibility
    is_public = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)  # Verified by moderators

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['severity', 'status']),
            models.Index(fields=['community', 'status']),
        ]

    def __str__(self):
        return f"{self.title} - {self.severity}"

    @property
    def is_critical(self):
        return self.severity == 'critical'


class AlertMedia(models.Model):
    """Media files attached to alerts (photos, videos)"""
    MEDIA_TYPES = [
        ('image', 'Image'),
        ('video', 'Video'),
    ]
    
    alert = models.ForeignKey(Alert, on_delete=models.CASCADE, related_name='media')
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPES)
    file = models.FileField(upload_to='alert_media/%Y/%m/%d/')
    caption = models.CharField(max_length=300, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['uploaded_at']

    def __str__(self):
        return f"{self.media_type} for {self.alert.title}"


class AlertVote(models.Model):
    """User votes on alerts (upvote/downvote)"""
    VOTE_CHOICES = [
        ('up', 'Upvote'),
        ('down', 'Downvote'),
    ]
    
    alert = models.ForeignKey(Alert, on_delete=models.CASCADE, related_name='votes')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    vote_type = models.CharField(max_length=4, choices=VOTE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['alert', 'user']


class Notification(models.Model):
    """Notification tracking for alerts"""
    NOTIFICATION_TYPES = [
        ('email', 'Email'),
        ('push', 'Push Notification'),
        ('sms', 'SMS'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('delivered', 'Delivered'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    alert = models.ForeignKey(Alert, on_delete=models.CASCADE, related_name='notifications')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=10, choices=NOTIFICATION_TYPES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    # For tracking email/push notification IDs
    external_id = models.CharField(max_length=200, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'notification_type']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.notification_type} to {self.user.email} - {self.status}"


class AlertComment(models.Model):
    """Comments on alerts for community discussion"""
    alert = models.ForeignKey(Alert, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    content = models.TextField()
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.user.username} on {self.alert.title}"


class PushNotificationDevice(models.Model):
    """Store FCM device tokens for push notifications"""
    DEVICE_TYPES = [
        ('android', 'Android'),
        ('ios', 'iOS'),
        ('web', 'Web Browser'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='devices')
    device_token = models.TextField(unique=True)
    device_type = models.CharField(max_length=10, choices=DEVICE_TYPES, default='web')
    device_name = models.CharField(max_length=200, blank=True)  # e.g., "Chrome on Windows"
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_used = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'device_token']
        ordering = ['-last_used']
    
    def __str__(self):
        return f"{self.user.username} - {self.device_type} - {self.device_name or 'Unknown Device'}"
