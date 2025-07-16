

from pathlib import Path
import os
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent



SECRET_KEY = 'django-insecure-0z_5kwzsq9x+=n(nc(z*htke@$3@yg9!%c$-1hn)zfduym-5la'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []





load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
# Change BASE_DIR to be a Path object
BASE_DIR = Path(__file__).resolve().parent.parent # <--- Use pathlib for BASE_DIR

# Your Firebase Admin SDK Configuration (adjust the path resolution for Path objects)
firebase_credentials_relative_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

db = None

if not firebase_admin._apps:
    if firebase_credentials_relative_path:
        # If firebase_credentials_relative_path is like '../../file.json'
        # The .parent / '..' syntax handles going up directories naturally.
        # So, BASE_DIR (which is already a Path) / relative_path_from_dotenv
        # This will construct the path correctly.
        firebase_credentials_path = BASE_DIR / firebase_credentials_relative_path

        print(f"Attempting to load Firebase credentials from: {firebase_credentials_path}")

        try:
            cred = credentials.Certificate(str(firebase_credentials_path)) # <--- Convert to string for credentials.Certificate
            firebase_admin.initialize_app(cred)
            print("Firebase Admin SDK initialized successfully.")
            db = firestore.client()
            print("Firestore client obtained.")
        except FileNotFoundError:
            print(f"Error: Firebase service account key not found at {firebase_credentials_path}")
        except Exception as e:
            print(f"Error initializing Firebase Admin SDK or obtaining client: {e}")
    else:
        print("Warning: GOOGLE_APPLICATION_CREDENTIALS environment variable not set. Firebase Admin SDK not initialized.")
else:
    print("Firebase Admin SDK already initialized. Reusing existing app.")
    db = firestore.client()

# --- DATABASES setting (will now work with Path objects) ---
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3', # This will now work
    }
}

# The rest of your settings...


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'mainapp',
    'rest_framework',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'cvbot_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'cvbot_backend.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
