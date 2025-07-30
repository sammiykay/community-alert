from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Q, F
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from .models import Alert, AlertCategory, Community, CustomUser, AlertVote
from .forms import (
    UserRegistrationForm, AlertForm, UserProfileForm, UserNotificationForm, CommunityForm,
    AlertCategoryForm, AdminUserForm, CreateAdminUserForm
)
import math


def home(request):
    """Home page showing recent alerts"""
    alerts = Alert.objects.filter(
        is_public=True, 
        status='active'
    ).select_related('category', 'community', 'created_by').order_by('-created_at')[:10]
    
    # Get alert statistics
    total_alerts = Alert.objects.filter(is_public=True).count()
    active_alerts = Alert.objects.filter(is_public=True, status='active').count()
    resolved_alerts = Alert.objects.filter(is_public=True, status='resolved').count()
    
    context = {
        'alerts': alerts,
        'total_alerts': total_alerts,
        'active_alerts': active_alerts,
        'resolved_alerts': resolved_alerts,
    }
    return render(request, 'community/home.html', context)


def alert_list(request):
    """List all public alerts with filtering"""
    alerts = Alert.objects.filter(is_public=True).select_related(
        'category', 'community', 'created_by'
    ).order_by('-created_at')
    
    # Filtering
    category_id = request.GET.get('category')
    severity = request.GET.get('severity')
    status = request.GET.get('status')
    community_id = request.GET.get('community')
    search = request.GET.get('search')
    
    if category_id:
        alerts = alerts.filter(category_id=category_id)
    if severity:
        alerts = alerts.filter(severity=severity)
    if status:
        alerts = alerts.filter(status=status)
    if community_id:
        alerts = alerts.filter(community_id=community_id)
    if search:
        alerts = alerts.filter(
            Q(title__icontains=search) | 
            Q(description__icontains=search) |
            Q(address__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(alerts, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get filter options
    categories = AlertCategory.objects.filter(is_active=True)
    communities = Community.objects.filter(is_active=True)
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'communities': communities,
        'current_filters': {
            'category': category_id,
            'severity': severity,
            'status': status,
            'community': community_id,
            'search': search,
        }
    }
    return render(request, 'community/alert_list.html', context)


def alert_detail(request, alert_id):
    """Display detailed view of an alert"""
    alert = get_object_or_404(
        Alert.objects.select_related('category', 'community', 'created_by'),
        id=alert_id,
        is_public=True
    )
    
    # Increment view count
    Alert.objects.filter(id=alert_id).update(view_count=F('view_count') + 1)
    
    # Get user's vote if logged in
    user_vote = None
    if request.user.is_authenticated:
        try:
            user_vote = AlertVote.objects.get(alert=alert, user=request.user).vote_type
        except AlertVote.DoesNotExist:
            pass
    
    # Get comments
    comments = alert.comments.filter(is_deleted=False, parent=None).select_related('user').order_by('created_at')
    
    context = {
        'alert': alert,
        'user_vote': user_vote,
        'comments': comments,
    }
    return render(request, 'community/alert_detail.html', context)


@login_required
def create_alert(request):
    """Create a new security alert"""
    # Check if user belongs to any communities
    if not request.user.communities.exists() and not request.user.is_staff:
        messages.error(request, 'You must be a member of at least one community to create alerts.')
        return redirect('user_profile')
    
    if request.method == 'POST':
        form = AlertForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            alert = form.save(commit=False)
            alert.created_by = request.user
            alert.save()
            
            # Trigger notifications for community members
            try:
                from notifications.views import trigger_alert_notifications
                notifications_sent = trigger_alert_notifications(alert)
                if notifications_sent > 0:
                    messages.success(request, f'Alert created successfully! {notifications_sent} community members have been notified.')
                else:
                    messages.success(request, 'Alert created successfully!')
            except ImportError:
                messages.success(request, 'Alert created successfully!')
            
            return redirect('alert_detail', alert_id=alert.id)
    else:
        form = AlertForm(user=request.user)
    
    return render(request, 'community/create_alert.html', {'form': form})


@login_required
def edit_alert(request, alert_id):
    """Edit an existing alert (only by creator or moderators)"""
    alert = get_object_or_404(Alert, id=alert_id)
    
    # Check permissions
    if alert.created_by != request.user and request.user.role not in ['moderator', 'admin']:
        messages.error(request, 'You do not have permission to edit this alert.')
        return redirect('alert_detail', alert_id=alert.id)
    
    if request.method == 'POST':
        form = AlertForm(request.POST, request.FILES, instance=alert, user=request.user)
        if form.is_valid():
            alert = form.save(commit=False)
            alert.updated_by = request.user
            alert.save()
            messages.success(request, 'Alert updated successfully!')
            return redirect('alert_detail', alert_id=alert.id)
    else:
        form = AlertForm(instance=alert, user=request.user)
    
    return render(request, 'community/edit_alert.html', {'form': form, 'alert': alert})


@login_required
@require_POST
def vote_alert(request, alert_id):
    """Vote on an alert (AJAX endpoint)"""
    alert = get_object_or_404(Alert, id=alert_id)
    vote_type = request.POST.get('vote_type')
    
    if vote_type not in ['up', 'down']:
        return JsonResponse({'error': 'Invalid vote type'}, status=400)
    
    vote, created = AlertVote.objects.get_or_create(
        alert=alert,
        user=request.user,
        defaults={'vote_type': vote_type}
    )
    
    if not created:
        if vote.vote_type == vote_type:
            # Remove vote if clicking same vote
            vote.delete()
            vote_type = None
        else:
            # Change vote
            vote.vote_type = vote_type
            vote.save()
    
    # Update alert vote counts
    upvotes = alert.votes.filter(vote_type='up').count()
    downvotes = alert.votes.filter(vote_type='down').count()
    
    Alert.objects.filter(id=alert_id).update(
        upvotes=upvotes,
        downvotes=downvotes
    )
    
    return JsonResponse({
        'success': True,
        'upvotes': upvotes,
        'downvotes': downvotes,
        'user_vote': vote_type
    })


def register(request):
    """User registration"""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Registration successful! Please log in.')
            return redirect('login')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'registration/register.html', {'form': form})


@login_required
def user_profile(request):
    """User profile management"""
    if request.method == 'POST':
        # Check if this is an AJAX request
        is_ajax = (
            request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
            request.content_type == 'application/json' or
            'application/json' in request.headers.get('Accept', '') or
            request.POST.get('action') in ['update_profile', 'update_notifications']
        )
        
        if is_ajax:
            try:
                action = request.POST.get('action')
                
                # Debug logging
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f'AJAX request detected - Action: {action}, Headers: {dict(request.headers)}')
                
                if action == 'update_profile':
                    # Update profile information
                    form = UserProfileForm(request.POST, instance=request.user)
                    if form.is_valid():
                        form.save()
                        return JsonResponse({
                            'success': True,
                            'message': 'Profile updated successfully!'
                        })
                    else:
                        # Debug logging
                        logger.info(f'Form validation failed. Errors: {form.errors}')
                        logger.info(f'Form data received: {dict(request.POST)}')
                        return JsonResponse({
                            'success': False,
                            'error': 'Please correct the form errors: ' + ', '.join([f'{field}: {", ".join(errors)}' for field, errors in form.errors.items()]),
                            'form_errors': form.errors
                        })
                
                elif action == 'update_notifications':
                    # Update notification preferences using the new form
                    form = UserNotificationForm(request.POST, instance=request.user)
                    if form.is_valid():
                        form.save()
                        return JsonResponse({
                            'success': True,
                            'message': 'Notification settings updated successfully!'
                        })
                    else:
                        logger.info(f'Notification form validation failed. Errors: {form.errors}')
                        logger.info(f'Form data received: {dict(request.POST)}')
                        return JsonResponse({
                            'success': False,
                            'error': 'Please correct the form errors: ' + ', '.join([f'{field}: {", ".join(errors)}' for field, errors in form.errors.items()]),
                            'form_errors': form.errors
                        })
                
                else:
                    return JsonResponse({
                        'success': False,
                        'error': 'Invalid action specified.'
                    })
                    
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'error': f'An error occurred: {str(e)}'
                })
        else:
            # Debug logging for non-AJAX requests
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f'Non-AJAX request - Action: {request.POST.get("action")}, Headers: {dict(request.headers)}')
        
        # Handle regular POST request (non-AJAX)
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('user_profile')
    else:
        form = UserProfileForm(instance=request.user)
    
    # Get user's alerts
    user_alerts = Alert.objects.filter(created_by=request.user).order_by('-created_at')[:5]
    
    context = {
        'form': form,
        'user_alerts': user_alerts,
    }
    return render(request, 'community/user_profile.html', context)


