import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    
    # Create tasks table
    c.execute("""
        CREATE TABLE IF NOT EXISTS tasks(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            status TEXT DEFAULT 'todo',
            day TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    # Create users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            email TEXT,
            phone TEXT,
            nationalID TEXT,
            passport TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

def add_task(name, day, user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO tasks (name, day, user_id) VALUES (?, ?, ?)",
              (name, day, user_id))
    conn.commit()
    conn.close()

def get_tasks(user_id=None):
    conn = get_db_connection()
    
    if user_id:
        tasks = conn.execute("""
            SELECT tasks.*, users.username 
            FROM tasks 
            JOIN users ON tasks.user_id = users.id 
            WHERE tasks.user_id = ?
            ORDER BY tasks.day, tasks.created_at
        """, (user_id,)).fetchall()
    else:
        tasks = conn.execute("""
            SELECT tasks.*, users.username 
            FROM tasks 
            JOIN users ON tasks.user_id = users.id 
            ORDER BY tasks.day, tasks.created_at
        """).fetchall()
    
    conn.close()
    return tasks

def move_task(task_id, new_status, user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE tasks SET status = ?, updated_at = ? WHERE id = ? AND user_id = ?",
              (new_status, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), task_id, user_id))
    conn.commit()
    conn.close()

def update_task(task_id, new_name, user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE tasks SET name = ?, updated_at = ? WHERE id = ? AND user_id = ?",
              (new_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), task_id, user_id))
    conn.commit()
    conn.close()

def delete_task(task_id, user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id))
    conn.commit()
    conn.close()