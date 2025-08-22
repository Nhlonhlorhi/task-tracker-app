from flask import Flask, render_template, request, redirect, session, jsonify
from flask import Flask, render_template, request, redirect, jsonify
import sqlite3
from datetime import datetime
from models import init_db, add_task, get_tasks, move_task

app = Flask(__name__)
init_db()
app = Flask(__name__)
app.secret_key = "your_secret_key"  # Replace with a strong random string

# Home page
@app.route('/')
def home():
    return render_template('index.html')

# Add new task
@app.route('/add', methods=['POST'])
def add():
    name = request.form['name']
    day = request.form['day']
    add_task(name, day)
    return redirect('/')

# Move task to new status
@app.route('/move/<int:task_id>/<new_status>')
def move(task_id, new_status):
    move_task(task_id, new_status)
    return redirect('/')

# Update task name inline
@app.route('/update/<int:task_id>', methods=['POST'])
def update(task_id):
    data = request.get_json()
    new_name = data['name']
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("UPDATE tasks SET name=?, updated_at=? WHERE id=?",
              (new_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), task_id))
    conn.commit()
    conn.close()
    return jsonify(success=True)

# JSON endpoint for live updates
@app.route('/tasks')
def tasks_json():
    tasks = get_tasks()
    return jsonify([{'id': t[0], 'name': t[1], 'status': t[2], 'day': t[3], 'updated_at': t[4]} for t in tasks])

if __name__ == "__main__":
    app.run(debug=True)

