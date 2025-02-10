import click
from flask.cli import with_appcontext
from getpass import getpass
from .models import User, db

@click.command('create-admin')
@with_appcontext
def create_admin_command():
    """Create a new admin user (similar to Django's createsuperuser)"""
    print("Create admin account")
    while True:
        username = input("Username: ")
        if User.query.filter_by(username=username).first():
            print("Error: Username already exists")
            continue
        break

    while True:
        password = getpass("Password: ")
        password2 = getpass("Password (again): ")
        if password != password2:
            print("Error: Passwords don't match")
            continue
        if len(password) < 8:
            print("Error: Password must be at least 8 characters long")
            continue
        break

    user = User.create_admin(username=username, password=password)
    db.session.add(user)
    db.session.commit()
    print(f"Admin user '{username}' created successfully!")
