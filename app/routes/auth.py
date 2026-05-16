from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User
from app.forms import LoginForm, RegisterForm

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user and user.check_password(form.password.data):
            if user.account_status == 'suspended':
                flash('Your account has been suspended. '
                      'Please contact the administrator for more information.', 'danger')
                return redirect(url_for('auth.login'))
            if user.account_status == 'inactive':
                flash('Your account is inactive. Please contact the administrator.', 'warning')
                return redirect(url_for('auth.login'))
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(next_page or url_for('dashboard.index'))
        flash('Invalid email or password.', 'danger')

    return render_template('auth/login.html', form=form, title='Log In')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    # ─────────────────────────────────────────────────────────────
    # [DECISION] Do you want open registration, or should only admins
    # create new accounts? To restrict registration, remove this route
    # and create users only through the admin panel.
    # ─────────────────────────────────────────────────────────────
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    form = RegisterForm()
    if form.validate_on_submit():
        existing = User.query.filter(
            (User.email == form.email.data.lower()) |
            (User.username == form.username.data)
        ).first()
        if existing:
            flash('Email or username already taken.', 'danger')
        else:
            user = User(
                username=form.username.data,
                email=form.email.data.lower(),
                role='operator'
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash('Account created. Please log in.', 'success')
            return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form=form, title='Register')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
