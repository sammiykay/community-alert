from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, F
from django.utils import timezone
import json
from decimal import Decimal

from community.models import Alert, AlertCategory, Community, CustomUser, AlertVote


def alert_to_dict(alert):
    """Convert Alert model to dictionary for JSON response"""
    return {
        'id': str(alert.id),
        'title': alert.title,
        'description': alert.description,
        'category': {
            'id': alert.category.id,
            'name': alert.category.name,
            'icon': alert.category.icon,
            'color': alert.category.color
        },
        'severity': alert.severity,
        'status': alert.status,
        'latitude': str(alert.latitude),
        'longitude': str(alert.longitude),
        'address': alert.address,
        'community': {
            'id': str(alert.community.id),
            'name': alert.community.name
        },
        'created_by': {
            'id': alert.created_by.id,
            'username': alert.created_by.username,
            'full_name': alert.created_by.get_full_name()
        },
        'incident_datetime': alert.incident_datetime.isoformat(),
        'created_at': alert.created_at.isoformat(),
        'updated_at': alert.updated_at.isoformat(),
        'view_count': alert.view_count,
        'upvotes': alert.upvotes,
        'downvotes': alert.downvotes,
        'is_public': alert.is_public,
        'is_verified': alert.is_verified,
        'media_count': alert.media.count(),
        'comments_count': alert.comments.filter(is_deleted=False).count()
    }


def community_to_dict(community):
    """Convert Community model to dictionary for JSON response"""
    return {
        'id': str(community.id),
        'name': community.name,
        'description': community.description,
        'latitude': str(community.latitude),
        'longitude': str(community.longitude),
        'radius_km': community.radius_km,
        'created_at': community.created_at.isoformat(),
        'is_active': community.is_active,
        'member_count': community.members.count(),
        'alert_count': community.alerts.filter(is_public=True).count()
    }


def user_to_dict(user):
    """Convert User model to dictionary for JSON response"""
    return {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'full_name': user.get_full_name(),
        'role': user.role,
        'created_at': user.created_at.isoformat(),
        'communities': [str(c.id) for c in user.communities.all()]
    }


