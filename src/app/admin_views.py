from flask import Blueprint, session, request, redirect, url_for, flash, render_template
from flask_login import login_required, current_user, login_user, logout_user
from werkzeug.security import check_password_hash
from functools import wraps
from .models import User, Teams, TeamType, Game, DependencyType, ScoringPreference, Admin, db  # Fixed import
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
    if request.endpoint and 'static' not in request.endpoint:
        if not session.get('is_admin') and request.endpoint != 'admin.login':
            return redirect(url_for('admin.login'))

@admin.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user:
            logger.info(f"User found: {user.username}")
        else:
            logger.info("User not found")
        
        if user and user.check_password(password):  # Use the check_password method
            logger.info("Password check passed")
            session.permanent = True
            session['user_id'] = user.id
            session['is_admin'] = user.is_admin
            login_user(user)
            return redirect(url_for('admin.dashboard'))
        
        logger.info("Invalid username or password")
        flash('Invalid username or password')
    return render_template('gog/admin/login.html')  # Ensure this path is correct

@admin.route('/logout')
@admin_required
def logout():
    session.clear()
    flash('You have been logged out.')
    return redirect(url_for('admin.login'))

@admin.route('/dashboard')
@admin_required
def dashboard():
    users = User.query.filter_by(is_admin=False).all()
    admins = Admin.query.all()  # Add this line
    teams = Teams.query.all()
    games = Game.query.all()
    return render_template('gog/admin/dashboard.html', users=users, teams=teams, games=games, admins=admins)  # Ensure this path is correct

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

@admin.route('/teams/delete/<string:team_id>', methods=['POST'])  # Change to <string:team_id>
@admin_required
def delete_team(team_id):
    team = Teams.query.get_or_404(team_id)
    db.session.delete(team)
    db.session.commit()
    
    flash('Team deleted successfully!')
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
        return redirect(url_for('main.home'))
    return redirect(url_for('admin.dashboard'))
