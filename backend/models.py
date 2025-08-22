import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY,
            name TEXT,
            status TEXT,
            day TEXT,
            updated_at TEXT,
            user TEXT
        )
    ''')
    conn.commit()
    conn.close()


def add_task(name, day, user="Unknown"):
    import sqlite3
    from datetime import datetime
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("INSERT INTO tasks (name, status, day, updated_at, user) VALUES (?, ?, ?, ?, ?)",
              (name, "Backlog", day, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user))
    conn.commit()
    conn.close()



def get_tasks():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM tasks")
    tasks = c.fetchall()
    conn.close()
    return tasks

def move_task(task_id, new_status):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("UPDATE tasks SET status=?, updated_at=? WHERE id=?",
              (new_status, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), task_id))
    conn.commit()
    conn.close()

