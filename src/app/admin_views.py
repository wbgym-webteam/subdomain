from flask import Blueprint, session, request, redirect, url_for, flash, render_template
from flask_login import login_required, current_user, login_user, logout_user
from werkzeug.security import check_password_hash
from functools import wraps
from .models import User, Teams, TeamType, Game, DependencyType, ScoringPreference, Admin, GamePoints, Log, db
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

admin = Blueprint('admin', __name__, 
                 url_prefix='/gog/admin', 
                 template_folder='templates/gog',  # Updated template folder path
                 static_folder='static/gog/admin',
                 static_url_path='/static/admin')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            flash('Please login as admin to access this area.', 'admin')
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated_function

@admin.before_request
def check_admin():
    # Skip authentication for static files and login route
    if not request.endpoint:
        return
    
    if 'static' in request.endpoint or request.endpoint == 'admin.login':
        return

    # Check if user is authenticated and is admin
    if not current_user.is_authenticated or not session.get('is_admin'):
        session.clear()  # Clear any existing session
        return redirect(url_for('admin.login'))

@admin.route('/login', methods=['GET', 'POST'])
def login():
    # Clear any existing session
    if 'is_admin' in session and not current_user.is_authenticated:
        session.clear()
    
    # If user is already authenticated and is admin, redirect to dashboard
    if current_user.is_authenticated and session.get('is_admin'):
        return redirect(url_for('admin.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password) and user.is_admin:
            login_user(user)
            session['is_admin'] = True
            session['user_id'] = user.id
            session.permanent = True
            return redirect(url_for('admin.dashboard'))
        
        flash('Invalid credentials or insufficient permissions')
        return render_template('gog/admin/login.html')
    
    return render_template('gog/admin/login.html')

@admin.route('/logout')
@admin_required
def logout():
    session.clear()
    flash('You have been logged out.')
    return redirect(url_for('admin.login'))

@admin.route('/dashboard')
@login_required
@admin_required
def dashboard():
    if not current_user.is_authenticated or not session.get('is_admin'):
        return redirect(url_for('admin.login'))
    
    users = User.query.filter_by(is_admin=False).all()
    admins = Admin.query.all()
    teams = Teams.query.all()
    games = Game.query.all()
    return render_template('gog/admin/dashboard.html', users=users, teams=teams, games=games, admins=admins)

@admin.route('/users/create', methods=['GET'])
@admin_required
def create_user_form():
    return render_template('gog/admin/create_user.html')

@admin.route('/users/create', methods=['POST'])
@admin_required
def create_user():
    username = request.form['username']
    password = request.form['password']
    
    if User.query.filter_by(username=username).first():
        flash('Username already exists!')
        return redirect(url_for('admin.dashboard'))
    
    user = User(username=username, is_admin=False)  # Explicitly set is_admin to False
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    
    flash('User created successfully!')
    return redirect(url_for('admin.dashboard'))

@admin.route('/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    
    flash('User deleted successfully!')
    return redirect(url_for('admin.dashboard'))

@admin.route('/teams/create', methods=['GET'])
@admin_required
def create_team_form():
    return render_template('gog/admin/create_team.html')

@admin.route('/teams/create', methods=['POST'])
@admin_required
def create_team():
    name = request.form['name']
    type_id = request.form['type']
    number = request.form['number']
    
    team_id = f"{type_id.lower()}{number}"
    
    if Teams.query.filter_by(id=team_id).first():
        flash('Team already exists!')
        return redirect(url_for('admin.dashboard'))
    
    if not name:
        name = team_id
    
    team = Teams(team_type=type_id, team_number=number)
    team.id = team_id
    team.team_name = name
    db.session.add(team)
    db.session.commit()
    
    flash('Team created successfully!')
    return redirect(url_for('admin.dashboard'))

@admin.route('/teams/delete/<string:team_id>', methods=['POST'])
@admin_required
def delete_team(team_id):
    try:
        # Get the team
        team = Teams.query.get_or_404(team_id)
        logger.info(f"Found team to delete: {team.id}")
        
        # First delete all related game points
        points_deleted = GamePoints.query.filter_by(team_id=team_id).delete()
        logger.info(f"Deleted {points_deleted} game points records")
        
        # Delete all related logs
        logs_deleted = Log.query.filter_by(team_id=team_id).delete()
        logger.info(f"Deleted {logs_deleted} log records")
        
        # Now delete the team
        db.session.delete(team)
        db.session.commit()
        
        logger.info(f"Successfully deleted team {team_id}")
        flash('Team deleted successfully!')
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting team {team_id}: {str(e)}")
        flash(f'Error deleting team: {str(e)}')
        
    return redirect(url_for('admin.dashboard'))

@admin.route('/games/create', methods=['GET'])
@admin_required
def create_game_form():
    return render_template('gog/admin/create_game.html')

@admin.route('/games/create', methods=['POST'])
@admin_required
def create_game():
    name = request.form['name']
    dependency_type = request.form.get('dependency_type', DependencyType.NONE)
    scoring_pref = request.form.get('scoring_preference', ScoringPreference.HIGHER_BETTER)
    
    if Game.query.filter_by(name=name).first():
        flash('Game already exists!')
        return redirect(url_for('admin.dashboard'))
    
    game = Game(
        name=name,
        dependency_type=dependency_type,
        scoring_preference=scoring_pref  # Use scoring_pref directly
    )
    db.session.add(game)
    db.session.commit()
    
    flash('Game created successfully!')
    return redirect(url_for('admin.dashboard'))

@admin.route('/games/delete/<int:game_id>', methods=['POST'])
@admin_required
def delete_game(game_id):
    game = Game.query.get_or_404(game_id)
    db.session.delete(game)
    db.session.commit()
    
    flash('Game deleted successfully!')
    return redirect(url_for('admin.dashboard'))

@admin.route('/')
@login_required
def admin_home():
    if not current_user.is_administrator:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('main_views.home'))
    return redirect(url_for('admin.dashboard'))
