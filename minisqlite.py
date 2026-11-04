import json
import os
import re

# The database file always lives next to this script,
# no matter which folder you start the program from
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.json")

HELP_TEXT = """Supported commands (each ends with ;):
  CREATE TABLE students (id INTEGER, name TEXT, age INTEGER);
  INSERT INTO students VALUES (1, 'Ani', 20);
  SELECT * FROM students;
  SELECT * FROM students WHERE id = 1;
  UPDATE students SET age = 21 WHERE id = 1;
  DELETE FROM students WHERE id = 2;

  WHERE supports one condition: column = value
  UPDATE/DELETE without WHERE apply to all rows

Service commands:
  .help     show this help
  .tables   list all tables
  .exit     quit the program"""


# Our own error type, for friendly messages
class DBError(Exception):
    pass


# Names may use only Latin letters, digits and _ (not starting with a digit)
def check_name(name):
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise DBError(f"invalid name '{name}'. Use Latin letters, digits and _ only")


# ---------- Saving and loading ----------

def load_db():
    if not os.path.exists(DB_FILE):
        db = {}
        save_db(db)
        return db
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            db = json.load(f)
    except json.JSONDecodeError:
        db = None
    if not isinstance(db, dict):
        # Stop instead of overwriting the user's file with an empty database
        raise SystemExit("Error: database.json is damaged and cannot be read. "
                         "Fix or delete it, then start again.")
    return db


def save_db(db):
    # Write to a temporary file first, then swap it in.
    # If the program is interrupted mid-save, the old file stays intact.
    temp_file = DB_FILE + ".tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)
    os.replace(temp_file, DB_FILE)


# ---------- Helpers ----------

# Find a table or raise a clear error
def get_table(db, name):
    if name not in db:
        raise DBError(f"table '{name}' does not exist")
    return db[name]


# Find a column in a table or raise a clear error
def get_column(table, name):
    for column in table["columns"]:
        if column["name"] == name:
            return column
    raise DBError(f"column '{name}' does not exist")


# Split "1, 'Ani', 20" into ["1", "'Ani'", "20"], ignoring commas inside quotes
def split_values(text):
    parts = []
    current = ""
    in_quotes = False
    for ch in text:
        if ch == "'":
            in_quotes = not in_quotes
        if ch == "," and not in_quotes:
            parts.append(current.strip())
            current = ""
        else:
            current += ch
    if in_quotes:
        raise DBError("missing closing quote '")
    parts.append(current.strip())
    return parts


# Turn "'Ani'" into Ani (text) and "20" into 20 (number)
def parse_value(text):
    if len(text) >= 2 and text.startswith("'") and text.endswith("'"):
        return text[1:-1]
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    raise DBError(f"invalid value '{text}'. Text must be in single quotes, e.g. 'Ani'")


# Make sure a value matches its column's type
def check_type(value, column):
    if column["type"] == "INTEGER" and not isinstance(value, int):
        raise DBError(f"column '{column['name']}' expects INTEGER, but got TEXT")
    if column["type"] == "TEXT" and not isinstance(value, str):
        raise DBError(f"column '{column['name']}' expects TEXT, but got INTEGER")


# Read "id = 1" into ("id", 1), checking the column and type
def parse_where(text, table):
    match = re.fullmatch(r"(\w+)\s*=\s*(.+)", text.strip())
    if not match:
        raise DBError("invalid WHERE condition. Example: WHERE id = 1")
    col_name = match.group(1)
    column = get_column(table, col_name)
    value = parse_value(match.group(2).strip())
    check_type(value, column)
    return (col_name, value)


# Does this row match the condition? (no condition = every row matches)
def row_matches(row, condition):
    if condition is None:
        return True
    col_name, value = condition
    return row[col_name] == value


# "1 row" / "2 rows"
def count_text(count):
    return f"{count} row" if count == 1 else f"{count} rows"


# Build one line of the printed table, padding each cell to its column width
def format_line(values, widths):
    return " | ".join(str(v).ljust(w) for v, w in zip(values, widths))


# Print rows as a neat table
def print_rows(columns, rows):
    names = [c["name"] for c in columns]

    # Each column is as wide as its longest value (or its name)
    widths = [len(n) for n in names]
    for row in rows:
        for i, n in enumerate(names):
            widths[i] = max(widths[i], len(str(row[n])))

    print(format_line(names, widths))
    print("-+-".join("-" * w for w in widths))
    for row in rows:
        print(format_line([row[n] for n in names], widths))

    print(f"({count_text(len(rows))})")


# ---------- Commands ----------

# CREATE TABLE name (col TYPE, col TYPE, ...)
def create_table(sql, db):
    match = re.fullmatch(r"CREATE\s+TABLE\s+(\w+)\s*\((.*)\)", sql, re.IGNORECASE)
    if not match:
        raise DBError("invalid syntax. Example: CREATE TABLE students (id INTEGER, name TEXT);")

    table_name = match.group(1)
    columns_text = match.group(2)

    check_name(table_name)
    if table_name in db:
        raise DBError(f"table '{table_name}' already exists")

    columns = []
    for part in columns_text.split(","):
        pieces = part.split()
        if len(pieces) != 2:
            raise DBError(f"invalid column definition '{part.strip()}'. Example: age INTEGER")
        col_name, col_type = pieces
        check_name(col_name)
        col_type = col_type.upper()
        if col_type not in ("INTEGER", "TEXT"):
            raise DBError(f"unknown type '{pieces[1]}'. Use INTEGER or TEXT")
        if any(c["name"] == col_name for c in columns):
            raise DBError(f"duplicate column name '{col_name}'")
        columns.append({"name": col_name, "type": col_type})

    # All checks passed: only now do we change the database
    db[table_name] = {"columns": columns, "rows": []}
    save_db(db)
    print(f"Table '{table_name}' created.")


