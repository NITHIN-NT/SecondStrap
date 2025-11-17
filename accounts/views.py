import logging 
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.views import View
from .models import CustomUser, EmailOTP
from .forms import CustomUserRegisterForm, LoginForm, VerifyOTPForm, SetNewPassword, ForgotPasswordEmailForm
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.db import transaction
from .decorators import login_redirect
from allauth.socialaccount.providers.google.views import oauth2_callback

# Create your views here.

logger = logging.getLogger(__name__) 


OTP_SESSION_EXPIRY = 120

class LoggedInRedirectMixin:
    """
    A mixin to redirect authenticated users away from a page.
    """
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('Home_page_user')
        return super().dispatch(request, *args, **kwargs)

@never_cache
@login_redirect
def signup_view(request):
    '''
    Handles user signup 
    Sends OTP for email verification
    '''
    if request.method == 'POST':
        form = CustomUserRegisterForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            password = form.cleaned_data['password']

            try:
                with transaction.atomic():
                    user = CustomUser.objects.create_user(
                        email=email,
                        first_name=first_name,
                        last_name=last_name,
                        password=password
                    )
                    user.is_active = False
                    user.save()

                    EmailOTP.objects.filter(user=user).delete()

                    otp_code = EmailOTP.generate_otp()
                    EmailOTP.objects.create(user=user, otp=otp_code)

                    plain_message = f"Your OTP code is {otp_code}"
                    html_message = render_to_string('accounts/email/otp_email.html', {'otp_code': otp_code})
                    msg = EmailMultiAlternatives(
                        body=plain_message,
                        subject='Your OTP Verification Code',
                        to=[email],
                    )
                    msg.attach_alternative(html_message, "text/html")
                    msg.send()

            except Exception as e:
                logger.error(f"Error during signup for {email}: {e}")
                messages.error(request, 'There was an error sending the email. Please try again later.')
                return redirect('signup')

            request.session['pending_user_id'] = user.id
            request.session.set_expiry(OTP_SESSION_EXPIRY)

            messages.info(request, "OTP sent to your email. Verify to continue.")
            return redirect('activate_account')
        else:
            return render(request, 'accounts/signup.html', {'form': form})
    else:
        form = CustomUserRegisterForm()
    return render(request, 'accounts/signup.html', {'form': form})

@never_cache
@login_redirect
def activate_account(request):
    '''
        Verifies the OTP entered after signup
    '''

    user_id = request.session.get('pending_user_id')

    if not user_id:
        messages.error(request, 'No pending Verification Found')
        return redirect('signup')

    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        messages.error(request, "User Not Found")
        return redirect('signup')

    if request.method == 'POST':
        otp_input = request.POST.get('otp', '').strip()

        otp_record = EmailOTP.objects.filter(user=user, otp=otp_input).last()

        if otp_record and otp_record.is_valid():
            user.is_active = True
            user.save()
            otp_record.delete()
            request.session.pop('pending_user_id', None)
            backend = settings.AUTHENTICATION_BACKENDS[0] 
            login(request, user,backend=backend)
            messages.success(request, "Your email has been verified successfully!")
            return redirect('Home_page_user')
        else:
            messages.error(request, 'Invalid or expired OTP. Please try again.')
            return render(request, 'accounts/activate_account.html', {'email': user.email})

    return render(request, 'accounts/activate_account.html', {'email': user.email})

@never_cache
@login_redirect
def resent_otp(request):
    '''
        Resends the verification OTP to the user
    '''
    user_id = request.session.get('pending_user_id')

    if not user_id:
        messages.error(request, 'No pending Verification Found')
        return redirect('signup')

    user = get_object_or_404(CustomUser, id=user_id)
    email = user.email

    otp_code = EmailOTP.generate_otp()
    EmailOTP.objects.create(user=user, otp=otp_code)

    plain_message = f"Your OTP code is {otp_code}"
    html_message = render_to_string('accounts/email/otp_email.html', {'otp_code': otp_code})

    try:
        msg = EmailMultiAlternatives(
            body=plain_message,
            subject='Your OTP Verification Code',
            to=[email],
        )
        msg.attach_alternative(html_message, "text/html")
        msg.send()
    except Exception as e:
        logger.error(f"Error resending OTP for {email}: {e}")
        messages.error(request, 'There was an error sending the email. Please try again later.')
        return redirect('signup')

    request.session['pending_user_id'] = user.id
    request.session.set_expiry(OTP_SESSION_EXPIRY)

    messages.success(request, "OTP has been re-sent.")
    return redirect('activate_account')

@never_cache
@login_redirect
def login_view(request):
    '''
        Handles user login for active (verified) users
    '''
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = authenticate(request, email=email, password=password)
            if user is not None:
                if user.is_active:
                    login(request, user)
                    request.session.cycle_key()
                    messages.success(request, f"Welcome back, {user.first_name or user.email}!")
                    return redirect('Home_page_user')
                else:
                    messages.error(request, "Please verify your email first.")
                    return render(request, 'accounts/activate_account.html', {'email': user.email})
            else:
                messages.error(request, "Invalid credentials. Please check your email and password.")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    if field == '__all__':
                        messages.error(request, f"{error}")
                    else:
                        messages.error(request, f"{field.replace('_', ' ').capitalize()}: {error}")
            return render(request, 'accounts/login.html', {'form': form})
    else:
        form = LoginForm()
    return render(request, 'accounts/login.html', {'form': form})

