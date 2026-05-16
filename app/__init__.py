from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)

    # Make csrf_token available in every template
    from flask_wtf.csrf import CSRFProtect, generate_csrf
    csrf = CSRFProtect(app)

    @app.context_processor
    def inject_csrf_token():
        return dict(csrf_token=generate_csrf)

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.records import records_bp
    from app.routes.reports import reports_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(records_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(admin_bp)

    # Create tables on first run
    with app.app_context():
        db.create_all()
        _seed_defaults()
        _seed_admin()

    return app


def _seed_admin():
    """Create the admin user automatically on first deploy if not exists."""
    from app.models import User
    existing = User.query.filter_by(email='olajuwonolamide70@gmail.com').first()
    if not existing:
        admin = User(
            username='admin',
            email='olajuwonolamide70@gmail.com',
            role='admin',
            account_status='active'
        )
        admin.set_password('password')
        db.session.add(admin)
        db.session.commit()


def _seed_defaults():
    """Seed default waste types and locations if the DB is empty."""
    from app.models import WasteType, Location

    if WasteType.query.count() == 0:
        # ─────────────────────────────────────────────────────────
        # [DECISION] Add, remove, or rename waste categories to match
        # your local regulations or project requirements.
        # ─────────────────────────────────────────────────────────
        default_types = [
            WasteType(name='General',    color='#6c757d'),
            WasteType(name='Recyclable', color='#198754'),
            WasteType(name='Organic',    color='#fd7e14'),
            WasteType(name='Hazardous',  color='#dc3545'),
            WasteType(name='Electronic', color='#0dcaf0'),
        ]
        db.session.add_all(default_types)

    if Location.query.count() == 0:
        # ─────────────────────────────────────────────────────────
        # [DECISION] Replace these with your actual collection sites,
        # zones, or districts.
        # ─────────────────────────────────────────────────────────
        default_locations = [
            Location(name='Zone A – Residential'),
            Location(name='Zone B – Commercial'),
            Location(name='Zone C – Industrial'),
            Location(name='Central Depot'),
        ]
        db.session.add_all(default_locations)

    db.session.commit()
