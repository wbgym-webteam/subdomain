# Subdomain for _wbgym.de_

This is the repository, where the Weinberg Secondary School develops a subdomain for their website wbgym.de.

# Installation Guide

1. Clone the repository using git.
2. Install the required packages using [command].
3. Create a DB-File called `src/wbgym,.db`.
4. Add the following folders under `src/`:

```
---src
 |---data
   |---tdw
     |---downloads
     |---uploads
```

5. Run the script `main.py` to start the server.

# DB Guide

1. Move to `/src` in your terminal.
2. [only once] Run `flask db init`.
3. Run `flask db migrate`.
4. Run `flask db upgrade`.

# Deployment Guide

- Pull the latest commits from the repository.
- Make the following changes to `main.py`:
  - Set debug to False
  - Set host to '0.0.0.0'

And run the `main.py`-file!
