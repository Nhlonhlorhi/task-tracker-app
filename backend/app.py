from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import sqlite3
from datetime import datetime, timedelta, date
import os
import re
import hashlib
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# -----------------------
# App config
# -----------------------
app = Flask(__name__)
app.secret_key = "dev_secret_change_me"

# Database path (adjust if needed)
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "database", "database.db")

# SMTP (only used if you replace placeholders)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = "your_email@gmail.com"    # replace with real email to enable SMTP sending
SMTP_PASSWORD = "your_app_password"       # replace with app password if using Gmail

# -----------------------
# Database helpers
# -----------------------
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    # Ensure database folder exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        full_name TEXT,
        email TEXT UNIQUE,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (DATETIME('now'))
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS tasks(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        priority TEXT NOT NULL DEFAULT 'medium',
        estimated_duration REAL,
        day TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'todo',
        user_id INTEGER NOT NULL,
        created_at TEXT NOT NULL DEFAULT (DATETIME('now')),
        updated_at TEXT NOT NULL DEFAULT (DATETIME('now')),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS time_entries(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT,
        duration_minutes INTEGER,
        work_date TEXT NOT NULL,
        FOREIGN KEY (task_id) REFERENCES tasks(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS password_resets(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        otp TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (DATETIME('now')),
        expires_at TEXT NOT NULL,
        used INTEGER DEFAULT 0,
        FOREIGN KEY (email) REFERENCES users(email)
    )
    """)

    # Optional sample users (only inserted if not present)
    sample_users = [
        ("john_doe", "John Doe", "john@example.com", hash_password("Password123!")),
        ("alice_smith", "Alice Smith", "alice@example.com", hash_password("Password123!")),
        ("robert_johnson", "Robert Johnson", "robert@example.com", hash_password("Password123!"))
    ]
    for username, full_name, email, password_hash in sample_users:
        c.execute("SELECT id FROM users WHERE username = ?", (username,))
        if not c.fetchone():
            c.execute("INSERT INTO users (username, full_name, email, password_hash) VALUES (?, ?, ?, ?)",
                      (username, full_name, email, password_hash))

    conn.commit()
    conn.close()

# Password hashing/verifying
def hash_password(password):
    salt = secrets.token_hex(16)
    salted = salt + password
    hashed = hashlib.sha256(salted.encode()).hexdigest()
    return f"{salt}${hashed}"

def verify_password(stored_password, provided_password):
    if not stored_password or '$' not in stored_password:
        return False
    salt, hashed = stored_password.split('$', 1)
    return hashlib.sha256((salt + provided_password).encode()).hexdigest() == hashed

# Password strength validator
def validate_password(password):
    if len(password) < 8:
        return "Password must be at least 8 characters long"
    if not re.search(r"[A-Z]", password):
        return "Password must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return "Password must contain at least one lowercase letter"
    if not re.search(r"\d", password):
        return "Password must contain at least one number"
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return "Password must contain at least one special character"
    return None

# OTP generation
def generate_otp():
    return str(secrets.randbelow(90000) + 10000)

# Send OTP: development prints OTP; if SMTP credentials are replaced it will attempt to send
def send_otp_email(email, otp):
    """
    Attempts to send email via SMTP if SMTP_USERNAME/PASSWORD are replaced.
    Falls back to printing OTP to console (development mode).
    Returns True if OTP is "sent" (or printed).
    """
    # If SMTP placeholders weren't replaced, fall back to dev print
    if SMTP_USERNAME == "your_email@gmail.com" or SMTP_PASSWORD == "your_app_password":
        print(f"[DEV] OTP for {email}: {otp}")
        return True

    # Attempt to send real email via SMTP
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Password Reset OTP - Task Tracker"
        msg["From"] = SMTP_USERNAME
        msg["To"] = email

        text = f"Your OTP code is: {otp}\nThis code expires in 10 minutes."
        html = f"""
        <html><body>
        <h3>Password Reset Request</h3>
        <p>Your One-Time Password (OTP) is: <strong>{otp}</strong></p>
        <p>This OTP will expire in 10 minutes.</p>
        </body></html>
        """
        part1 = MIMEText(text, "plain")
        part2 = MIMEText(html, "html")
        msg.attach(part1)
        msg.attach(part2)

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(SMTP_USERNAME, [email], msg.as_string())
        server.quit()
        return True
    except Exception as e:
        # fallback to printing OTP and logging error
        print(f"[SMTP ERROR] Could not send OTP via SMTP: {e}")
        print(f"[DEV] OTP for {email}: {otp}")
        return True

# Initialize DB
init_db()

# -----------------------
# Business helpers
# -----------------------
def current_user():
    if "user_id" in session and "username" in session:
        return {"id": session["user_id"], "username": session["username"]}
    return None

def week_bounds(any_date=None):
    if any_date is None:
        any_date = date.today()
    monday = any_date - timedelta(days=any_date.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday

# Task helpers
def add_task(name, day, user_id, description=None, priority="medium", estimated_duration=None):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
    INSERT INTO tasks (title, description, priority, estimated_duration, day, user_id)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (name, description, priority, estimated_duration, day, user_id))
    conn.commit()
    conn.close()

def get_tasks(user_id=None):
    conn = get_conn()
    c = conn.cursor()
    if user_id:
        c.execute("""
        SELECT tasks.*, users.username, users.full_name
        FROM tasks
        JOIN users ON users.id = tasks.user_id
        WHERE tasks.user_id = ?
        ORDER BY CASE status
            WHEN 'todo' THEN 1
            WHEN 'inprogress' THEN 2
            WHEN 'done' THEN 3
        END, created_at DESC
        """, (user_id,))
    else:
        c.execute("""
        SELECT tasks.*, users.username, users.full_name
        FROM tasks
        JOIN users ON users.id = tasks.user_id
        ORDER BY CASE status
            WHEN 'todo' THEN 1
            WHEN 'inprogress' THEN 2
            WHEN 'done' THEN 3
        END, created_at DESC
        """)
    rows = c.fetchall()
    conn.close()
    return rows

def move_task(task_id, new_status):
    conn = get_conn()
    c = conn.cursor()
    if new_status == "done":
        open_entry = c.execute("""
        SELECT id, start_time FROM time_entries
        WHERE task_id = ? AND end_time IS NULL
        ORDER BY id DESC LIMIT 1
        """, (task_id,)).fetchone()
        if open_entry:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            c.execute("""
            UPDATE time_entries
               SET end_time = ?, duration_minutes = CAST((JULIANDAY(?) - JULIANDAY(start_time)) * 24 * 60 AS INTEGER)
             WHERE id = ?
            """, (now, now, open_entry["id"]))
    c.execute("""
    UPDATE tasks SET status = ?, updated_at = ?
    WHERE id = ?
    """, (new_status, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), task_id))
    conn.commit()
    conn.close()

# -----------------------
# Routes
# -----------------------
@app.route("/")
def index():
    return redirect(url_for("login"))

# Login route
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = (request.form.get("password") or "").strip()
        if not username or not password:
            flash("Please enter both username and password.", "danger")
            return redirect(url_for("login"))

        conn = get_conn()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if not user or not verify_password(user["password_hash"], password):
            flash("Invalid username or password.", "danger")
            return redirect(url_for("login"))

        session["user_id"] = user["id"]
        session["username"] = user["username"]
        flash("Logged in successfully.", "success")
        return redirect(url_for("dashboard"))

    return render_template("login.html")

# Signup
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        full_name = (request.form.get("full_name") or "").strip()
        email = (request.form.get("email") or "").strip()
        password = request.form.get("password") or ""
        confirm_password = request.form.get("confirm_password") or ""

        if not username:
            flash("Username is required.", "danger")
            return redirect(url_for("signup"))
        if not full_name:
            flash("Full name is required.", "danger")
            return redirect(url_for("signup"))
        if not email:
            flash("Email is required.", "danger")
        if not password:
            flash("Password is required.", "danger")
            return redirect(url_for("signup"))
        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("signup"))

        pw_err = validate_password(password)
        if pw_err:
            flash(pw_err, "danger")
            return redirect(url_for("signup"))

        conn = get_conn()
        existing = conn.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email)).fetchone()
        if existing:
            flash("Username or email already exists.", "danger")
            conn.close()
            return redirect(url_for("signup"))

        conn.execute("INSERT INTO users (username, full_name, email, password_hash) VALUES (?, ?, ?, ?)",
                     (username, full_name, email, hash_password(password)))
        conn.commit()
        conn.close()
        flash("Account created successfully. Please login.", "success")
        return redirect(url_for("login"))

    return render_template("signup.html")

# Logout
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("login"))

# Forgot password (shows form & sends OTP)
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        if not email:
            flash("Please enter your email address.", "danger")
            return redirect(url_for("forgot_password"))

        conn = get_conn()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if not user:
            flash("No account found with that email address.", "danger")
            conn.close()
            return redirect(url_for("forgot_password"))

        # Generate and store OTP
        otp = generate_otp()
        expires_at = (datetime.now() + timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("UPDATE password_resets SET used = 1 WHERE email = ?", (email,))
        conn.execute("INSERT INTO password_resets (email, otp, expires_at) VALUES (?, ?, ?)",
                     (email, otp, expires_at))
        conn.commit()
        conn.close()

        # Send (or print) OTP
        send_otp_email(email, otp)

        session['reset_email'] = email
        flash("OTP sent to your email address. Please check your inbox (or console in dev).", "success")
        return redirect(url_for("verify_otp"))

    return render_template("forgot_password.html")

# Verify OTP
@app.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    if 'reset_email' not in session:
        flash("Please request a password reset first.", "danger")
        return redirect(url_for("forgot_password"))

    email = session['reset_email']
    if request.method == "POST":
        otp = (request.form.get("otp") or "").strip()
        if not otp or len(otp) != 5:
            flash("Please enter a valid 5-digit OTP.", "danger")
            return redirect(url_for("verify_otp"))

        conn = get_conn()
        reset_request = conn.execute("""
            SELECT * FROM password_resets
            WHERE email = ? AND otp = ? AND used = 0 AND expires_at > DATETIME('now')
            ORDER BY created_at DESC LIMIT 1
        """, (email, otp)).fetchone()

        if not reset_request:
            flash("Invalid or expired OTP. Please try again.", "danger")
            conn.close()
            return redirect(url_for("verify_otp"))

        # Mark used
        conn.execute("UPDATE password_resets SET used = 1 WHERE id = ?", (reset_request["id"],))
        conn.commit()
        conn.close()

        session['otp_verified'] = True
        flash("OTP verified successfully. You can now reset your password.", "success")
        return redirect(url_for("reset_password"))

    return render_template("verify_otp.html")

# Reset password
@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    if 'reset_email' not in session or not session.get('otp_verified'):
        flash("Please verify your OTP first.", "danger")
        return redirect(url_for("forgot_password"))

    email = session['reset_email']
    if request.method == "POST":
        password = request.form.get("password") or ""
        confirm_password = request.form.get("confirm_password") or ""
        if not password:
            flash("Password is required.", "danger")
            return redirect(url_for("reset_password"))
        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("reset_password"))
        pw_err = validate_password(password)
        if pw_err:
            flash(pw_err, "danger")
            return redirect(url_for("reset_password"))

        conn = get_conn()
        conn.execute("UPDATE users SET password_hash = ? WHERE email = ?", (hash_password(password), email))
        conn.commit()
        conn.close()

        session.pop('reset_email', None)
        session.pop('otp_verified', None)
        flash("Password reset successfully. Please login with your new password.", "success")
        return redirect(url_for("login"))

    return render_template("reset_password.html")

# Dashboard
@app.route("/dashboard")
def dashboard():
    user = current_user()
    if not user:
        return redirect(url_for("login"))

    conn = get_conn()
    users = conn.execute("SELECT id, username, full_name FROM users").fetchall()

    tasks = get_tasks(user["id"])

    start, end = week_bounds()
    entries = conn.execute("""
    SELECT te.*, t.title, u.full_name
      FROM time_entries te
      JOIN tasks t ON t.id = te.task_id
      JOIN users u ON u.id = te.user_id
     WHERE te.work_date BETWEEN ? AND ?
     ORDER BY te.work_date, te.start_time
    """, (start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))).fetchall()

    days = [(start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
    day_names = [(start + timedelta(days=i)).strftime("%a<br>%d") for i in range(7)]

    timesheet_data = {}
    for user_row in users:
        uid = user_row["id"]
        full_name = user_row["full_name"] or ""
        initials = "".join([n[0] for n in full_name.split()][:2]).upper() if full_name else ""
        timesheet_data[uid] = {"full_name": full_name, "initials": initials, "days": {d: 0 for d in days}}

    for entry in entries:
        uid = entry["user_id"]
        wdate = entry["work_date"]
        hours = round((entry["duration_minutes"] or 0) / 60, 1)
        if uid in timesheet_data and wdate in timesheet_data[uid]["days"]:
            timesheet_data[uid]["days"][wdate] += hours

    conn.close()

    return render_template("dashboard.html",
                           username=user["username"],
                           users=users,
                           tasks=tasks,
                           timesheet_data=timesheet_data,
                           days=days,
                           day_names=day_names,
                           start=start,
                           end=end)

# Add task (form)
@app.route("/add", methods=["POST"])
def add():
    user = current_user()
    if not user:
        return jsonify({"success": False, "message": "Not authenticated"}), 401

    name = request.form.get('name') or ""
    day = request.form.get('day') or "Monday"
    if not name:
        flash("Task name is required.", "danger")
        return redirect(url_for("dashboard"))

    add_task(name, day, user["id"])
    flash("Task added.", "success")
    return redirect(url_for("dashboard"))

# Move task
@app.route("/move/<int:task_id>/<new_status>")
def move(task_id, new_status):
    user = current_user()
    if not user:
        return redirect(url_for("login"))
    if new_status not in ("todo", "inprogress", "done"):
        flash("Invalid status.", "danger")
        return redirect(url_for("dashboard"))
    move_task(task_id, new_status)
    return redirect(url_for("dashboard"))

@app.route("/task/move/<int:task_id>/<status>", methods=["POST"])
def task_move(task_id, status):
    return move(task_id, status)

# Update task (inline)
@app.route("/update/<int:task_id>", methods=["POST"])
def update(task_id):
    user = current_user()
    if not user:
        return jsonify({"success": False, "message": "Not authenticated"}), 401

    data = request.get_json()
    new_name = data.get('name', '')
    if not new_name:
        return jsonify({"success": False, "message": "Task name cannot be empty"})

    conn = get_conn()
    conn.execute("UPDATE tasks SET title=?, updated_at=? WHERE id=?",
                 (new_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), task_id))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Task updated."})

# Timer start/stop
@app.route("/timer/start/<int:task_id>", methods=["POST"])
def timer_start(task_id):
    user = current_user()
    if not user:
        return jsonify({"success": False, "message": "Not authenticated"}), 401

    now = datetime.now()
    work_date = now.strftime("%Y-%m-%d")
    conn = get_conn()
    t = conn.execute("SELECT id FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if not t:
        conn.close()
        return jsonify({"success": False, "message": "Task not found."})

    # stop any previous running timer for same task & user
    conn.execute("""
    UPDATE time_entries
       SET end_time = ?, duration_minutes = CAST((JULIANDAY(?) - JULIANDAY(start_time)) * 24 * 60 AS INTEGER)
     WHERE task_id = ? AND user_id = ? AND end_time IS NULL
    """, (now.strftime("%Y-%m-%d %H:%M:%S"), now.strftime("%Y-%m-%d %H:%M:%S"), task_id, user["id"]))

    conn.execute("""
    INSERT INTO time_entries (task_id, user_id, start_time, work_date)
    VALUES (?,?,?,?)
    """, (task_id, user["id"], now.strftime("%Y-%m-%d %H:%M:%S"), work_date))

    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Timer started."})

@app.route("/timer/stop/<int:task_id>", methods=["POST"])
def timer_stop(task_id):
    user = current_user()
    if not user:
        return jsonify({"success": False, "message": "Not authenticated"}), 401

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_conn()
    open_entry = conn.execute("""
    SELECT id, start_time FROM time_entries
    WHERE task_id = ? AND user_id = ? AND end_time IS NULL
    ORDER BY id DESC LIMIT 1
    """, (task_id, user["id"])).fetchone()
    if not open_entry:
        conn.close()
        return jsonify({"success": False, "message": "No running timer for this task."})

    conn.execute("""
    UPDATE time_entries
       SET end_time = ?, duration_minutes = CAST((JULIANDAY(?) - JULIANDAY(start_time)) * 24 * 60 AS INTEGER)
     WHERE id = ?
    """, (now, now, open_entry["id"]))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Timer stopped."})

# Timesheet (per-day detail) - this supplies per_day, totals, week_total for your template
@app.route("/timesheet")
def timesheet():
    user = current_user()
    if not user:
        return redirect(url_for("login"))

    date_str = request.args.get("date")
    view_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else date.today()
    start, end = week_bounds(view_date)

    conn = get_conn()
    rows = conn.execute("""
        SELECT te.*, t.title
        FROM time_entries te
        JOIN tasks t ON t.id = te.task_id
        WHERE te.user_id=? AND te.work_date BETWEEN ? AND ?
        ORDER by te.work_date, te.start_time
    """, (user["id"], start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))).fetchall()
    conn.close()

    days = [(start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
    per_day = {d: [] for d in days}
    totals = {d: 0 for d in days}

    for r in rows:
        d = r["work_date"]
        if d in per_day:
            per_day[d].append(r)
            totals[d] += r["duration_minutes"] or 0

    week_total = sum(totals.values())

    return render_template("timesheet.html",
                           username=user["username"],
                           start=start,
                           end=end,
                           days=days,
                           per_day=per_day,
                           totals=totals,
                           week_total=week_total)

# Weekly report
@app.route("/report/weekly")
def weekly_report():
    user = current_user()
    if not user:
        return redirect(url_for("login"))

    start, end = week_bounds()
    conn = get_conn()
    entries = conn.execute("""
    SELECT duration_minutes FROM time_entries
    WHERE user_id = ? AND work_date BETWEEN ? AND ?
    """, (user["id"], start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))).fetchall()

    minutes = sum((e["duration_minutes"] or 0) for e in entries)
    hours_worked = round(minutes / 60, 2)

    tasks_total_row = conn.execute("""
    SELECT COUNT(*) AS n FROM tasks
    WHERE user_id = ? AND DATE(created_at) BETWEEN ? AND ?
    """, (user["id"], start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))).fetchone()
    tasks_total = tasks_total_row["n"] if tasks_total_row else 0

    tasks_done_row = conn.execute("""
    SELECT COUNT(*) AS n FROM tasks
    WHERE user_id = ? AND status = 'done' AND DATE(created_at) BETWEEN ? AND ?
    """, (user["id"], start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))).fetchone()
    tasks_done = tasks_done_row["n"] if tasks_done_row else 0

    completion_rate = (tasks_done / tasks_total) * 100 if tasks_total else 0
    hours_score = min(hours_worked / 40.0, 1.0) * 100
    raw_score = 0.6 * completion_rate + 0.4 * hours_score
    rating = round(raw_score / 20, 1)

    conn.close()

    return render_template("weekly_report.html",
                           username=user["username"],
                           start=start,
                           end=end,
                           hours_worked=hours_worked,
                           tasks_total=tasks_total,
                           tasks_done=tasks_done,
                           completion_rate=round(completion_rate, 1),
                           rating=rating)

# Task add endpoint for templates expecting task_add
@app.route("/task/add", methods=["POST"])
def task_add():
    user = current_user()
    if not user:
        return redirect(url_for("login"))
    
    title = (request.form.get("title") or "").strip()
    description = (request.form.get("description") or "").strip()
    priority = request.form.get("priority") or "medium"
    estimated_duration = request.form.get("estimated_duration")
    day = request.form.get("day") or "Monday"
    assigned_to = request.form.get("assigned_to") or user["id"]
    
    if not title:
        flash("Task title is required.", "danger")
        return redirect(url_for("dashboard"))
    
    try:
        estimated_duration = float(estimated_duration) if estimated_duration else None
    except ValueError:
        estimated_duration = None
    
    conn = get_conn()
    conn.execute("""
    INSERT INTO tasks (title, description, priority, estimated_duration, day, user_id) 
    VALUES (?,?,?,?,?,?)
    """, (title, description, priority, estimated_duration, day, assigned_to))
    conn.commit()
    conn.close()
    
    flash("Task added.", "success")
    return redirect(url_for("dashboard"))

# Task delete endpoint
@app.route("/task/delete/<int:task_id>", methods=["POST"])
def task_delete(task_id):
    user = current_user()
    if not user:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    
    conn = get_conn()
    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    
    flash("Task deleted successfully.", "success")
    return redirect(url_for("dashboard"))

# API endpoints for AJAX calls
@app.route("/api/tasks")
def api_tasks():
    user = current_user()
    if not user:
        return jsonify({"error": "Not authenticated"}), 401
    
    tasks = get_tasks(user["id"])
    
    result = []
    for task in tasks:
        result.append(dict(task))
    
    return jsonify(result)

@app.route("/api/users")
def api_users():
    user = current_user()
    if not user:
        return jsonify({"error": "Not authenticated"}), 401
    
    conn = get_conn()
    users = conn.execute("SELECT id, username, full_name FROM users").fetchall()
    
    result = []
    for user in users:
        result.append(dict(user))
    
    conn.close()
    return jsonify(result)

# -----------------------
# Run
# -----------------------
if __name__ == "__main__":
    app.run(debug=True)