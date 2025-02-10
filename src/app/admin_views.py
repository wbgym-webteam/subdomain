from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user, login_user, logout_user
from .models import User, Teams, TeamType, db  # Fix the import here - removed 'dbams' typo
from functools import wraps

admin = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_administrator:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function



@admin.route('/admin/login', methods=['GET', 'POST'])  # Remove /gog prefix
def admin_login():
    if current_user.is_authenticated and current_user.is_administrator:
        return redirect(url_for('admin.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password) and user.is_administrator:
            login_user(user)
            return redirect(url_for('admin.dashboard'))
        else:
            flash('Invalid credentials or not an admin user')
            
    return render_template('gog/admin/login.html')

@admin.route('/admin/logout')  # Remove /gog prefix
@login_required
def admin_logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('admin.admin_login'))

@admin.route('/admin/dashboard')  # Remove /gog prefix
@admin_required
def dashboard():
    users = User.query.filter_by(is_admin=False).all()
    teams = Teams.query.all()
    return render_template('gog/admin/dashboard.html', users=users, teams=teams)


@admin.route('/admin/create_user', methods=['GET', 'POST'])  # Remove /gog prefix
@admin_required
def create_user():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('admin.create_user'))
        
        user = User(username=username, is_admin=False)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('User created successfully')
        return redirect(url_for('admin.dashboard'))
    
    return render_template('gog/admin/create_user.html')

@admin.route('/admin/create_team', methods=['GET', 'POST'])
@admin_required
def create_team():
    if request.method == 'POST':
        team_type = request.form.get('team_type')
        team_number = request.form.get('team_number')
        team_name = request.form.get('team_name')
        
        # Check if team number already exists for this team type
        existing_team = Teams.query.filter_by(
            id=f"{team_type.lower()}{team_number}"
        ).first()
        
        if existing_team:
            flash(f'Team {team_type}{team_number} already exists')
            return redirect(url_for('admin.create_team'))
        
        try:
            team = Teams(team_type=team_type, team_number=team_number)
            team.team_name = team_name
            db.session.add(team)
            db.session.commit()
            flash('Team created successfully', 'admin')  # Add category 'admin'
            return redirect(url_for('admin.dashboard'))
        except Exception as e:
            flash(f'Error creating team: {str(e)}', 'admin')  # Add category 'admin'
            
    return render_template('gog/admin/create_team.html')

@admin.route('/admin/delete_team/<team_id>', methods=['POST'])
@admin_required
def delete_team(team_id):
    team = Teams.query.get_or_404(team_id)
    try:
        db.session.delete(team)
        db.session.commit()
        flash(f'Team {team.team_name} deleted successfully', 'admin')
    except Exception as e:
        flash(f'Error deleting team: {str(e)}', 'admin')
    return redirect(url_for('admin.dashboard'))
