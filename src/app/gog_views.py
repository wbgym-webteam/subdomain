from flask import Flask, render_template, request, redirect, url_for, Blueprint, current_app, flash
from . import db
from .models import Game, Teams, GamePoints, Log, TeamType, User, DependencyType
import sqlite3
from flask_login import login_user, logout_user, login_required, current_user
from functools import wraps

gog = Blueprint("gog", __name__)
DATABASE = "wbgym.db"  # Update this to the path of your SQLite database


def calculate_ranked_points(game_id):
    
    game = Game.query.get(game_id)

    # Separate rankings for A Teams and B Teams
    for team_type in [TeamType.A, TeamType.B]:
        game_points = GamePoints.query.filter_by(game_id=game_id, team_type=team_type).all()

        # Determine ordering based on dependency type
        if game.dependency_type == DependencyType.TIME_DEPENDENT:
            game_points.sort(key=lambda x: x.time_taken)  # Lower is better
        elif game.dependency_type == DependencyType.POINT_DEPENDENT:
            game_points.sort(key=lambda x: x.points, reverse=True)  # Higher is better

        # Assign ranks within each team type
        for rank, game_point in enumerate(game_points, start=1):
            game_point.final_points = rank
            db.session.add(game_point)

            # Get or create log, then update points
            log = Log.query.filter_by(team_id=game_point.team_id, game_id=game_point.game_id).first()
            if not log:
                log = Log(team_id=game_point.team_id, game_id=game_point.game_id, points=game_point.points)
            else:
                log.points = game_point.points
            db.session.add(log)
    db.session.commit()


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


@gog.route("/")
def redirectToLogin():
    return redirect("/gog/login")


# Add decorator for regular users only
def regular_user_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.is_administrator:
            flash("Please login with a regular user account to access this area.")
            return redirect(url_for('gog.login'))
        return f(*args, **kwargs)
    return decorated_function

@gog.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username, is_admin=False).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("gog.dashboard"))
        else:
            flash("Invalid username or password for regular user account")
            return render_template("gog/gog_login.html")
            
    return render_template("gog/gog_login.html")


# Update all protected routes to use both decorators
@gog.route("/dashboard")
@login_required
@regular_user_required
def dashboard():
    return render_template("gog/gog_dashboard.html")


@gog.route("/setup", methods=["GET", "POST"])
@login_required
def setup():
    if request.method == "POST":
        pass
    else:
        return render_template("gog/gog_setup.html")


# Add regular_user_required to other routes
@gog.route("/ranking")
@login_required
@regular_user_required
def ranking():
    try:
        a_teams = Teams.query.filter_by(team_type=TeamType.A).all()
        b_teams = Teams.query.filter_by(team_type=TeamType.B).all()

        game_leaderboards = {
            'A_Teams': [],
            'B_Teams': []
        }

        games = Game.query.all()
        for game in games:
            a_team_ranking = GamePoints.query.filter_by(game_id=game.id, team_type=TeamType.A).order_by(GamePoints.final_points).all()
            b_team_ranking = GamePoints.query.filter_by(game_id=game.id, team_type=TeamType.B).order_by(GamePoints.final_points).all()
            game_leaderboards['A_Teams'].append((game, a_team_ranking))
            game_leaderboards['B_Teams'].append((game, b_team_ranking))

        return render_template("gog/gog_ranking.html", a_teams=a_teams, b_teams=b_teams, game_leaderboards=game_leaderboards)
    
    except Exception as e:
        current_app.logger.error(f"Error in ranking route: {e}")
        return render_template("error.html", error=str(e))


@gog.route("/teamManagement", methods=["GET", "POST"])
@login_required
@regular_user_required
def teamManagement():

    if request.method == "POST":
        team_id = request.form.get("team_id")
        game_id = request.form.get("game_id")
        points = request.form.get("points")

        game_point = GamePoints(team_id=team_id, game_id=game_id, points=points)
        db.session.add(game_point)
        db.session.commit()

        calculate_ranked_points(game_id)

        return redirect(url_for("gog.teamManagement"))
    teams = Teams.query.all()
    games = Game.query.all()
    return render_template("gog/gog_teamManagement.html", teams=teams, games=games)


@gog.route("/logs", methods=["GET", "POST"])
@login_required
@regular_user_required
def logs():
    if request.method == "POST":
        pass
    else:
        return render_template("gog/gog_logs.html")


@gog.route("/logout")
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('gog.login'))
