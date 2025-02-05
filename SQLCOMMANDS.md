# SQL Commands to run on the DB

```sql
CREATE TABLE student (
    id INTEGER PRIMARY KEY,
    ID INTEGER UNIQUE NOT NULL,
    name VARCHAR(80) NOT NULL,
    first_name VARCHAR(80) NOT NULL,
    grade INTEGER NOT NULL,
    presentations TEXT  -- This column can store a string (or text) for presentations
);
```
