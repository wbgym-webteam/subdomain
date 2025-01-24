import sqlite3


def migrate(db):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()

    # Create users table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        )
    """
    )

    conn.commit()
    conn.close()