# INSERT INTO name VALUES (v1, v2, ...)
def insert(sql, db):
    match = re.fullmatch(r"INSERT\s+INTO\s+(\w+)\s+VALUES\s*\((.*)\)", sql, re.IGNORECASE)
    if not match:
        raise DBError("invalid syntax. Example: INSERT INTO students VALUES (1, 'Ani', 20);")

    table_name = match.group(1)
    table = get_table(db, table_name)
    columns = table["columns"]
    values = [parse_value(v) for v in split_values(match.group(2))]

    if len(values) != len(columns):
        raise DBError(f"table '{table_name}' has {len(columns)} columns, but {len(values)} values were given")

    row = {}
    for column, value in zip(columns, values):
        check_type(value, column)
        row[column["name"]] = value

    # All checks passed: now change and save
    table["rows"].append(row)
    save_db(db)
    print("1 row inserted.")


# SELECT * FROM name [WHERE col = value]
def select(sql, db):
    match = re.fullmatch(r"SELECT\s+\*\s+FROM\s+(\w+)(?:\s+WHERE\s+(.+))?", sql, re.IGNORECASE)
    if not match:
        raise DBError("invalid syntax. Example: SELECT * FROM students WHERE id = 1; (only * is supported)")

    table = get_table(db, match.group(1))
    condition = None
    if match.group(2):
        condition = parse_where(match.group(2), table)

    rows = [row for row in table["rows"] if row_matches(row, condition)]
    print_rows(table["columns"], rows)


# UPDATE name SET col = value [WHERE col = value]
def update(sql, db):
    match = re.fullmatch(
        r"UPDATE\s+(\w+)\s+SET\s+(\w+)\s*=\s*(.+?)(?:\s+WHERE\s+(.+))?",
        sql, re.IGNORECASE)
    if not match:
        raise DBError("invalid syntax. Example: UPDATE students SET age = 21 WHERE id = 1;")

    # Check everything first
    table = get_table(db, match.group(1))
    column = get_column(table, match.group(2))
    new_value = parse_value(match.group(3).strip())
    check_type(new_value, column)

    condition = None
    if match.group(4):
        condition = parse_where(match.group(4), table)

    # All checks passed: now change matching rows
    count = 0
    for row in table["rows"]:
        if row_matches(row, condition):
            row[column["name"]] = new_value
            count += 1

    if count > 0:
        save_db(db)
    print(f"{count_text(count)} updated.")


# DELETE FROM name [WHERE col = value]
def delete(sql, db):
    match = re.fullmatch(r"DELETE\s+FROM\s+(\w+)(?:\s+WHERE\s+(.+))?", sql, re.IGNORECASE)
    if not match:
        raise DBError("invalid syntax. Example: DELETE FROM students WHERE id = 2;")

    # Check everything first
    table = get_table(db, match.group(1))
    condition = None
    if match.group(2):
        condition = parse_where(match.group(2), table)

    # Keep the rows that do NOT match; the rest are deleted
    kept = [row for row in table["rows"] if not row_matches(row, condition)]
    count = len(table["rows"]) - len(kept)
    table["rows"] = kept

    if count > 0:
        save_db(db)
    print(f"{count_text(count)} deleted.")


# ---------- Command router ----------

def handle_command(line, db):
    # Service commands (start with a dot); any case, optional ;
    if line.startswith("."):
        command = line.lower().rstrip(";").strip()
        if command == ".help":
            print(HELP_TEXT)
        elif command == ".tables":
            if not db:
                print("(no tables)")
            else:
                for name in db:
                    print(name)
        else:
            raise DBError(f"unknown service command '{line}'. Type .help")
        return

    # SQL commands must end with ;
    if not line.endswith(";"):
        raise DBError("command must end with ;")
    sql = line[:-1].strip()

    # Decide what to do based on the first word (any case)
    first_word = sql.split()[0].upper() if sql else ""
    if first_word == "CREATE":
        create_table(sql, db)
    elif first_word == "INSERT":
        insert(sql, db)
    elif first_word == "SELECT":
        select(sql, db)
    elif first_word == "UPDATE":
        update(sql, db)
    elif first_word == "DELETE":
        delete(sql, db)
    else:
        raise DBError("unknown command. Type .help to see supported commands")


# ---------- Main loop ----------

def main():
    db = load_db()

    print("MiniSQLite")
    print("Type .help for help.")
    print()

    while True:
        try:
            line = input("minidb> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if line == "":
            continue
        if line.lower().rstrip(";").strip() == ".exit":
            break

        try:
            handle_command(line, db)
        except Exception as e:
            print("Error:", e)


if __name__ == "__main__":
    main()