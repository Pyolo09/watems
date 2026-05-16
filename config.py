import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'change-this-secret-key'

    # On Render, DATABASE_URL is set automatically if you add a PostgreSQL db.
    # For the free tier with no DB addon, SQLite is used (stored in /tmp — resets on redeploy).
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(BASE_DIR, 'waste.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    RECORDS_PER_PAGE = 15
    HAZARDOUS_ALERT_KG = 500
