
import re  
import os
from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
from datetime import datetime
import MySQLdb.cursors

app = Flask(__name__) 

app.secret_key = 'abcdefgh'
  
app.config['MYSQL_HOST'] = 'db'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'password'
app.config['MYSQL_DB'] = 'cs353hw4db'
  
mysql = MySQL(app)  

@app.route('/')

@app.route('/login', methods =['GET', 'POST'])
def login():
    message = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM User WHERE username = % s AND password = % s', (username, password, ))
        user = cursor.fetchone()
        if user:              
            session['loggedin'] = True
            session['userid'] = user['id']
            session['username'] = user['username']
            session['email'] = user['email']
            message = 'Logged in successfully!'
            return redirect(url_for('tasks', user_id=user['id']))
        else:
            message = 'Please enter correct email / password !'
    return render_template('login.html', message = message)


@app.route('/register', methods =['GET', 'POST'])
def register():
    message = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form :
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT MAX(id) FROM User')
        max_id = cursor.fetchone()["MAX(id)"]
        max_id = max_id + 1
        cursor.execute('SELECT * FROM User WHERE username = % s', (username, ))
        account = cursor.fetchone()
        if account:
            message = 'Choose a different username!'
  
        elif not username or not password or not email:
            message = 'Please fill out the form!'

        else:
            cursor.execute('INSERT INTO User (id, username, email, password) VALUES (%s, % s, % s, % s)', (max_id, username, email, password,))
            mysql.connection.commit()
            message = 'User successfully created!'

    elif request.method == 'POST':

        message = 'Please fill all the fields!'
    return render_template('register.html', message = message)

@app.route('/tasks/<int:user_id>')
def tasks(user_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM Task WHERE user_id=%s ORDER BY deadline ASC', (user_id, ))
    tasks = cursor.fetchall()
    cursor.execute('SELECT * FROM Task WHERE user_id=%s AND status="Done" ORDER BY done_time ASC', (user_id, ))
    completed_tasks = cursor.fetchall()
    message = request.args.get('message')
    return render_template('tasks.html', tasks = tasks, message= message, user_id=user_id, completed_tasks=completed_tasks)

@app.route('/tasks/edit-add-task', methods=['GET', 'POST'])
def edit_add_task():
    task_id = request.args.get('task_id')
    user_id = request.args.get('user_id')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM TaskType')
    taskTypes = cursor.fetchall()
    if task_id:
        # Edit existing task
        cursor.execute('SELECT * FROM Task WHERE id=%s', (task_id,))
        task = cursor.fetchone()
    else:
        task = {}

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        deadline = datetime.strptime(request.form['deadline'], '%Y-%m-%d %H:%M:%S')
        selectedType =request.form['task_type']
        cursor.execute('SELECT * FROM TaskType WHERE type=%s', (selectedType,))
        task_type = cursor.fetchone()['type'] 
        selectedUser = request.form['user_id']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        taskId = request.form['task_id']
        isEdit = False
        status = 'Todo'
        doneTime = None
        if taskId:
            isEdit = True
            status = request.form['status']
            if status == 'Done':
                doneTime = datetime.strptime(request.form['done_time'], '%Y-%m-%d %H:%M:%S')

        if isEdit:
            cursor.execute('UPDATE Task SET user_id=%s ,title=%s, description=%s,status=%s, deadline=%s, done_time=%s, task_type=%s WHERE id=%s', (selectedUser ,title, description, status, deadline, doneTime, task_type, taskId))
        else:
            cursor.execute('SELECT MAX(id) FROM Task')
            max_id = cursor.fetchone()["MAX(id)"]
            max_id = max_id + 1            
            cursor.execute('INSERT INTO Task (id, title, description, status, deadline, creation_time, done_time, user_id, task_type) VALUES (%s, %s, %s, %s, %s, NOW(), NULL,%s, %s)', (max_id, title, description, status, deadline, selectedUser, task_type))
        mysql.connection.commit()

        return redirect(url_for('tasks', user_id=selectedUser))

    # Render edit/add task form
    return render_template('editAddTask.html', task=task, taskTypes=taskTypes, user_id=user_id)
@app.route('/delete_task/<int:task_id>/<int:user_id>', methods=['POST'])
def delete_task(task_id, user_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('DELETE FROM Task WHERE id=%s', (task_id, ))
    mysql.connection.commit()
    message = 'Task deleted successfully'
    return redirect(url_for('tasks', user_id=user_id, message = message))

@app.route('/change_status/<int:task_id>/<int:user_id>/<current>', methods=['POST'])
def change_status(task_id, user_id,current):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if current == 'Todo':
        cursor.execute('UPDATE Task SET status=%s, done_time=NOW()  WHERE id=%s', ('Done', task_id))
    else:
        cursor.execute('UPDATE Task SET status=%s, done_time=NULL WHERE id=%s', ('Todo',task_id))
    mysql.connection.commit()
    message = 'Task updated succesfully'
    return redirect(url_for('tasks', user_id=user_id, message = message))




@app.route('/analysis/<user_id>', methods=['GET'])
def analysis(user_id):
    if 'userid' in session and session['userid'] == int(user_id):
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        def seconds_to_readable(seconds):
            minutes, seconds = divmod(seconds, 60)
            hours, minutes = divmod(minutes, 60)
            return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"

        # Query 1
        cursor.execute("SELECT title, TIMESTAMPDIFF(SECOND, deadline, done_time) AS latency FROM Task WHERE user_id=%s AND status='Done' AND done_time > deadline", (user_id,))
        late_tasks = cursor.fetchall()
        for task in late_tasks:
            task['latency'] = seconds_to_readable(task['latency'])

        # Query 2
        cursor.execute("SELECT AVG(TIMESTAMPDIFF(SECOND, creation_time, done_time)) as avg_completion_time FROM Task WHERE user_id=%s AND status='Done'", (user_id,))
        avg_completion_time = cursor.fetchone()["avg_completion_time"]
        if avg_completion_time:
          avg_completion_time = seconds_to_readable(avg_completion_time)

        # Query 3
        cursor.execute("SELECT task_type as type, COUNT(*) as count FROM Task WHERE user_id=%s AND status='Done' GROUP BY task_type ORDER BY count DESC", (user_id,))
        completed_tasks_per_type = cursor.fetchall()

        # Query 4
        cursor.execute("SELECT title, deadline FROM Task WHERE user_id=%s AND status='Todo' ORDER BY deadline ASC", (user_id,))
        uncompleted_tasks = cursor.fetchall()

        # Query 5
        cursor.execute("SELECT title, TIMESTAMPDIFF(SECOND, creation_time, done_time) AS completion_time FROM Task WHERE user_id=%s AND status='Done' ORDER BY completion_time DESC LIMIT 2", (user_id,))
        top_2_completed_tasks = cursor.fetchall()
        for task in top_2_completed_tasks:
            task['completion_time'] = seconds_to_readable(task['completion_time'])

        return render_template('analysis.html', tasks_completed_after_deadline=late_tasks, 
            avg_completion_time=avg_completion_time, completed_tasks_per_type=completed_tasks_per_type, uncompleted_tasks=uncompleted_tasks,
                top_2_tasks=top_2_completed_tasks)
    else:
        return redirect(url_for('login'))

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
