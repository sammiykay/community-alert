from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    CustomUser, Community, AlertCategory, Alert, 
    AlertMedia, AlertVote, Notification, AlertComment
)


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['email', 'username', 'role', 'email_verified', 'created_at']
    list_filter = ['role', 'email_verified', 'created_at']
    search_fields = ['email', 'username']
    ordering = ['-created_at']
    
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('phone_number', 'role', 'email_verified', 'communities')
        }),
        ('Notifications', {
            'fields': ('email_notifications', 'push_notifications')
        }),
    )


@admin.register(Community)
class CommunityAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_by', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['name']


@admin.register(AlertCategory)
class AlertCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'color', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']
    ordering = ['name']


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'severity', 'status', 'created_by', 'community', 'created_at']
    list_filter = ['severity', 'status', 'category', 'is_verified', 'created_at']
    search_fields = ['title', 'description', 'address']
    ordering = ['-created_at']
    readonly_fields = ['view_count', 'upvotes', 'downvotes']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'category', 'severity', 'status')
        }),
        ('Location', {
            'fields': ('address', 'community')
        }),
        ('Metadata', {
            'fields': ('incident_datetime', 'created_by', 'updated_by', 'is_public', 'is_verified')
        }),
        ('Engagement', {
            'fields': ('view_count', 'upvotes', 'downvotes'),
            'classes': ('collapse',)
        }),
    )


@admin.register(AlertMedia)
class AlertMediaAdmin(admin.ModelAdmin):
    list_display = ['alert', 'media_type', 'uploaded_at']
    list_filter = ['media_type', 'uploaded_at']
    search_fields = ['alert__title', 'caption']
    ordering = ['-uploaded_at']


@admin.register(AlertVote)
class AlertVoteAdmin(admin.ModelAdmin):
    list_display = ['alert', 'user', 'vote_type', 'created_at']
    list_filter = ['vote_type', 'created_at']
    ordering = ['-created_at']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'notification_type', 'status', 'created_at']
    list_filter = ['notification_type', 'status', 'created_at']
    search_fields = ['title', 'message', 'user__email']
    ordering = ['-created_at']


@admin.register(AlertComment)
class AlertCommentAdmin(admin.ModelAdmin):
    list_display = ['alert', 'user', 'created_at', 'is_deleted']
    list_filter = ['is_deleted', 'created_at']
    search_fields = ['content', 'user__username', 'alert__title']
    ordering = ['-created_at']
