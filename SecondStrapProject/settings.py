from pathlib import Path
import environ
import os
import cloudinary
import cloudinary.uploader
import cloudinary.api
import razorpay
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

"""
    Env Setup
"""
env = environ.Env(
    DEBUG=(bool, False),
    SECURE_SSL_REDIRECT=(bool, True),
)
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

"""
    RAZORPAY INTEGRATION
"""
RAZORPAY_KEY_ID = env("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = env("RAZORPAY_KEY_SECRET")
RAZORPAY_CALLBACK_URL = env("RAZORPAY_CALLBACK_URL")
RAZORPAY_WALLET_CALLBACK_URL = env("RAZORPAY_WALLET_CALLBACK_URL", default="")
RAZORPAY_CURRENCY = "INR"

"""
    SECURITY
"""
SECRET_KEY = env("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["0.0.0.0", "127.0.0.1", "localhost"])
CSRF_TRUSTED_ORIGINS = [o.strip() for o in env.list("CSRF_TRUSTED_ORIGINS", default=[]) if o.strip()]

"""
    USER & AUTH
"""
AUTH_USER_MODEL = "accounts.CustomUser"
SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

"""
    APPLICATIONS
"""
INSTALLED_APPS = [
    # Django default apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",

    # Third-party apps
    "dynamic_breadcrumbs",

    # Local apps
    "userFolder.userprofile",
    "userFolder.wishlist",
    "userFolder.cart",
    "userFolder.checkout",
    "userFolder.order",
    "userFolder.wallet",
    "userFolder.payment",
    "userFolder.referral",
    "userFolder.review",
    "coupon",
    "offer",
    "products",
    "Admin",
    "accounts",
    "Scripts",

    # Allauth
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",

    # Cloudinary
    "cloudinary",
    "cloudinary_storage", 
]

# ============================ AUTHENTICATION SETTINGS ============================
LOGIN_URL = "login"
LOGOUT_REDIRECT_URL = "Home_page_user"
LOGIN_REDIRECT_URL = "Home_page_user"
ACCOUNT_LOGOUT_REDIRECT_URL = "Home_page_user"
ACCOUNT_AUTHENTICATED_LOGIN_REDIRECTS = True

ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_LOGIN_METHODS = {"email"}

ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
SOCIALACCOUNT_EMAIL_VERIFICATION = "none"
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_ADAPTER = "accounts.adapter.CustomSocialAccountAdapter"
ACCOUNT_DEFAULT_HTTP_PROTOCOL = "https"

"""
    MIDDLEWARE
"""
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

"""
    URLS & WSGI
"""
ROOT_URLCONF = "SecondStrapProject.urls"
WSGI_APPLICATION = "SecondStrapProject.wsgi.application"

"""
    TEMPLATES
"""
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "dynamic_breadcrumbs.context_processors.breadcrumbs",
                "userFolder.cart.context_processors.cart_count",
                "userFolder.wishlist.context_processors.wishlist_count",
            ],
        },
    },
]

"""
    DATABASE
"""
DATABASE_URL = env("DATABASE_URL", default=os.environ.get("DATABASE_URL", ""))

DATABASES = {
    "default": dj_database_url.parse(
        DATABASE_URL,
        conn_max_age=60,
        ssl_require=True,   
    )
}

"""
    SOCIAL ACCOUNT PROVIDERS
"""
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": env("CLIENT_ID"),
            "secret": env("CLIENT_SECRET"),
            "key": "",
            "FETCH_USERINFO": True,
        },
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
        "OAUTH_PKCE_ENABLED": True,
    }
}

"""
    PASSWORD VALIDATORS
"""
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

"""
    LOCALIZATION
"""
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

"""
    STATIC & MEDIA
"""
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_ROOT = os.path.join(BASE_DIR, "media")
MEDIA_URL = "/media/"

"""
    EMAIL CONFIG
"""
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER


# ============================ PROXY / COOKIE / SSL SETTINGS ============================

# proxy headers (Cloudflare / nginx)
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Safer redirect control (avoid redirect loop)
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=not DEBUG)

SESSION_EXPIRE_AT_BROWSER_CLOSE = True

SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG

CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = not DEBUG


# ============================ PRODUCTION SECURITY HEADERS ============================

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# Enable HSTS only in prod
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG


# ============================ CLOUDINARY STORAGE ============================

CLOUDINARY_STORAGE = {
    "CLOUD_NAME": env("CLOUD_NAME"),
    "API_KEY": env("API_KEY"),
    "API_SECRET": env("API_SECRET"),
}

STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

WHITENOISE_MANIFEST_STRICT = False

# ============================ LOGGING ============================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}