@require_http_methods(["GET"])
def api_alerts_list(request):
    """API endpoint for listing alerts with filtering and pagination"""
    try:
        # Get query parameters
        page = int(request.GET.get('page', 1))
        page_size = min(int(request.GET.get('page_size', 20)), 100)  # Max 100 items per page
        
        # Filtering parameters
        category_id = request.GET.get('category')
        severity = request.GET.get('severity')
        status = request.GET.get('status')
        community_id = request.GET.get('community')
        search = request.GET.get('search')
        
        # Base queryset
        alerts = Alert.objects.filter(is_public=True).select_related(
            'category', 'community', 'created_by'
        ).order_by('-created_at')
        
        # Apply filters
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
        paginator = Paginator(alerts, page_size)
        page_obj = paginator.get_page(page)
        
        # Convert to JSON format
        alerts_data = [alert_to_dict(alert) for alert in page_obj]
        
        return JsonResponse({
            'success': True,
            'data': alerts_data,
            'pagination': {
                'page': page_obj.number,
                'pages': paginator.num_pages,
                'per_page': page_size,
                'total': paginator.count,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous()
            },
            'filters': {
                'category': category_id,
                'severity': severity,
                'status': status,
                'community': community_id,
                'search': search
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def api_alert_detail(request, alert_id):
    """API endpoint for getting alert details"""
    try:
        alert = Alert.objects.select_related(
            'category', 'community', 'created_by'
        ).prefetch_related('media', 'comments').get(
            id=alert_id, 
            is_public=True
        )
        
        # Increment view count
        Alert.objects.filter(id=alert_id).update(view_count=F('view_count') + 1)
        
        # Get comments
        comments = alert.comments.filter(is_deleted=False).select_related('user').order_by('created_at')
        comments_data = [{
            'id': comment.id,
            'content': comment.content,
            'user': {
                'username': comment.user.username,
                'full_name': comment.user.get_full_name()
            },
            'created_at': comment.created_at.isoformat(),
            'updated_at': comment.updated_at.isoformat()
        } for comment in comments]
        
        # Get media
        media_data = [{
            'id': media.id,
            'media_type': media.media_type,
            'file_url': media.file.url if media.file else None,
            'caption': media.caption,
            'uploaded_at': media.uploaded_at.isoformat()
        } for media in alert.media.all()]
        
        alert_data = alert_to_dict(alert)
        alert_data['comments'] = comments_data
        alert_data['media'] = media_data
        
        return JsonResponse({
            'success': True,
            'data': alert_data
        })
        
    except Alert.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Alert not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def api_communities_list(request):
    """API endpoint for listing communities"""
    try:
        communities = Community.objects.filter(is_active=True).order_by('name')
        
        communities_data = [community_to_dict(community) for community in communities]
        
        return JsonResponse({
            'success': True,
            'data': communities_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def api_categories_list(request):
    """API endpoint for listing alert categories"""
    try:
        categories = AlertCategory.objects.filter(is_active=True).order_by('name')
        
        categories_data = [{
            'id': category.id,
            'name': category.name,
            'description': category.description,
            'icon': category.icon,
            'color': category.color,
            'alert_count': category.alerts.filter(is_public=True).count()
        } for category in categories]
        
        return JsonResponse({
            'success': True,
            'data': categories_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def api_nearby_alerts(request):
    """API endpoint for getting alerts near user's location"""
    try:
        user = request.user
        
        if not user.latitude or not user.longitude:
            return JsonResponse({
                'success': False,
                'error': 'User location not set'
            }, status=400)
        
        # Simple radius calculation
        radius_km = user.notification_radius_km
        lat_delta = radius_km / 111.0
        lng_delta = radius_km / (111.0 * abs(float(user.latitude)))
        
        alerts = Alert.objects.filter(
            is_public=True,
            status='active',
            latitude__range=(user.latitude - lat_delta, user.latitude + lat_delta),
            longitude__range=(user.longitude - lng_delta, user.longitude + lng_delta)
        ).select_related('category', 'community', 'created_by').order_by('-created_at')
        
        alerts_data = [alert_to_dict(alert) for alert in alerts]
        
        return JsonResponse({
            'success': True,
            'data': alerts_data,
            'user_location': {
                'latitude': str(user.latitude),
                'longitude': str(user.longitude),
                'radius_km': radius_km
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def api_create_alert(request):
    """API endpoint for creating new alerts"""
    try:
        data = json.loads(request.body)
        
        # Validate required fields
        required_fields = ['title', 'description', 'category_id', 'severity', 
                          'latitude', 'longitude', 'community_id', 'incident_datetime']
        
        for field in required_fields:
            if field not in data:
                return JsonResponse({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }, status=400)
        
        # Validate category and community exist
        try:
            category = AlertCategory.objects.get(id=data['category_id'], is_active=True)
            community = Community.objects.get(id=data['community_id'], is_active=True)
        except (AlertCategory.DoesNotExist, Community.DoesNotExist):
            return JsonResponse({
                'success': False,
                'error': 'Invalid category or community'
            }, status=400)
        
        # Create alert
        alert = Alert.objects.create(
            title=data['title'],
            description=data['description'],
            category=category,
            severity=data['severity'],
            status=data.get('status', 'active'),
            latitude=Decimal(str(data['latitude'])),
            longitude=Decimal(str(data['longitude'])),
            address=data.get('address', ''),
            community=community,
            created_by=request.user,
            incident_datetime=timezone.datetime.fromisoformat(data['incident_datetime'].replace('Z', '+00:00')),
            is_public=data.get('is_public', True)
        )
        
        return JsonResponse({
            'success': True,
            'data': alert_to_dict(alert)
        }, status=201)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def api_user_profile(request):
    """API endpoint for getting user profile"""
    try:
        user = request.user
        user_data = user_to_dict(user)
        
        # Add additional profile data
        user_data.update({
            'notification_preferences': {
                'email_notifications': user.email_notifications,
                'push_notifications': user.push_notifications,
                'notification_radius_km': user.notification_radius_km
            },
            'location': {
                'latitude': str(user.latitude) if user.latitude else None,
                'longitude': str(user.longitude) if user.longitude else None
            },
            'stats': {
                'alerts_created': user.created_alerts.count(),
                'alerts_voted': user.alertvote_set.count()
            }
        })
        
        return JsonResponse({
            'success': True,
            'data': user_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def api_stats(request):
    """API endpoint for getting system statistics"""
    try:
        stats = {
            'total_alerts': Alert.objects.filter(is_public=True).count(),
            'active_alerts': Alert.objects.filter(is_public=True, status='active').count(),
            'resolved_alerts': Alert.objects.filter(is_public=True, status='resolved').count(),
            'total_communities': Community.objects.filter(is_active=True).count(),
            'total_users': CustomUser.objects.filter(is_active=True).count(),
            'alerts_by_severity': {
                'low': Alert.objects.filter(is_public=True, severity='low').count(),
                'medium': Alert.objects.filter(is_public=True, severity='medium').count(),
                'high': Alert.objects.filter(is_public=True, severity='high').count(),
                'critical': Alert.objects.filter(is_public=True, severity='critical').count()
            },
            'recent_alerts': Alert.objects.filter(
                is_public=True, 
                created_at__gte=timezone.now() - timezone.timedelta(days=7)
            ).count()
        }
        
        return JsonResponse({
            'success': True,
            'data': stats
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def api_test_notification(request):
    """API endpoint for testing user notifications"""
    try:
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
