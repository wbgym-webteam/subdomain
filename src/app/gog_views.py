from flask import Flask, render_template, request, redirect, url_for, Blueprint, current_app
from . import db
from .models import Game, Teams, GamePoints, Log, TeamType, User, DependencyType
import sqlite3

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


@gog.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        conn.close()

        if user and User.check_password(user["password_hash"], password):
            return redirect(url_for("gog.dashboard"))
        else:
            return render_template("gog/gog_login.html", error="Invalid credentials")

    return render_template("gog/gog_login.html")


@gog.route("/dashboard")
def dashboard():
    return render_template("gog/gog_dashboard.html")


@gog.route("/setup", methods=["GET", "POST"])
def setup():
    if request.method == "POST":
        pass
    else:
        return render_template("gog/gog_setup.html")


@gog.route("/ranking")
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
def logs():
    if request.method == "POST":
        pass
    else:
        return render_template("gog/gog_logs.html")
