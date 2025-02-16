CREATE TABLE students (
	student_id INTEGER NOT NULL PRIMARY KEY,
	last_name VARCHAR(80) NOT NULL,
	first_name VARCHAR(80) NOT NULL,
	grade INTEGER NOT NULL,
	logincode VARCHAR(20) NOT NULL UNIQUE
);


CREATE TABLE presentations (
	presentation_id INTEGER NOT NULL PRIMARY KEY,
	title VARCHAR(120) NOT NULL,
	presenter VARCHAR(80) NOT NULL,
	abstract VARCHAR(250),
	grades VARCHAR(20) NOT NULL
);
