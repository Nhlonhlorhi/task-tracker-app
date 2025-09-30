from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = os.urandom(24).hex()  # Secure random secret key

# Database initialization
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

init_db()

# Database helper functions
def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

# Task functions
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

# -----------------------
# Routes
# -----------------------
@app.route("/")
def root():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login_page"))

@app.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        user = conn.execute(
            "SELECT id, username, password, role FROM users WHERE username = ?", 
            (username,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            flash("Login successful!", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid credentials", "danger")
        return redirect(url_for("login_page"))

    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        confirm = request.form["confirm_password"]
        role = request.form.get("role", "user")
        email = request.form.get("email")
        phone = request.form.get("phone")
        nationalID = request.form.get("nationalID")
        passport = request.form.get("passport")

        if password != confirm:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("signup"))

        hashed = generate_password_hash(password)
        conn = get_db_connection()
        try:
            conn.execute("""
                INSERT INTO users (username, password, role, email, phone, nationalID, passport)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (username, hashed, role, email, phone, nationalID, passport))
            conn.commit()
            flash("Registration successful. Please log in.", "success")
            return redirect(url_for("login_page"))
        except sqlite3.IntegrityError:
            flash("Username already exists.", "danger")
            return redirect(url_for("signup"))
        finally:
            conn.close()

    return render_template("signup.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login_page"))

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login_page"))
    
    tasks = get_tasks(session["user_id"])
    return render_template("index.html", 
                           username=session["username"], 
                           tasks=tasks)

@app.route("/add", methods=["POST"])
def add():
    if "user_id" not in session:
        return redirect(url_for("login_page"))
    
    name = request.form["name"]
    day = request.form["day"]
    user_id = session["user_id"]
    
    add_task(name, day, user_id)
    flash("Task added successfully!", "success")
    return redirect(url_for("dashboard"))

@app.route("/move/<int:task_id>/<new_status>")
def move(task_id, new_status):
    if "user_id" not in session:
        return redirect(url_for("login_page"))
    
    move_task(task_id, new_status, session["user_id"])
    return redirect(url_for("dashboard"))

@app.route("/update/<int:task_id>", methods=["POST"])
def update(task_id):
    if "user_id" not in session:
        return jsonify(success=False, error="auth"), 401
    
    data = request.get_json()
    new_name = data["name"]
    update_task(task_id, new_name, session["user_id"])
    return jsonify(success=True)

@app.route("/delete/<int:task_id>")
def delete(task_id):
    if "user_id" not in session:
        return redirect(url_for("login_page"))
    
    delete_task(task_id, session["user_id"])
    flash("Task deleted successfully!", "success")
    return redirect(url_for("dashboard"))

@app.route("/tasks")
def tasks_json():
    if "user_id" not in session:
        return jsonify([])
    
    tasks = get_tasks(session["user_id"])
    return jsonify([
        {
            "id": t["id"], 
            "name": t["name"], 
            "status": t["status"], 
            "day": t["day"], 
            "updated_at": t["updated_at"], 
            "user": t["username"]
        } for t in tasks
    ])

if __name__ == "__main__":
    app.run(debug=True)