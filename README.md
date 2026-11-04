# MiniSQLite

A small educational database system that runs in the terminal and accepts SQL-like commands.
Users can create tables and add, view, modify and delete data. Data is saved to a local JSON file.

## Requirements

- Python 3.6 or newer
- No external libraries (uses only Python's built-in `json`, `os` and `re` modules)

## How to run

```
python3 minisqlite.py
```

## Supported commands

Each SQL command is written on one line and ends with `;`. Keywords can be uppercase or lowercase.

| Command | Example |
|---|---|
| Create a table | `CREATE TABLE students (id INTEGER, name TEXT, age INTEGER);` |
| Add a row | `INSERT INTO students VALUES (1, 'Ani', 20);` |
| View all rows | `SELECT * FROM students;` |
| View matching rows | `SELECT * FROM students WHERE id = 1;` |
| Change a value | `UPDATE students SET age = 21 WHERE id = 1;` |
| Delete rows | `DELETE FROM students WHERE id = 2;` |

Supported types: `INTEGER` (whole numbers) and `TEXT` (in single quotes, e.g. `'Ani'`).

Service commands:

| Command | Action |
|---|---|
| `.help` | Show supported commands and examples |
| `.tables` | List all tables |
| `.exit` | Quit the program |

## Example session

```
minidb> CREATE TABLE students (id INTEGER, name TEXT, age INTEGER);
Table 'students' created.
minidb> INSERT INTO students VALUES (1, 'Ani', 20);
1 row inserted.
minidb> INSERT INTO students VALUES (2, 'Aram', 22);
1 row inserted.
minidb> SELECT * FROM students;
id | name | age
---+------+----
1  | Ani  | 20
2  | Aram | 22
(2 rows)
minidb> UPDATE students SET age = 21 WHERE id = 1;
1 row updated.
minidb> DELETE FROM students WHERE id = 2;
1 row deleted.
```

## Data storage

Tables and rows are saved to `database.json`, next to the program.

- On the first run, an empty database is created.
- After every successful change, the database is saved.
- On restart, previous data is restored.

Each table stores its columns (name and type, in order) and its rows.

## Error handling

The program shows a clear message, and keeps running, when:

- a table or column does not exist
- a command has invalid syntax
- the number of values does not match the number of columns
- a value's type does not match the column's type

A failed command never changes the saved data. Every command is fully checked before anything is modified.
Saving writes to a temporary file first, so an interrupted save cannot damage the existing database.

## Design decisions and limitations

- `WHERE` supports one equality condition (`column = value`) and applies to all matching rows.
- `UPDATE` and `DELETE` without `WHERE` apply to all rows, as in SQLite.
- `UPDATE` changes one column per command.
- `SELECT` supports only `*`.
- Table and column names may contain only Latin letters, digits and `_`, and are case-sensitive.
- Not supported: JOIN, ORDER BY, indexes, transactions, NULL, escaped quotes inside text, multiple users.

## Project structure

```
minisqlite/
├── minisqlite.py   # the program
├── README.md       # this file
└── .gitignore      # files Git should ignore
```