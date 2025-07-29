from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt


@login_required
@csrf_exempt
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