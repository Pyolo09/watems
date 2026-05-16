"""
Run this script ONCE to create the first admin user.

Usage:
    python create_admin.py

[DECISION] Change the username, email, and password below before running.
"""
from app import create_app, db
from app.models import User

app = create_app()

with app.app_context():
    # ─────────────────────────────────────────────────────────────
    # [DECISION] Set your admin credentials here
    # ─────────────────────────────────────────────────────────────
    ADMIN_USERNAME = 'admin'
    ADMIN_EMAIL    = 'olajuwonolamide70@gmail.com'
    ADMIN_PASSWORD = 'password'   # ⚠️ CHANGE THIS before deploying to production

    existing = User.query.filter_by(email=ADMIN_EMAIL).first()
    if existing:
        print(f'User {ADMIN_EMAIL} already exists.')
    else:
        admin = User(username=ADMIN_USERNAME, email=ADMIN_EMAIL, role='admin')
        admin.set_password(ADMIN_PASSWORD)
        db.session.add(admin)
        db.session.commit()
        print(f'Admin user created: {ADMIN_EMAIL}')
