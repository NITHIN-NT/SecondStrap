from django.contrib.auth.decorators import user_passes_test
from functools import wraps
from django.shortcuts import redirect

def superuser_required(view_func=None,login_url=''):
    """
        allow only superusers
    """ 
    actual_decorator = user_passes_test(lambda user:user.is_superuser,login_url=login_url)
    if view_func:
        return actual_decorator(view_func)
    return actual_decorator

def redirect_if_authenticated(view_func):
    '''
        If a user is loged in ,User should not redirect to the login or related pages
    '''
    @wraps(view_func)
    def wrapper(req,*args, **kwargs):
        if req.user.is_authenticated:
            if req.user.is_superuser:
                return redirect('admin_home')
            else:
                return redirect('Home_page_user')
        return view_func(req, *args, **kwargs)
    
    return wrapper