from functools import wraps
from django.shortcuts import redirect

def login_redirect(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('Home_page_user')
        return view_func(request, *args, **kwargs)
    return wrapper