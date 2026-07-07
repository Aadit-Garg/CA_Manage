"""
CA Manage — Configuration Classes

Loads settings from environment variables with secure defaults.
Three tiers: base Config, DevelopmentConfig, ProductionConfig.
"""
import os


class Config:
    """Base configuration — shared across all environments."""

    # Flask core
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    if not SQLALCHEMY_DATABASE_URI:
        if os.environ.get('VERCEL') == '1':
            SQLALCHEMY_DATABASE_URI = 'sqlite:////tmp/ca_manage.db'
        else:
            SQLALCHEMY_DATABASE_URI = 'sqlite:///ca_manage.db'
            
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }

    # Handle NeonDB's postgres:// prefix and use psycopg3 driver
    if SQLALCHEMY_DATABASE_URI:
        if SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
            SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql+psycopg://', 1)
        elif SQLALCHEMY_DATABASE_URI.startswith('postgresql://'):
            SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgresql://', 'postgresql+psycopg://', 1)

    # Session
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours

    # CSRF
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour

    # Rate limiting
    RATELIMIT_STORAGE_URI = os.getenv('RATELIMIT_STORAGE_URI', 'memory://')
    RATELIMIT_DEFAULT = os.getenv('RATELIMIT_DEFAULT', '200 per hour')

    # Cloudinary
    CLOUDINARY_CLOUD_NAME = os.getenv('CLOUDINARY_CLOUD_NAME', '')
    CLOUDINARY_API_KEY = os.getenv('CLOUDINARY_API_KEY', '')
    CLOUDINARY_API_SECRET = os.getenv('CLOUDINARY_API_SECRET', '')

    # Application
    APP_NAME = 'CA Manage'
    APP_DESCRIPTION = 'Secure Document Portal & Practice Management'


class DevelopmentConfig(Config):
    """Development environment — debug mode, verbose logging."""

    DEBUG = True
    SESSION_COOKIE_SECURE = False
    SQLALCHEMY_ECHO = False  # Set True to log SQL queries


class ProductionConfig(Config):
    """Production environment — strict security, no debug."""

    DEBUG = False
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PREFERRED_URL_SCHEME = 'https'

    # Ensure a real secret key is set in production
    @classmethod
    def init_app(cls, app):
        if app.config['SECRET_KEY'] == 'dev-secret-key-change-in-production':
            raise ValueError('SECRET_KEY must be set in production environment')


class TestingConfig(Config):
    """Testing environment — in-memory database."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False


# Configuration map for easy selection
config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig,
}