def community_detail(request, community_id):
    """Display community details and alerts"""
    community = get_object_or_404(Community, id=community_id, is_active=True)
    
    alerts = Alert.objects.filter(
        community=community,
        is_public=True
    ).select_related('category', 'created_by').order_by('-created_at')
    
    # Pagination
    paginator = Paginator(alerts, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Community statistics
    total_alerts = alerts.count()
    active_alerts = alerts.filter(status='active').count()
    member_count = community.members.count()
    
    context = {
        'community': community,
        'page_obj': page_obj,
        'total_alerts': total_alerts,
        'active_alerts': active_alerts,
        'member_count': member_count,
    }
    return render(request, 'community/community_detail.html', context)


@login_required
def my_community_alerts(request):
    """Show alerts from user's communities"""
    user = request.user
    
    # Get alerts from user's communities
    alerts = Alert.objects.filter(
        community__in=user.communities.all(),
        is_public=True,
        status='active'
    ).select_related('category', 'community', 'created_by').order_by('-created_at')
    
    # Get user's communities
    user_communities = user.communities.filter(is_active=True)
    
    context = {
        'alerts': alerts,
        'user_communities': user_communities,
    }
    return render(request, 'community/my_community_alerts.html', context)


@login_required
@require_POST
def test_notification(request):
    """Test notification endpoint for user profile"""
    try:
        # Simulate sending a test notification
        user = request.user
        
        # Check user's notification preferences
        if not user.email_notifications and not user.push_notifications:
            return JsonResponse({
                'success': False,
                'error': 'No notification methods enabled. Please enable email or push notifications first.'
            })
        
        # Simulate notification sending
        notification_status = []
        if user.email_notifications:
            notification_status.append('Email notification sent')
        if user.push_notifications:
            notification_status.append('Push notification sent')
        
        return JsonResponse({
            'success': True,
            'message': 'Test notification sent successfully!',
            'notification_status': ', '.join(notification_status)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to send test notification: {str(e)}'
        })


@login_required
@require_POST
def debug_headers(request):
    """Debug endpoint to check request headers"""
    return JsonResponse({
        'method': request.method,
        'content_type': request.content_type,
        'headers': dict(request.headers),
        'POST': dict(request.POST),
        'is_ajax_checks': {
            'X-Requested-With': request.headers.get('X-Requested-With'),
            'content_type': request.content_type,
            'accept_header': request.headers.get('Accept', ''),
            'action_in_post': request.POST.get('action'),
        }
    })


def is_admin(user):
    """Check if user is admin"""
    return user.is_authenticated and user.role == 'admin'

@user_passes_test(is_admin)
def create_community(request):
    """Create a new community (admin-only)"""
    if request.method == 'POST':
        form = CommunityForm(request.POST)
        if form.is_valid():
            community = form.save(commit=False)
            community.created_by = request.user
            community.save()
            messages.success(request, f'Community "{community.name}" created successfully!')
            return redirect('manage_communities')
    else:
        form = CommunityForm()
    
    return render(request, 'community/create_community.html', {'form': form})


@user_passes_test(is_admin)
def manage_communities(request):
    """Manage communities (admin-only)"""
    communities = Community.objects.all().order_by('name')
    
    # Pagination
    paginator = Paginator(communities, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'community/manage_communities.html', context)


@user_passes_test(is_admin)
def edit_community(request, community_id):
    """Edit a community (admin-only)"""
    community = get_object_or_404(Community, id=community_id)
    
    if request.method == 'POST':
        form = CommunityForm(request.POST, instance=community)
        if form.is_valid():
            form.save()
            messages.success(request, f'Community "{community.name}" updated successfully!')
            return redirect('manage_communities')
    else:
        form = CommunityForm(instance=community)
    
    return render(request, 'community/edit_community.html', {'form': form, 'community': community})


@user_passes_test(is_admin)
@require_POST
def toggle_community_status(request, community_id):
    """Toggle community active status (admin-only)"""
    community = get_object_or_404(Community, id=community_id)
    community.is_active = not community.is_active
    community.save()
    
    status = "activated" if community.is_active else "deactivated"
    messages.success(request, f'Community "{community.name}" has been {status}.')
    
    return redirect('manage_communities')


# ============================================================================
# ADMIN MANAGEMENT VIEWS
# ============================================================================

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    """Main admin dashboard with overview stats"""
    context = {
        'total_users': CustomUser.objects.count(),
        'total_communities': Community.objects.count(),
        'total_categories': AlertCategory.objects.count(),
        'total_alerts': Alert.objects.count(),
        'active_alerts': Alert.objects.filter(status='active').count(),
        'recent_alerts': Alert.objects.select_related('community', 'category', 'created_by').order_by('-created_at')[:5],
        'recent_users': CustomUser.objects.order_by('-date_joined')[:5],
        'admin_count': CustomUser.objects.filter(role='admin').count(),
        'moderator_count': CustomUser.objects.filter(role='moderator').count(),
    }
    return render(request, 'community/admin/dashboard.html', context)


# Category Management
@login_required
@user_passes_test(is_admin)
def manage_categories(request):
    """Manage alert categories (admin-only)"""
    categories = AlertCategory.objects.all().order_by('name')
    
    context = {
        'categories': categories,
        'total_categories': categories.count(),
        'active_categories': categories.filter(is_active=True).count(),
    }
    return render(request, 'community/admin/manage_categories.html', context)


@login_required
@user_passes_test(is_admin)
def create_category(request):
    """Create a new alert category (admin-only)"""
    if request.method == 'POST':
        form = AlertCategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Category "{category.name}" created successfully!')
            return redirect('manage_categories')
    else:
        form = AlertCategoryForm()
    
    return render(request, 'community/admin/create_category.html', {'form': form})


@login_required
@user_passes_test(is_admin)
def edit_category(request, category_id):
    """Edit an alert category (admin-only)"""
    category = get_object_or_404(AlertCategory, id=category_id)
    
    if request.method == 'POST':
        form = AlertCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f'Category "{category.name}" updated successfully!')
            return redirect('manage_categories')
    else:
        form = AlertCategoryForm(instance=category)
    
    return render(request, 'community/admin/edit_category.html', {
        'form': form, 
        'category': category
    })


