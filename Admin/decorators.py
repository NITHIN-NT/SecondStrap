from django.contrib.auth.decorators import user_passes_test
from functools import wraps
from django.shortcuts import redirect
from django.urls import reverse

def superuser_required(view_func=None,login_url=''):
    """
        allow only superusers
    """ 
    actual_decorator = user_passes_test(lambda user:user.is_superuser,login_url=login_url)
    if view_func:
        return actual_decorator(view_func)
    return actual_decorator

def redirect_if_authenticated(view_func):
    """
    Prevent logged-in users from accessing login pages.
    Safe against redirect loops.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            # Resolve target URLs
            admin_home = reverse("admin_home")
            user_home = reverse("Home_page_user")

            # 🚨 Prevent redirect loop
            if request.user.is_superuser and request.path != admin_home:
                return redirect("admin_home")

            if not request.user.is_superuser and request.path != user_home:
                return redirect("Home_page_user")

        return view_func(request, *args, **kwargs)

    return wrapper
