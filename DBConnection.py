import sqlite3

DB_NAME = "data.db"

sql_statements = [
    """CREATE TABLE IF NOT EXISTS measurements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        position REAL NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    );"""
]


def get_connection():
    return sqlite3.connect(DB_NAME)


def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()

        for stmt in sql_statements:
            cursor.execute(stmt)

def save_position(lote):
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.executemany(
            "INSERT INTO measurements (position) VALUES (?)",
            [(p,) for p in lote]
        )

        conn.commit()  # 👈 asegura escritura inmediata