@login_required
@user_passes_test(is_admin)
@require_POST
def toggle_category_status(request, category_id):
    """Toggle category active status (admin-only)"""
    category = get_object_or_404(AlertCategory, id=category_id)
    category.is_active = not category.is_active
    category.save()
    
    status = "activated" if category.is_active else "deactivated"
    messages.success(request, f'Category "{category.name}" has been {status}.')
    
    return redirect('manage_categories')


# User Management (Admin-only)
@login_required
@user_passes_test(is_admin)
def manage_users(request):
    """Manage users (admin-only)"""
    users = CustomUser.objects.select_related().order_by('-date_joined')
    
    # Filter by role if specified
    role_filter = request.GET.get('role')
    if role_filter:
        users = users.filter(role=role_filter)
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        users = users.filter(
            models.Q(username__icontains=search_query) |
            models.Q(email__icontains=search_query) |
            models.Q(first_name__icontains=search_query) |
            models.Q(last_name__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(users, 25)
    page_number = request.GET.get('page')
    users = paginator.get_page(page_number)
    
    context = {
        'users': users,
        'total_users': CustomUser.objects.count(),
        'role_filter': role_filter,
        'search_query': search_query,
        'role_choices': CustomUser.ROLE_CHOICES,
    }
    return render(request, 'community/admin/manage_users.html', context)


@login_required
@user_passes_test(is_admin)
def edit_user(request, user_id):
    """Edit user details and role (admin-only)"""
    user_to_edit = get_object_or_404(CustomUser, id=user_id)
    
    if request.method == 'POST':
        form = AdminUserForm(request.POST, instance=user_to_edit)
        if form.is_valid():
            form.save()
            messages.success(request, f'User "{user_to_edit.username}" updated successfully!')
            return redirect('manage_users')
    else:
        form = AdminUserForm(instance=user_to_edit)
    
    return render(request, 'community/admin/edit_user.html', {
        'form': form, 
        'user_to_edit': user_to_edit
    })


# ============================================================================
# SUPERUSER MANAGEMENT VIEWS
# ============================================================================

def is_superuser(user):
    """Check if user is superuser"""
    return user.is_authenticated and user.is_superuser


@login_required
@user_passes_test(is_superuser)
def superuser_dashboard(request):
    """Superuser dashboard with system-wide stats"""
    context = {
        'total_users': CustomUser.objects.count(),
        'total_admins': CustomUser.objects.filter(role='admin').count(),
        'total_moderators': CustomUser.objects.filter(role='moderator').count(),
        'total_members': CustomUser.objects.filter(role='member').count(),
        'total_communities': Community.objects.count(),
        'total_categories': AlertCategory.objects.count(),
        'total_alerts': Alert.objects.count(),
        'recent_users': CustomUser.objects.order_by('-date_joined')[:10],
        'recent_admins': CustomUser.objects.filter(role='admin').order_by('-date_joined')[:5],
    }
    return render(request, 'community/admin/superuser_dashboard.html', context)


@login_required
@user_passes_test(is_superuser)
def create_admin_user(request):
    """Create a new administrator user (superuser-only)"""
    if request.method == 'POST':
        form = CreateAdminUserForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = 'admin'  # Force admin role
            user.is_staff = True  # Allow Django admin access
            user.save()
            
            messages.success(request, f'Administrator "{user.username}" created successfully!')
            return redirect('superuser_dashboard')
    else:
        form = CreateAdminUserForm()
    
    return render(request, 'community/admin/create_admin_user.html', {'form': form})


@login_required
@user_passes_test(is_superuser)
def manage_admin_users(request):
    """Manage administrator users (superuser-only)"""
    admins = CustomUser.objects.filter(
        models.Q(role='admin') | models.Q(is_superuser=True)
    ).order_by('-date_joined')
    
    context = {
        'admins': admins,
        'total_admins': admins.filter(role='admin').count(),
        'total_superusers': admins.filter(is_superuser=True).count(),
    }
    return render(request, 'community/admin/manage_admin_users.html', context)


@login_required
@user_passes_test(is_superuser)
@require_POST
def toggle_admin_status(request, user_id):
    """Toggle user admin status (superuser-only)"""
    user = get_object_or_404(CustomUser, id=user_id)
    
    if user == request.user:
        messages.error(request, "You cannot modify your own admin status.")
        return redirect('manage_admin_users')
    
    if user.role == 'admin':
        user.role = 'member'
        user.is_staff = False
        status = "removed admin privileges from"
    else:
        user.role = 'admin'
        user.is_staff = True
        status = "granted admin privileges to"
    
    user.save()
    messages.success(request, f'Successfully {status} "{user.username}".')
    
    return redirect('manage_admin_users')
