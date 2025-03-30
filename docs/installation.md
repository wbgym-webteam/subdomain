# Installation Guide

--> [_Homepage_](index.md)

## Commands for Installing Dependencies

It is recommended to use a virtual environment to install the packages, so they do not interfer with the system packages.

```sh
pip install flask
pip install flask-sqlalchemy
pip install flask-login
pip install flask-migrate
pip install python-dotenv
pip install openpyxl
pip install python-docx
pip install gunicorn
pip install dotenv
pip install zipfile
```

Or the more simple (but rarely working) variant is to use the command `pip install .` .

## Setup

1. Create a `.env`-file in `/src/app/`, where you put in the following content:
```
SECRETKEY = "YOURSECRETKEY"
ADMIN_USERNAME = "YOURADMINUSERNAME"
ADMIN_PASSWORD = "YOURADMINPASSWORD"
```

2. Create the following directories:
```sh
/src/app/data/tdw/downloads
/src/app/data/tdw/uploads
```

3. In `main.py`: change `debug` to _False_, if you are using it for production (Deployment Guide will come...)

4. Run the `main.py`-Script!

