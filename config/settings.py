"""
Django settings for config project.

Generated by 'django-admin startproject' using Django 4.1.6.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.1/ref/settings/
"""
import os
import environ
from pathlib import Path

# Initialise environment variables and defaults
env = environ.Env(
    DEBUG=(bool, True),
    ALLOWED_HOSTS=([str], ['127.0.0.1']),
    CSRF_TRUSTED_ORIGINS=([str], ['http://localhost']),
    CSRF_COOKIE_SECURE=(bool, True),
    SESSION_COOKIE_SECURE=(bool, True),
    STATIC_URL=(str, 'static/'),
    STATIC_ROOT=(str, ''),
    WEBHOOK_SECRET=(str, 'secret'),
    B2_KEYID_RW=(str, ''),
    B2_APPKEY_RW=(str, ''),
    B2_ENDPOINT=(str, ''),
    B2_BUCKET_IMAGES=(str, ''),
    POSTGRES_NAME=(str, ''),
    POSTGRES_USER=(str, ''),
    POSTGRES_PW=(str, ''),
    POSTGRES_HOST=(str, ''),
    POSTGRES_PORT=(int, ''),
    GDAL_LIBRARY_PATH=(str, ''),
    NPM_BIN_PATH=(str, '/usr/local/bin/npm'),
    EMAIL_HOST=(str, ''),
    EMAIL_PORT=(str, ''),
    EMAIL_HOST_USER=(str, ''),
    EMAIL_HOST_PASSWORD=(str, ''),
)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Take environment variables from .env file
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG')

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY')

WEBHOOK_SECRET = env('WEBHOOK_SECRET')

GOOGLE_MAPS_API_KEY = env('GOOGLE_MAPS_API_KEY')
GOOGLE_SIGNING_SECRET = env('GOOGLE_SIGNING_SECRET')
MAPBOX_TOKEN = env('MAPBOX_TOKEN')

ALLOWED_HOSTS = env('ALLOWED_HOSTS')

CSRF_TRUSTED_ORIGINS = env('CSRF_TRUSTED_ORIGINS')

CSRF_COOKIE_SECURE = env('CSRF_COOKIE_SECURE')

SESSION_COOKIE_SECURE = env('SESSION_COOKIE_SECURE')

GDAL_LIBRARY_PATH = env('GDAL_LIBRARY_PATH')

# Backblaze B2 variables
B2_KEYID_RW = env('B2_KEYID_RW')
B2_APPKEY_RW = env('B2_APPKEY_RW')
B2_ENDPOINT = env('B2_ENDPOINT')
B2_BUCKET_IMAGES = env('B2_BUCKET_IMAGES')

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.1/howto/static-files/
STATIC_URL = env('STATIC_URL')

STATIC_ROOT = env('STATIC_ROOT')

# See https://docs.djangoproject.com/en/4.2/topics/logging/#configuring-logging
LOGGING = {
    'version': 1,                       # the dictConfig format version
    'disable_existing_loggers': False,  # retain the default loggers
    'handlers': {
        'stdout': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        '': {
            'level': 'DEBUG',
            'handlers': ['stdout'],
        },
        'boto3': {
            'level': 'CRITICAL',
            'handlers': ['stdout'],
        },
        'botocore': {
            'level': 'CRITICAL',
            'handlers': ['stdout'],
        },
        's3transfer': {
            'level': 'CRITICAL',
            'handlers': ['stdout'],
        },
        'urllib3': {
            'level': 'CRITICAL',
            'handlers': ['stdout'],
        }
    },
}

INSTALLED_APPS = [
    "buildings.apps.BuildingsConfig",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",
    "django_htmx",
    'django.contrib.humanize',
    'tailwind',
    'theme',
    'django_browser_reload',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    "mailer",
]

TAILWIND_APP_NAME = 'theme'

NPM_BIN_PATH = env('NPM_BIN_PATH')

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "django_browser_reload.middleware.BrowserReloadMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "config.urls"

APPEND_SLASH = True

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / 'templates'
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
            'builtins': [
                'django.templatetags.static',
            ],
        },
    },
]


WSGI_APPLICATION = "config.wsgi.application"

INTERNAL_IPS = (
    '127.0.0.1',
)

# Database
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases

DATABASES = {
    "default": {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': env('POSTGRES_NAME'),
        'USER': env('POSTGRES_USER'),
        'PASSWORD': env('POSTGRES_PW'),
        'HOST': env('POSTGRES_HOST'),
        'PORT': env('POSTGRES_PORT'),
        'TEST': {
            'TEMPLATE': 'template0', 
        }
    }
}

# https://docs.djangoproject.com/en/4.2/topics/auth/customizing/#extending-the-existing-user-model
AUTH_USER_MODEL = "buildings.User"

# Password validation
# https://docs.djangoproject.com/en/4.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
] if not DEBUG else []


AUTHENTICATION_BACKENDS = [
    # Needed to login by username in Django admin, regardless of `allauth`
    'django.contrib.auth.backends.ModelBackend',

    # `allauth` specific authentication methods, such as login by email
    'allauth.account.auth_backends.AuthenticationBackend',
]

# Internationalization
# https://docs.djangoproject.com/en/4.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "America/Montreal"

# Internationalization allows multiple languages
# https://docs.djangoproject.com/en/4.2/topics/i18n/translation/
USE_I18N = True

USE_TZ = True

# Default primary key field type
# https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Max request size increased to 16MB to upload images
DATA_UPLOAD_MAX_MEMORY_SIZE = 16_777_216

# https://github.com/pinax/django-mailer/blob/master/docs/usage.rst#usage
EMAIL_BACKEND = "mailer.backend.DbBackend"
MAILER_EMPTY_QUEUE_SLEEP = 5
# Email config given by the domain provider
EMAIL_HOST = env('EMAIL_HOST')
EMAIL_PORT = env('EMAIL_PORT')
EMAIL_HOST_USER = env('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD= env('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL=env('EMAIL_HOST_USER')
EMAIL_USE_TLS=True

# Override the default allauth forms here
ACCOUNT_FORMS = {
    'login': 'buildings.forms.LoginUserForm',
    'signup': 'buildings.forms.CreateUserForm',
    'reset_password': 'buildings.forms.PasswordResetForm',
    'reset_password_from_key': 'buildings.forms.ResetPasswordKeyForm',
    'add_email': 'allauth.account.forms.AddEmailForm',
    'change_password': 'allauth.account.forms.ChangePasswordForm',
    'set_password': 'allauth.account.forms.SetPasswordForm',
    'user_token': 'allauth.account.forms.UserTokenForm',
}

ACCOUNT_LOGIN_ATTEMPTS_LIMIT = not DEBUG
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 1

LOGIN_REDIRECT_URL = '/'