@never_cache
def logout_view(request):
    '''
    Logs out the authenticated user
    '''
    if not request.user.is_authenticated:
        return redirect('Home_page_user')
    logout(request)
    '''
    Ensure session is cleared after logout to remove any leftover keys
    '''
    try:
        request.session.flush()
    except Exception:
        pass
    return redirect('Home_page_user')

@method_decorator(never_cache, name='dispatch')
class SendOTPView(LoggedInRedirectMixin, View):
    '''
       Sends OTP for password reset request
    '''
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('Home_page_user')
        form = ForgotPasswordEmailForm()
        return render(request, 'accounts/forgot-password.html', {'form': form})

    def post(self, request):
        form = ForgotPasswordEmailForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user_query = CustomUser.objects.filter(email=email) 
            
            if user_query.filter(is_superuser=True):
                messages.error(request, 'You are not authorized to change the password from this interface.')
                return redirect('Home_page_user')

            try:
                user = user_query.get() 
            except CustomUser.DoesNotExist:
                messages.error(request, 'No user found with this email')
                return render(request, 'accounts/forgot-password.html', {'form': form})

            otp = EmailOTP.generate_otp()
            EmailOTP.objects.create(user=user, otp=otp)

            plain_message = f'Your OTP code for password reset is: {otp}'
            html_message = render_to_string('accounts/email/otp_email_reset.html', {'otp_code': otp})

            try:
                msg = EmailMultiAlternatives(
                    body=plain_message,
                    subject='Your OTP Verification Code',
                    to=[email],
                )
                msg.attach_alternative(html_message, "text/html")
                msg.send()
            except Exception as e:
                logger.error(f"Error sending password reset OTP for {email}: {e}")
                messages.error(request, 'There was an error sending the email. Please try again later.')
                return redirect('forgot-password')

            request.session['reset_user_email'] = user.email
            request.session.pop('reset_password_allowed', None)
            request.session.set_expiry(OTP_SESSION_EXPIRY)

            messages.success(request, f'An otp has been sent to your mail.')
            return redirect('forgot-verify-otp')
        else:
            return render(request, 'accounts/forgot-password.html', {'form': form})

@method_decorator(never_cache, name='dispatch')
class VerifyOTPView(LoggedInRedirectMixin, View):
    '''
        Verifies OTP for password reset
    '''
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('Home_page_user')
        if 'reset_user_email' not in request.session:
            messages.error(request, 'Please Request an OTP First.')
            return redirect('forgot-password')

        form = VerifyOTPForm()
        return render(request, 'accounts/verify-otp-password_reset.html', {'form': form})

    def post(self, request):
        email = request.session.get('reset_user_email')
        if not email:
            messages.error(request, 'Your Session has expired.Please start over')
            return redirect('forgot-password')

        form = VerifyOTPForm(request.POST)
        if form.is_valid():
            otp_from_form = form.cleaned_data['otp']
            user = get_object_or_404(CustomUser, email=email)

            try:
                email_otp = EmailOTP.objects.filter(user=user, otp=otp_from_form).latest('created_at')
            except EmailOTP.DoesNotExist:
                messages.error(request, "Invalid OTP. Please try again.")
                return render(request, 'accounts/verify-otp-password_reset.html', {'form': form})

            if email_otp.is_valid(): 
                email_otp.delete()
                request.session['reset_password_allowed'] = True
                request.session.set_expiry(OTP_SESSION_EXPIRY)
                messages.success(request, 'OTP verified successfully. Please set your new password')
                return redirect('set-new-password')
            else:
                messages.error(request, 'Your OTP has expired. Please request a new one.')

        return render(request, 'accounts/verify-otp-password_reset.html', {'form': form})

@method_decorator(never_cache, name='dispatch')
class NewPasswordView(LoggedInRedirectMixin, View):
    '''
        Allows user to set a new password after OTP verification
    '''
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('Home_page_user')
        if not request.session.get('reset_user_email') or not request.session.get('reset_password_allowed'):
            messages.error(request, 'You are not authorized to access this page. Please verify your OTP first.')
            return redirect('forgot-password')

        form = SetNewPassword()
        return render(request, 'accounts/new-password.html', {'form': form})

    def post(self, request):
        email = request.session.get('reset_user_email')

        if not email or not request.session.get('reset_password_allowed'):
            messages.error(request, 'Your session has expired. Please start over.')
            return redirect('forgot-password')

        form = SetNewPassword(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_password1']
            user = get_object_or_404(CustomUser, email=email)

            user.set_password(new_password)
            user.save()
            request.session.pop('reset_user_email', None)
            request.session.pop('reset_password_allowed', None)

            messages.success(request, 'Your password has been reset successfully. Please log in.')
            return redirect('login')

        return render(request, 'accounts/new-password.html', {'form': form})
    

@never_cache
def google_callback_safe(request, *args, **kwargs):
    if request.user.is_authenticated:
        return redirect('Home_page_user') 
    
    return oauth2_callback(request, *args, **kwargs)

# Final fixed