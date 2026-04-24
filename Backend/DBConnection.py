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

        cursor.execute("DROP TABLE IF EXISTS measurements;")

        for stmt in sql_statements:
            cursor.execute(stmt)

        conn.commit()

def save_position(lote):
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.executemany(
            "INSERT INTO measurements (position) VALUES (?)",
            [(p,) for p in lote]
        )

        conn.commit()  

def reset_measurements():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM measurements;")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='measurements';")
        conn.commit()

def get_data():
    data = []
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
        SELECT id, position, timestamp
        FROM measurements
        ORDER BY timestamp 
    """
        )
    
        rows = cursor.fetchall()

    
    for row in rows:
        data.append({
            "id": row[0],
            "position": row[1],
            "timestamp": row[2]
        })


    return data

