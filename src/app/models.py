from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from enum import Enum

db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)




class TeamType(Enum):
    A = 'A'
    B = 'B'

class DependencyType(Enum):
    POINT_DEPENDENT = 'point'
    TIME_DEPENDENT = 'time'

class ScoringPreference(Enum):
    BETTER_HIGHER = 'higher'
    BETTER_LOWER = 'lower'


class Teams(db.Model):
    __tablename__ = 'teams'
    id = db.Column(db.String(10), primary_key=True)  # Unique ID like a1, a2, b1, b2
    team_name = db.Column(db.String(100), nullable=True)  # Can be changed later
    points = db.Column(db.Integer, default=0)
    team_type = db.Column(db.Enum(TeamType), nullable=False)  # Choice constraint

    def __init__(self, team_type, team_number):
        self.id = f"{team_type.lower()}{team_number}"
        self.team_name = self.id  # Default name is the same as ID
        self.team_type = TeamType(team_type)

    def __repr__(self):
        return f"{self.team_name} ({self.team_type.value})"
    

class Game(db.Model):
    __tablename__ = 'games'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    dependency_type = db.Column(db.String(10), nullable=False)  # 'time' or 'point'
    scoring_preference = db.Column(db.String(10), nullable=False)  # 'higher' or 'lower'

    def __repr__(self):
        return f"{self.name} ({self.dependency_type}, {self.scoring_preference})"
    

class GamePoints(db.Model):
    __tablename__ = 'game_points'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    team_id = db.Column(db.String(10), db.ForeignKey('teams.id'), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), nullable=False)

    points = db.Column(db.Integer, default=0) #for point dependent games
    time_taken = db.Column(db.Time, nullable=True)  # Used for time-based games
    final_points = db.Column(db.Integer, default=0)  # Rank-based points

    team = db.relationship('Teams', backref=db.backref('gamepoints', lazy=True))
    game = db.relationship('Game', backref=db.backref('gamepoints', lazy=True))

    def __repr__(self):
        return f"{self.team.team_name} - {self.game.name}: {self.points} points"


class Log(db.Model):
    __tablename__ = 'logs'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    team_id = db.Column(db.String(10), db.ForeignKey('teams.id'), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), nullable=False)
    points = db.Column(db.Integer, default=0)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    team = db.relationship('Teams', backref=db.backref('logs', lazy=True))
    game = db.relationship('Game', backref=db.backref('logs', lazy=True))

    def __repr__(self):
        return f"Log: {self.team.team_name} - {self.game.name} ({self.points} points)"