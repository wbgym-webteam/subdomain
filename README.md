# Subdomain for _wbgym.de_

This is the repository, where the Weinberg Secondary School develops a subdomain for their website wbgym.de.

## Installation Guide

1. Clone the repository using git.
2. Install the required packages using [command].
3.1. Create a DB-File called `src/wbgym,.db`.
3.2. Run the SQL-Commands to create the tables in the DB-File. (temporary solution, there will be a script to run for that)
4. Add the following folders under `src/`:

```text
---src
 |---data
   |---tdw
     |---downloads
     |---uploads
```

5. Create a file called `/app/.env` with the following content:

```.env
SECRET_KEY = 'yoursecretkey'
```

6. Run the script `main.py` to start the server.

## DB Guide

1. Move to `/src` in your terminal.
2. [only once] Run `flask db init`.
3. Run `flask db migrate`.
4. Run `flask db upgrade`.

## Deployment Guide

- Pull the latest commits from the repository.
- Run `flask db upgrade` to update the database.
- Make the following changes to `main.py`:
  - Set debug to False
  - Set host to '0.0.0.0'

And run the `main.py`-file!
