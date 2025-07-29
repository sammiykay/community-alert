from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, F
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from .models import Alert, AlertCategory, Community, CustomUser, AlertVote
from .forms import UserRegistrationForm, AlertForm, UserProfileForm
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
    if request.method == 'POST':
        form = AlertForm(request.POST, request.FILES)
        if form.is_valid():
            alert = form.save(commit=False)
            alert.created_by = request.user
            alert.save()
            
            # Trigger notifications for high/critical alerts
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
        form = AlertForm()
    
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
        form = AlertForm(request.POST, request.FILES, instance=alert)
        if form.is_valid():
            alert = form.save(commit=False)
            alert.updated_by = request.user
            alert.save()
            messages.success(request, 'Alert updated successfully!')
            return redirect('alert_detail', alert_id=alert.id)
    else:
        form = AlertForm(instance=alert)
    
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
                        return JsonResponse({
                            'success': False,
                            'error': 'Please correct the form errors.',
                            'form_errors': form.errors
                        })
                
                elif action == 'update_notifications':
                    # Update notification preferences
                    user = request.user
                    user.email_notifications = request.POST.get('email_notifications') == 'on'
                    user.push_notifications = request.POST.get('push_notifications') == 'on'
                    
                    # Update notification radius
                    try:
                        radius = float(request.POST.get('notification_radius_km', user.notification_radius_km))
                        if 0.1 <= radius <= 50.0:
                            user.notification_radius_km = radius
                        else:
                            return JsonResponse({
                                'success': False,
                                'error': 'Notification radius must be between 0.1 and 50 km.'
                            })
                    except (ValueError, TypeError):
                        return JsonResponse({
                            'success': False,
                            'error': 'Invalid notification radius value.'
                        })
                    
                    user.save()
                    return JsonResponse({
                        'success': True,
                        'message': 'Notification settings updated successfully!'
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


def nearby_alerts(request):
    """Show alerts near user's location (requires location permission)"""
    if not request.user.is_authenticated:
        return redirect('login')
    
    user = request.user
    if not user.latitude or not user.longitude:
        messages.info(request, 'Please set your location in your profile to see nearby alerts.')
        return redirect('user_profile')
    
    # Simple radius calculation (this would be better with PostGIS)
    radius_km = user.notification_radius_km
    lat_delta = radius_km / 111.0  # Approximate km per degree latitude
    lng_delta = radius_km / (111.0 * math.cos(math.radians(float(user.latitude))))
    
    alerts = Alert.objects.filter(
        is_public=True,
        status='active',
        latitude__range=(user.latitude - lat_delta, user.latitude + lat_delta),
        longitude__range=(user.longitude - lng_delta, user.longitude + lng_delta)
    ).select_related('category', 'community', 'created_by').order_by('-created_at')
    
    context = {
        'alerts': alerts,
        'user_location': {'lat': float(user.latitude), 'lng': float(user.longitude)},
        'radius_km': radius_km,
    }
    return render(request, 'community/nearby_alerts.html', context)


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
