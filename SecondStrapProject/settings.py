from pathlib import Path
import environ
import os
import cloudinary
import cloudinary.uploader
import cloudinary.api
import razorpay


BASE_DIR = Path(__file__).resolve().parent.parent

'''
    Env Setup
'''
env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))  # .env should be in project root (same as manage.py)

'''
    RAZORPAY INTEGRATION
'''
RAZORPAY_KEY_ID = env('RAZORPAY_KEY_ID')
RAZORPAY_KEY_SECRET = env('RAZORPAY_KEY_SECRET')
RAZORPAY_CALLBACK_URL = env('RAZORPAY_CALLBACK_URL')
RAZORPAY_CURRENCY = "INR"


'''
    SECURITY
'''
SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['127.0.0.1', 'localhost'])
CSRF_TRUSTED_ORIGINS = ['https://stephanie-unmanipulative-louella.ngrok-free.dev']

'''
    USER & AUTH
'''
AUTH_USER_MODEL = 'accounts.CustomUser'
SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

'''
    APPLICATIONS
'''

INSTALLED_APPS = [
    # Django default apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'cloudinary_storage', 
    'django.contrib.staticfiles',
    'django.contrib.sites',

    # Third-party apps
    'dynamic_breadcrumbs',

    # Local apps
    'userFolder.userprofile',
    'userFolder.wishlist',
    'userFolder.cart',
    'userFolder.checkout',
    'userFolder.order',
    'userFolder.wallet',
    'userFolder.payment',
    'products',
    'Admin',
    'accounts',
    'Scripts',

    # Allauth
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',

    'cloudinary',
]

# ============================ AUTHENTICATION SETTINGS ============================
LOGIN_URL = 'accounts/login'
LOGOUT_REDIRECT_URL = 'Home_page_user'
LOGIN_REDIRECT_URL = 'Home_page_user'
ACCOUNT_LOGOUT_REDIRECT_URL = 'Home_page_user'
ACCOUNT_AUTHENTICATED_LOGIN_REDIRECTS = True

ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_LOGIN_METHODS = {'email'}

ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']
SOCIALACCOUNT_EMAIL_VERIFICATION = 'none'
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_ADAPTER = 'accounts.adapter.CustomSocialAccountAdapter'
'''
    MIDDLEWARE
'''

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

'''
    URLS & WSGI 
'''

ROOT_URLCONF = 'SecondStrapProject.urls'
WSGI_APPLICATION = 'SecondStrapProject.wsgi.application'

'''
    TEMPLATES
'''

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'dynamic_breadcrumbs.context_processors.breadcrumbs',
            ],
        },
    },
]

'''
    DATABASE
'''
DATABASES = {
    'default': env.db(),
}

'''
    SOCIAL ACCOUNT PROVIDERS
'''
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': env('client_id'),
            'secret': env('secret'),
            'key': '',
            'FETCH_USERINFO': True,
        },
        'SCOPE': [
            'profile',
            'email',
            'https://www.googleapis.com/auth/user.phonenumbers.read'
            ],
        'AUTH_PARAMS': {'access_type': 'online'},
        'OAUTH_PKCE_ENABLED': True,
    }
}

'''
    PASSWORD VALIDATORS
'''
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

'''
    LOCALIZATION
'''
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

'''
    STATIC & MEDIA
'''
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/' 

'''
    EMAIL CONFIG
'''
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': env('CLOUD_NAME'),
    'API_KEY': env('API_KEY'),
    'API_SECRET': env('API_SECRET')
}

STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}