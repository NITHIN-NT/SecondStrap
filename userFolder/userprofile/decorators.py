from functools import wraps
from django.http import JsonResponse

def ajax_login_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(
                {"message": "Please log in to continue."},
                status=401
            )
        return view_func(request, *args, **kwargs)
    return _wrapped_view
