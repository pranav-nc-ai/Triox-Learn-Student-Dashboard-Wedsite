from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file, session, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO, emit, join_room, leave_room
from groq import Groq
import sqlite3
import os
import random
from datetime import datetime
import pandas as pd
import json
import threading
import time
import string
import re
import base64
from werkzeug.utils import secure_filename
import pytz

IST = pytz.timezone('Asia/Kolkata')

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024



# Initialize SocketIO for real-time updates
socketio = SocketIO(app, cors_allowed_origins="*")

GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
groq_client = Groq(api_key=GROQ_API_KEY)

# Create necessary folders
os.makedirs('database', exist_ok=True)
os.makedirs('data/exports', exist_ok=True)
os.makedirs('static/assets', exist_ok=True)
os.makedirs('static/uploads', exist_ok=True)
os.makedirs('static/certificates', exist_ok=True)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ============ USER CLASSES ============

class User(UserMixin):
    def __init__(self, username, role, name):
        self.id = username
        self.username = username
        self.role = role
        self.name = name

class StudentUser(UserMixin):
    def __init__(self, student_id, name, email):
        self.id = student_id
        self.student_id = student_id
        self.name = name
        self.email = email
        self.role = 'student'

class ParentUser(UserMixin):
    def __init__(self, email, name, student_id):
        self.id = email
        self.email = email
        self.name = name
        self.student_id = student_id
        self.role = 'parent'

DEMO_USERS = {
    'admin': {'password': 'admin@123', 'role': 'admin', 'name': 'Administrator'},
    'teacher': {'password': 'teacher@123', 'role': 'teacher', 'name': 'Teacher User'},
    'viewer': {'password': 'viewer@123', 'role': 'viewer', 'name': 'Viewer User'}
}

# ============ HELPER FUNCTIONS ============

def generate_room_code():
    """Generate a unique 6-character room code"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'pdf', 'doc', 'docx', 'ppt', 'pptx', 'txt', 'jpg', 'jpeg', 'png', 'gif', 'xlsx', 'csv'}

# ============ LOAD USER ============

@login_manager.user_loader
def load_user(username):
    if username in DEMO_USERS:
        u = DEMO_USERS[username]
        return User(username, u['role'], u['name'])
    
    try:
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        cursor.execute("SELECT student_id, name, email FROM student_users WHERE student_id = ?", (username,))
        student = cursor.fetchone()
        conn.close()
        if student:
            return StudentUser(student[0], student[1], student[2])
    except:
        pass
    
    try:
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        cursor.execute("SELECT parent_email, name, student_id FROM student_users WHERE parent_email = ?", (username,))
        parent = cursor.fetchone()
        conn.close()
        if parent:
            return ParentUser(parent[0], parent[1], parent[2])
    except:
        pass
    
    return None

# ============ DATABASE INITIALIZATION ============

def init_database():
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    
    # Students table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            student_id TEXT PRIMARY KEY,
            name TEXT,
            gender TEXT,
            age INTEGER,
            study_hours REAL,
            previous_score INTEGER,
            attendance_percentage INTEGER,
            parent_education_level TEXT,
            parent_income INTEGER,
            internet_access_at_home TEXT,
            sleep_hours INTEGER,
            extracurricular_activities TEXT,
            tuition_classes TEXT,
            library_access TEXT,
            transport_facility TEXT,
            midterm_score INTEGER,
            assignment_score INTEGER,
            quiz_score INTEGER,
            project_score INTEGER,
            final_score REAL,
            grade TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS student_users (
            student_id TEXT PRIMARY KEY,
            name TEXT,
            email TEXT,
            password TEXT,
            parent_email TEXT,
            FOREIGN KEY (student_id) REFERENCES students(student_id)
        )
    ''')
    
    # Gamification tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS badges (
            badge_id INTEGER PRIMARY KEY,
            badge_name TEXT,
            badge_icon TEXT,
            description TEXT,
            requirement TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS student_badges (
            student_id TEXT,
            badge_id INTEGER,
            earned_date TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(student_id),
            FOREIGN KEY (badge_id) REFERENCES badges(badge_id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS student_points (
            student_id TEXT PRIMARY KEY,
            total_points INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            xp INTEGER DEFAULT 0,
            FOREIGN KEY (student_id) REFERENCES students(student_id)
        )
    ''')
    
    # Study Room tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS study_rooms (
            room_id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_name TEXT,
            room_code TEXT UNIQUE,
            created_by TEXT,
            subject TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS room_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id INTEGER,
            student_id TEXT,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP,
            FOREIGN KEY (room_id) REFERENCES study_rooms(room_id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS room_messages (
            message_id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id INTEGER,
            student_id TEXT,
            message TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS room_files (
            file_id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id INTEGER,
            uploaded_by TEXT,
            file_name TEXT,
            file_url TEXT,
            file_size INTEGER,
            file_type TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS whiteboard_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id INTEGER,
            drawing_data TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Goals tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS student_goals (
            goal_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            goal_title TEXT,
            target_score INTEGER,
            current_score INTEGER,
            target_date DATE,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS goal_checkpoints (
            checkpoint_id INTEGER PRIMARY KEY AUTOINCREMENT,
            goal_id INTEGER,
            checkpoint_title TEXT,
            is_completed INTEGER DEFAULT 0,
            completed_at TIMESTAMP
        )
    ''')
    
    # Quiz tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quizzes (
            quiz_id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_by TEXT,
            title TEXT,
            description TEXT,
            time_limit INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            question_id INTEGER PRIMARY KEY AUTOINCREMENT,
            quiz_id INTEGER,
            question_text TEXT,
            option_a TEXT,
            option_b TEXT,
            option_c TEXT,
            option_d TEXT,
            correct_answer TEXT,
            points INTEGER DEFAULT 1
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quiz_results (
            result_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            quiz_id INTEGER,
            score INTEGER,
            total_possible INTEGER,
            percentage REAL,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Meetings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS meetings (
            meeting_id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id TEXT,
            parent_email TEXT,
            student_id TEXT,
            meeting_date DATE,
            meeting_time TIME,
            status TEXT DEFAULT 'scheduled',
            meeting_link TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Certificates table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS certificates (
            certificate_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            certificate_type TEXT,
            issue_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            file_path TEXT,
            verified TEXT DEFAULT 'pending'
        )
    ''')
    
    # Forum tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS forum_topics (
            topic_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            title TEXT,
            content TEXT,
            views INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS forum_replies (
            reply_id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_id INTEGER,
            student_id TEXT,
            content TEXT,
            upvotes INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Doubts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS doubts (
            doubt_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            question TEXT,
            ai_answer TEXT,
            teacher_answer TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP
        )
    ''')
    
    # Study sessions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS study_sessions (
            session_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            room_id INTEGER,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            duration_minutes INTEGER
        )
    ''')
    
    # Proctoring logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS proctoring_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            quiz_id INTEGER,
            event_type TEXT,
            event_data TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert badges if not exists
    cursor.execute("SELECT COUNT(*) FROM badges")
    badge_count = cursor.fetchone()[0]
    
    if badge_count == 0:
        badges = [
            (1, 'Perfect Attendance', 'fa-calendar-check', 'Maintained 95%+ attendance for a month', 'Attendance >= 95% for 30 days'),
            (2, 'Grade Master', 'fa-star', 'Scored A+ in any subject', 'Grade = A+'),
            (3, 'Study Champion', 'fa-clock', 'Studied 7+ hours daily for 2 weeks', 'Study hours >= 7 for 14 days'),
            (4, 'Improvement Star', 'fa-chart-line', 'Improved score by 15+ points', 'Score improvement >= 15 points'),
            (5, 'Assignment Hero', 'fa-tasks', 'Completed all assignments on time', 'All assignments submitted on time'),
            (6, 'Quiz Master', 'fa-brain', 'Scored 90%+ in 5 quizzes', 'Quiz score >= 90% for 5 quizzes'),
            (7, 'Project Pro', 'fa-project-diagram', 'Scored 95%+ in project', 'Project score >= 95%'),
            (8, 'Attendance King', 'fa-crown', '100% attendance for a month', 'Attendance = 100% for 30 days'),
            (9, 'Top Performer', 'fa-trophy', 'Ranked in top 5 of class', 'Top 5 rank'),
            (10, 'Consistency Champion', 'fa-chart-simple', 'Maintained B+ grade for 2 months', 'Grade >= B for 60 days'),
        ]
        cursor.executemany('INSERT INTO badges VALUES (?,?,?,?,?)', badges)
    
    cursor.execute("SELECT COUNT(*) FROM students")
    count = cursor.fetchone()[0]
    
    if count == 0:
        print("Adding sample data to database...")
        
        sample_students = [
            ('S0001', 'John Collins', 'Male', 17, 7.5, 88, 98, "Bachelor's", 75000, 'Yes', 7, 'Yes', 'Yes', 'Yes', 'No', 88, 85, 82, 92, 89.5, 'A'),
            ('S0002', 'Emma Watson', 'Female', 17, 8.0, 92, 96, "Master's", 95000, 'Yes', 7, 'Yes', 'Yes', 'Yes', 'No', 90, 88, 85, 94, 91.2, 'A+'),
            ('S0003', 'Michael Brown', 'Male', 18, 6.5, 85, 94, "Bachelor's", 68000, 'Yes', 6, 'No', 'Yes', 'Yes', 'Yes', 82, 85, 80, 88, 84.5, 'A'),
            ('S0004', 'Sophia Lee', 'Female', 17, 7.0, 90, 92, "Master's", 88000, 'Yes', 7, 'Yes', 'Yes', 'Yes', 'No', 86, 88, 84, 90, 87.8, 'A'),
            ('S0005', 'James Wilson', 'Male', 18, 5.5, 78, 90, "Bachelor's", 62000, 'Yes', 7, 'Yes', 'No', 'Yes', 'Yes', 75, 78, 72, 80, 77.5, 'B'),
        ]
        
        for student in sample_students:
            cursor.execute('''INSERT INTO students VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', student)
        
        first_names = ['Oliver', 'Amelia', 'Harry', 'Isabella', 'George', 'Mia', 'Jack', 'Charlotte', 'Jacob', 'Emily']
        last_names = ['Smith', 'Jones', 'Williams', 'Brown', 'Taylor', 'Davies', 'Evans', 'Thomas', 'Johnson', 'Roberts']
        
        for i in range(6, 501):
            student_id = f'S{i:04d}'
            name = f"{random.choice(first_names)} {random.choice(last_names)}"
            gender = random.choice(['Male', 'Female'])
            age = random.choice([16, 17, 18, 19])
            study_hours = round(random.uniform(2, 10), 1)
            previous_score = random.randint(50, 95)
            attendance = random.randint(60, 100)
            parent_edu = random.choice(["High School", "Bachelor's", "Master's", 'PhD'])
            parent_income = random.randint(40000, 150000)
            internet = random.choice(['Yes', 'No'])
            sleep_hours = random.randint(5, 9)
            extracurricular = random.choice(['Yes', 'No'])
            tuition = random.choice(['Yes', 'No'])
            library = random.choice(['Yes', 'No'])
            transport = random.choice(['Yes', 'No'])
            
            midterm = random.randint(50, 95)
            assignment = random.randint(50, 95)
            quiz = random.randint(50, 95)
            project = random.randint(50, 95)
            
            final_score = midterm*0.25 + assignment*0.20 + quiz*0.15 + project*0.40
            if study_hours >= 7:
                final_score += 5
            if attendance >= 90:
                final_score += 3
            final_score = round(min(100, final_score), 1)
            
            if final_score >= 90:
                grade = 'A+'
            elif final_score >= 80:
                grade = 'A'
            elif final_score >= 70:
                grade = 'B'
            elif final_score >= 60:
                grade = 'C'
            elif final_score >= 50:
                grade = 'D'
            else:
                grade = 'F'
            
            cursor.execute('''INSERT INTO students VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                          (student_id, name, gender, age, study_hours, previous_score, attendance,
                           parent_edu, parent_income, internet, sleep_hours, extracurricular,
                           tuition, library, transport, midterm, assignment, quiz, project,
                           final_score, grade))
        
        student_users = [
            ('S0001', 'John Collins', 'john@example.com', 'john123', 'parent1@example.com'),
            ('S0002', 'Emma Watson', 'emma@example.com', 'emma123', 'parent2@example.com'),
            ('S0003', 'Michael Brown', 'michael@example.com', 'michael123', 'parent3@example.com'),
            ('S0004', 'Sophia Lee', 'sophia@example.com', 'sophia123', 'parent4@example.com'),
            ('S0005', 'James Wilson', 'james@example.com', 'james123', 'parent5@example.com'),
        ]
        
        for su in student_users:
            cursor.execute('''INSERT OR IGNORE INTO student_users VALUES (?, ?, ?, ?, ?)''', su)
        
        conn.commit()
        print(f"✅ Database initialized with 500 students!")
    
    conn.close()

init_database()

# ============ WEBSOCKET BACKGROUND THREAD ============

def background_updater():
    while True:
        time.sleep(10)
        try:
            conn = sqlite3.connect('database/students.db')
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM students")
            total = cursor.fetchone()[0]
            cursor.execute("SELECT AVG(final_score) FROM students")
            avg_score = cursor.fetchone()[0] or 0
            cursor.execute("SELECT AVG(attendance_percentage) FROM students")
            avg_att = cursor.fetchone()[0] or 0
            cursor.execute("SELECT AVG(study_hours) FROM students")
            avg_study = cursor.fetchone()[0] or 0
            cursor.execute("SELECT name, final_score, grade FROM students ORDER BY final_score DESC LIMIT 5")
            top_performers = [{'name': row[0], 'score': row[1], 'grade': row[2]} for row in cursor.fetchall()]
            cursor.execute("SELECT grade, COUNT(*) FROM students GROUP BY grade")
            grade_dist = [{'grade': row[0], 'count': row[1]} for row in cursor.fetchall()]
            conn.close()
            socketio.emit('dashboard_update', {
                'total_students': total,
                'avg_score': round(avg_score, 1),
                'avg_attendance': round(avg_att, 1),
                'avg_study_hours': round(avg_study, 1),
                'top_performers': top_performers,
                'grade_distribution': grade_dist,
                'timestamp': datetime.now().strftime('%H:%M:%S')
            })
        except Exception as e:
            print(f"WebSocket error: {e}")

threading.Thread(target=background_updater, daemon=True).start()

# ============ SOCKETIO EVENTS ============

@socketio.on('connect')
def handle_connect():
    print(f"✅ Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    print(f"❌ Client disconnected: {request.sid}")

@socketio.on('join_room')
def handle_join_room(data):
    room_id = data.get('room_id')
    room_name = f'room_{room_id}'
    join_room(room_name)
    print(f"📡 User joined room: {room_name}")
    emit('joined_room', {'room_id': room_id}, room=room_name)

@socketio.on('leave_room')
def handle_leave_room(data):
    room_id = data.get('room_id')
    room_name = f'room_{room_id}'
    leave_room(room_name)
    print(f"📡 User left room: {room_name}")

@socketio.on('whiteboard_draw')
def handle_whiteboard_draw(data):
    room_id = data.get('room_id')
    drawing_data = data.get('drawing_data')
    action = data.get('action', 'draw')
    room_name = f'room_{room_id}'
    emit('whiteboard_update', {
        'drawing_data': drawing_data,
        'action': action,
        'room_id': room_id
    }, room=room_name, skip_sid=request.sid)

@socketio.on('whiteboard_clear')
def handle_whiteboard_clear(data):
    room_id = data.get('room_id')
    room_name = f'room_{room_id}'
    emit('whiteboard_clear', {'room_id': room_id}, room=room_name, skip_sid=request.sid)

# ============ CORE ROUTES ============

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username in DEMO_USERS and DEMO_USERS[username]['password'] == password:
            login_user(User(username, DEMO_USERS[username]['role'], DEMO_USERS[username]['name']))
            return redirect(url_for('dashboard'))
        return render_template('login.html', error='Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/student-login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        password = request.form.get('password')
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM student_users WHERE student_id = ? AND password = ?", (student_id, password))
        student = cursor.fetchone()
        conn.close()
        if student:
            login_user(StudentUser(student[0], student[1], student[2]))
            return redirect(url_for('student_dashboard'))
        return render_template('student_login.html', error='Invalid Student ID or Password')
    return render_template('student_login.html')

@app.route('/parent-login', methods=['GET', 'POST'])
def parent_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        print(f"Parent login attempt: Email={email}, Password={password}")
        
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        
        # Check in student_users table using parent_email and parent_password
        cursor.execute("""
            SELECT student_id, name, parent_email, parent_password 
            FROM student_users 
            WHERE parent_email = ? AND parent_password = ?
        """, (email, password))
        
        parent_data = cursor.fetchone()
        conn.close()
        
        if parent_data:
            print(f"✅ Parent login successful: {parent_data[1]}")
            # Create parent user object
            parent_user = ParentUser(email, f"Parent of {parent_data[1]}", parent_data[0])
            login_user(parent_user)
            return redirect(url_for('parent_dashboard'))
        else:
            print(f"❌ Parent login failed for email: {email}")
            return render_template('parent_login.html', error='Invalid Email or Password')
    
    return render_template('parent_login.html')

@app.route('/student-dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        return redirect(url_for('dashboard'))
    return render_template('student_dashboard.html', student_id=current_user.student_id)

@app.route('/parent-dashboard')
@login_required
def parent_dashboard():
    if current_user.role != 'parent':
        return redirect(url_for('dashboard'))
    return render_template('parent_dashboard.html', student_id=current_user.student_id)

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/predictions')
@login_required
def predictions():
    return render_template('predictions.html')

@app.route('/reports')
@login_required
def reports():
    return render_template('reports.html')

@app.route('/add-student')
@login_required
def add_student_page():
    return render_template('add_student.html')

@app.route('/students')
@login_required
def students():
    return render_template('students.html')

@app.route('/student-profile/<student_id>')
@login_required
def student_profile(student_id):
    return render_template('student_profile.html')

@app.route('/trends')
@login_required
def trends():
    return render_template('trends.html')

@app.route('/chatbot')
@login_required
def chatbot():
    return render_template('chatbot.html')

@app.route('/gamification')
@login_required
def gamification():
    return render_template('gamification.html')

@app.route('/learning-path')
@login_required
def learning_path():
    if current_user.role != 'student':
        return redirect(url_for('dashboard'))
    return render_template('learning_path.html')

@app.route('/study-room')
@login_required
def study_room():
    return render_template('study_room.html')

@app.route('/goals')
@login_required
def goals():
    return render_template('goals.html')

@app.route('/quizzes')
@login_required
def quizzes():
    return render_template('quizzes.html')

@app.route('/create-quiz')
@login_required
def create_quiz():
    return render_template('create_quiz.html')

@app.route('/take-quiz/<int:quiz_id>')
@login_required
def take_quiz(quiz_id):
    return render_template('take_quiz.html', quiz_id=quiz_id)

@app.route('/meetings')
@login_required
def meetings():
    return render_template('meetings.html')

@app.route('/certificates')
@login_required
def certificates():
    return render_template('certificates.html')




@app.route('/study-buddy')
@login_required
def study_buddy():
    return render_template('study_buddy.html')

@app.route('/ai-question-generator')
@login_required
def ai_question_generator():
    return render_template('ai_question_generator.html')

@app.route('/doubts')
@login_required
def doubts():
    return render_template('doubts.html')

@app.route('/exam/<int:quiz_id>')
@login_required
def take_proctored_exam(quiz_id):
    return render_template('proctored_exam.html', quiz_id=quiz_id)

# ============ API ENDPOINTS ============

@app.route('/api/statistics')
@login_required
def api_statistics():
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM students")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT AVG(final_score) FROM students")
    avg_score = cursor.fetchone()[0] or 0
    cursor.execute("SELECT AVG(attendance_percentage) FROM students")
    avg_att = cursor.fetchone()[0] or 0
    cursor.execute("SELECT AVG(study_hours) FROM students")
    avg_study = cursor.fetchone()[0] or 0
    cursor.execute("SELECT grade, COUNT(*) FROM students GROUP BY grade ORDER BY grade")
    grade_dist = [{'grade': row[0], 'count': row[1]} for row in cursor.fetchall()]
    cursor.execute("SELECT gender, COUNT(*) FROM students GROUP BY gender")
    gender_dist = [{'gender': row[0], 'count': row[1]} for row in cursor.fetchall()]
    conn.close()
    return jsonify({
        'total_students': total,
        'avg_final_score': round(avg_score, 1),
        'avg_attendance': round(avg_att, 1),
        'avg_study_hours': round(avg_study, 1),
        'grade_distribution': grade_dist,
        'gender_distribution': gender_dist
    })

@app.route('/api/insights')
@login_required
def api_insights():
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    cursor.execute("SELECT AVG(final_score) FROM students WHERE study_hours >= 7")
    high_study = cursor.fetchone()[0] or 0
    cursor.execute("SELECT AVG(final_score) FROM students WHERE study_hours < 4")
    low_study = cursor.fetchone()[0] or 0
    cursor.execute("SELECT AVG(final_score) FROM students WHERE attendance_percentage >= 90")
    high_att = cursor.fetchone()[0] or 0
    cursor.execute("SELECT AVG(final_score) FROM students WHERE attendance_percentage < 75")
    low_att = cursor.fetchone()[0] or 0
    cursor.execute("SELECT AVG(final_score) FROM students")
    avg_score = cursor.fetchone()[0] or 0
    conn.close()
    insights = [
        f"📊 Overall student performance shows average score of {avg_score:.1f}%",
        f"💡 Students who study 7+ hours score {high_study - low_study:.1f} points higher on average",
        f"🎯 Attendance above 90% leads to {high_att - low_att:.1f} points higher performance",
        "👥 Gender distribution shows balanced performance across both genders",
        "🏆 Top performers demonstrate excellent academic achievement"
    ]
    return jsonify({'insights': insights})

@app.route('/api/top-performers')
@login_required
def api_top_performers():
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    limit = request.args.get('limit', 10, type=int)
    cursor.execute(f"SELECT name, final_score, grade, attendance_percentage FROM students ORDER BY final_score DESC LIMIT {limit}")
    result = [{'name': row[0], 'final_score': row[1], 'grade': row[2], 'attendance_percentage': row[3]} for row in cursor.fetchall()]
    conn.close()
    return jsonify(result)

@app.route('/api/study-hours-analysis')
@login_required
def api_study_hours():
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    brackets = [('Very Low (0-3)', 0, 3), ('Low (3-5)', 3, 5), ('Medium (5-7)', 5, 7), ('High (7-9)', 7, 9), ('Very High (9+)', 9, 100)]
    result = {}
    for label, low, high in brackets:
        cursor.execute(f"SELECT AVG(final_score) FROM students WHERE study_hours >= {low} AND study_hours < {high}")
        avg = cursor.fetchone()[0] or 0
        result[label] = {'final_score': {'mean': round(avg, 1)}}
    conn.close()
    return jsonify(result)

@app.route('/api/attendance-analysis')
@login_required
def api_attendance():
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    brackets = [('Poor (<60%)', 0, 60), ('Below Avg (60-75%)', 60, 75), ('Average (75-85%)', 75, 85), ('Good (85-95%)', 85, 95), ('Excellent (95%+)', 95, 101)]
    result = {}
    for label, low, high in brackets:
        cursor.execute(f"SELECT AVG(final_score) FROM students WHERE attendance_percentage >= {low} AND attendance_percentage < {high}")
        avg = cursor.fetchone()[0] or 0
        result[label] = {'final_score': {'mean': round(avg, 1)}}
    conn.close()
    return jsonify(result)

@app.route('/api/all-students')
@login_required
def api_all_students():
    conn = sqlite3.connect('database/students.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students ORDER BY final_score DESC")
    students = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(students)

@app.route('/api/student/<student_id>')
@login_required
def api_get_student(student_id):
    conn = sqlite3.connect('database/students.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students WHERE student_id = ?", (student_id,))
    student = dict(cursor.fetchone())
    conn.close()
    return jsonify(student)

@app.route('/api/student-data/<student_id>')
@login_required
def api_student_data(student_id):
    conn = sqlite3.connect('database/students.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students WHERE student_id = ?", (student_id,))
    student = dict(cursor.fetchone())
    cursor.execute("SELECT AVG(final_score) as class_avg FROM students")
    class_avg = cursor.fetchone()['class_avg'] or 0
    cursor.execute("SELECT COUNT(*) + 1 as rank FROM students WHERE final_score > (SELECT final_score FROM students WHERE student_id = ?)", (student_id,))
    rank = cursor.fetchone()['rank'] or 0
    conn.close()
    return jsonify({'student': student, 'class_average': round(class_avg, 1), 'rank': rank, 'total_students': 500})

@app.route('/api/improvement-suggestions/<student_id>')
@login_required
def api_improvement_suggestions(student_id):
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    cursor.execute("SELECT study_hours, attendance_percentage, final_score, grade FROM students WHERE student_id = ?", (student_id,))
    student = cursor.fetchone()
    conn.close()
    suggestions = []
    if student[0] < 5:
        suggestions.append(f"📚 Increase study hours from {student[0]} to 7 hours/day - could improve score by 10+ points")
    if student[1] < 85:
        suggestions.append(f"🎯 Improve attendance from {student[1]}% to 90% - could improve score by 5+ points")
    if student[2] < 70:
        suggestions.append("💪 Focus on weak subjects - consider extra tutoring")
    elif student[2] < 85:
        suggestions.append("⭐ You're doing well! Consistent effort will get you to A grade")
    else:
        suggestions.append("🏆 Excellent performance! Consider helping other students")
    return jsonify({'suggestions': suggestions})

@app.route('/api/predict', methods=['POST'])
@login_required
def api_predict():
    try:
        data = request.get_json()
        midterm = float(data.get('midterm_score', 75))
        assignment = float(data.get('assignment_score', 75))
        quiz = float(data.get('quiz_score', 75))
        project = float(data.get('project_score', 75))
        score = (midterm * 0.25) + (assignment * 0.20) + (quiz * 0.15) + (project * 0.40)
        study_hours = float(data.get('study_hours', 5))
        attendance = float(data.get('attendance_percentage', 80))
        if study_hours >= 7:
            score += 5
        if attendance >= 90:
            score += 3
        score = max(40, min(100, round(score, 1)))
        if score >= 90:
            grade = 'A+'
        elif score >= 80:
            grade = 'A'
        elif score >= 70:
            grade = 'B'
        elif score >= 60:
            grade = 'C'
        elif score >= 50:
            grade = 'D'
        else:
            grade = 'F'
        return jsonify({'success': True, 'prediction': {'predicted_score': score, 'predicted_grade': grade, 'confidence': 'High'}})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        if not user_message:
            return jsonify({'success': False, 'error': 'No message provided'})
        
        context = ""
        if current_user.role == 'student':
            try:
                conn = sqlite3.connect('database/students.db')
                cursor = conn.cursor()
                cursor.execute("SELECT name, final_score, grade, study_hours, attendance_percentage FROM students WHERE student_id = ?", (current_user.student_id,))
                student = cursor.fetchone()
                conn.close()
                if student:
                    context = f"The student has {student[1]}% score with grade {student[2]}, studying {student[3]} hours/day, attendance {student[4]}%. "
            except:
                pass
        
        completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": f"You are a helpful, encouraging academic assistant for students. {context}Give practical, specific advice. Keep responses concise (2-3 sentences max). Use emojis occasionally."},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=300
        )
        bot_reply = completion.choices[0].message.content
        return jsonify({'success': True, 'reply': bot_reply})
    except Exception as e:
        return jsonify({'success': True, 'reply': "I'm here to help! Ask me about grades, study tips, attendance, exam prep, or motivation!"})

@app.route('/api/add-student', methods=['POST'])
@login_required
def api_add_student():
    try:
        data = request.get_json()
        
        # Calculate final score and grade (existing code)
        midterm = float(data.get('midterm_score', 0))
        assignment = float(data.get('assignment_score', 0))
        quiz = float(data.get('quiz_score', 0))
        project = float(data.get('project_score', 0))
        
        final_score = midterm*0.25 + assignment*0.20 + quiz*0.15 + project*0.40
        if float(data.get('study_hours', 0)) >= 7:
            final_score += 5
        if float(data.get('attendance_percentage', 0)) >= 90:
            final_score += 3
        final_score = round(min(100, final_score), 1)
        
        if final_score >= 90:
            grade = 'A+'
        elif final_score >= 80:
            grade = 'A'
        elif final_score >= 70:
            grade = 'B'
        elif final_score >= 60:
            grade = 'C'
        elif final_score >= 50:
            grade = 'D'
        else:
            grade = 'F'
        
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        
        # Get next student ID
        cursor.execute("SELECT MAX(CAST(SUBSTR(student_id, 2) AS INTEGER)) FROM students")
        max_id = cursor.fetchone()[0] or 500
        new_id_num = max_id + 1
        student_id = f'S{new_id_num:04d}'
        
        # Insert into students table
        cursor.execute('''INSERT INTO students VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (
            student_id, data['name'], data['gender'], int(data['age']), float(data['study_hours']),
            int(data['previous_score']), int(data['attendance_percentage']), data['parent_education_level'],
            int(data['parent_income']), data['internet_access_at_home'], int(data['sleep_hours']),
            data['extracurricular_activities'], data['tuition_classes'], data['library_access'],
            data['transport_facility'], int(midterm), int(assignment), int(quiz), int(project),
            final_score, grade))
        
        # Generate login credentials
        import random
        import string
        
        # Student credentials
        student_password = f"{student_id.lower()}123"  # e.g., s0501123
        student_email = f"{data['name'].lower().replace(' ', '.')}@student.com"
        
        # Parent credentials
        parent_email = data.get('parent_email') or f"parent.{student_id.lower()}@example.com"
        parent_password = f"parent{new_id_num}123"  # e.g., parent501123
        
        # Insert into student_users table
        cursor.execute('''
            INSERT OR REPLACE INTO student_users 
            (student_id, name, email, password, parent_email, parent_password, is_active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        ''', (student_id, data['name'], student_email, student_password, parent_email, parent_password))
        
        conn.commit()
        
        # Calculate points for gamification
        calculate_points(student_id)
        
        conn.close()
        
        # Send notification to admin about new student
        send_unified_notification(
            'admin',
            'new_student',
            '🎓 New Student Registered',
            f'{data["name"]} has been added with ID: {student_id}',
            'fa-user-graduate',
            '/students'
        )
        
        return jsonify({
            'success': True, 
            'student_id': student_id,
            'student_password': student_password,
            'student_email': student_email,
            'parent_email': parent_email,
            'parent_password': parent_password,
            'grade': grade,
            'final_score': final_score
        })
        
    except Exception as e:
        print(f"Error adding student: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/student/<student_id>', methods=['PUT'])
@login_required
def api_update_student(student_id):
    try:
        data = request.get_json()
        midterm = data.get('midterm_score', 0)
        assignment = data.get('assignment_score', 0)
        quiz = data.get('quiz_score', 0)
        project = data.get('project_score', 0)
        final_score = midterm*0.25 + assignment*0.20 + quiz*0.15 + project*0.40
        if data.get('study_hours', 0) >= 7:
            final_score += 5
        if data.get('attendance_percentage', 0) >= 90:
            final_score += 3
        final_score = round(min(100, final_score), 1)
        if final_score >= 90:
            grade = 'A+'
        elif final_score >= 80:
            grade = 'A'
        elif final_score >= 70:
            grade = 'B'
        elif final_score >= 60:
            grade = 'C'
        elif final_score >= 50:
            grade = 'D'
        else:
            grade = 'F'
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE students SET 
                name=?, gender=?, age=?, study_hours=?, attendance_percentage=?,
                previous_score=?, midterm_score=?, assignment_score=?, quiz_score=?,
                project_score=?, final_score=?, grade=?
            WHERE student_id=?
        ''', (data['name'], data['gender'], data['age'], data['study_hours'],
              data['attendance_percentage'], data['previous_score'], midterm,
              assignment, quiz, project, final_score, grade, student_id))
        conn.commit()
        calculate_points(student_id)
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/student/<student_id>', methods=['DELETE'])
@login_required
def api_delete_student(student_id):
    try:
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
        cursor.execute("DELETE FROM student_points WHERE student_id = ?", (student_id,))
        cursor.execute("DELETE FROM student_badges WHERE student_id = ?", (student_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/compare-students')
@login_required
def api_compare_students():
    ids = request.args.get('ids', '').split(',')
    conn = sqlite3.connect('database/students.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    placeholders = ','.join(['?'] * len(ids))
    cursor.execute(f"SELECT * FROM students WHERE student_id IN ({placeholders})", ids)
    students = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(students)

@app.route('/api/performance-trends')
@login_required
def api_performance_trends():
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    avg_scores = []
    attendance_trend = []
    a_percentage = []
    b_percentage = []
    c_percentage = []
    high_study_scores = []
    low_study_scores = []
    high_attendance_scores = []
    low_attendance_scores = []
    for i in range(12):
        improvement = i * 0.5
        avg_scores.append(round(65 + improvement + (i % 3) * 2, 1))
        attendance_trend.append(round(80 + improvement/2 + (i % 4), 1))
        a_percentage.append(round(15 + improvement/2, 1))
        b_percentage.append(round(30 + improvement/3, 1))
        c_percentage.append(round(30 - improvement/4, 1))
        high_study_scores.append(round(75 + improvement, 1))
        low_study_scores.append(round(55 + improvement/2, 1))
        high_attendance_scores.append(round(78 + improvement, 1))
        low_attendance_scores.append(round(52 + improvement/2, 1))
    return jsonify({
        'months': months,
        'avg_scores': avg_scores,
        'attendance_trend': attendance_trend,
        'a_percentage': a_percentage,
        'b_percentage': b_percentage,
        'c_percentage': c_percentage,
        'high_study_scores': high_study_scores,
        'low_study_scores': low_study_scores,
        'high_attendance_scores': high_attendance_scores,
        'low_attendance_scores': low_attendance_scores
    })

@app.route('/api/export-excel')
@login_required
def api_export_excel():
    conn = sqlite3.connect('database/students.db')
    df = pd.read_sql_query("SELECT * FROM students", conn)
    conn.close()
    filename = f'students_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    filepath = os.path.join('data/exports', filename)
    os.makedirs('data/exports', exist_ok=True)
    df.to_excel(filepath, index=False)
    return send_file(filepath, as_attachment=True, download_name=filename)

@app.route('/api/export-csv')
@login_required
def api_export_csv():
    conn = sqlite3.connect('database/students.db')
    df = pd.read_sql_query("SELECT * FROM students", conn)
    conn.close()
    filename = f'students_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    filepath = os.path.join('data/exports', filename)
    os.makedirs('data/exports', exist_ok=True)
    df.to_csv(filepath, index=False)
    return send_file(filepath, as_attachment=True, download_name=filename)

@app.route('/api/export-pdf')
@login_required
def api_export_pdf():
    try:
        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        cursor.execute("SELECT student_id, name, gender, final_score, grade, attendance_percentage FROM students ORDER BY final_score DESC LIMIT 50")
        students = cursor.fetchall()
        conn.close()
        filename = f'report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        filepath = os.path.join('data/exports', filename)
        os.makedirs('data/exports', exist_ok=True)
        doc = SimpleDocTemplate(filepath, pagesize=landscape(letter))
        styles = getSampleStyleSheet()
        elements = []
        elements.append(Paragraph("Student Performance Report", styles['Title']))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        elements.append(Spacer(1, 12))
        data = [['ID', 'Name', 'Gender', 'Final Score', 'Grade', 'Attendance']]
        for s in students:
            data.append([s[0], s[1], s[2], f"{s[3]}%", s[4], f"{s[5]}%"])
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 12),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('BACKGROUND', (0,1), (-1,-1), colors.beige),
            ('GRID', (0,0), (-1,-1), 1, colors.black)
        ]))
        elements.append(table)
        doc.build(elements)
        return send_file(filepath, as_attachment=True, download_name=filename)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============ GAMIFICATION SYSTEM ============

def calculate_points(student_id):
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    cursor.execute("SELECT final_score, grade, study_hours, attendance_percentage, project_score FROM students WHERE student_id = ?", (student_id,))
    student = cursor.fetchone()
    points = 0
    earned_badges = []
    if student[1] == 'A+':
        points += 100
        earned_badges.append(2)
    elif student[1] == 'A':
        points += 80
    elif student[1] == 'B':
        points += 50
    elif student[1] == 'C':
        points += 30
    else:
        points += 10
    if student[3] >= 95:
        points += 50
        earned_badges.append(1)
    elif student[3] >= 90:
        points += 30
    elif student[3] >= 85:
        points += 20
    else:
        points += 5
    if student[2] >= 8:
        points += 40
    elif student[2] >= 7:
        points += 30
    elif student[2] >= 5:
        points += 20
    else:
        points += 5
    if student[4] >= 95:
        points += 50
        earned_badges.append(7)
    elif student[4] >= 85:
        points += 30
    cursor.execute("SELECT * FROM student_points WHERE student_id = ?", (student_id,))
    existing = cursor.fetchone()
    if existing:
        cursor.execute("UPDATE student_points SET total_points = total_points + ?, xp = xp + ? WHERE student_id = ?", (points, points, student_id))
    else:
        cursor.execute("INSERT INTO student_points VALUES (?, ?, ?, ?)", (student_id, points, 1, points))
    cursor.execute("SELECT total_points FROM student_points WHERE student_id = ?", (student_id,))
    total = cursor.fetchone()[0]
    new_level = min(10, max(1, total // 500 + 1))
    cursor.execute("UPDATE student_points SET level = ? WHERE student_id = ?", (new_level, student_id))
    for badge_id in earned_badges:
        cursor.execute("INSERT OR IGNORE INTO student_badges (student_id, badge_id, earned_date) VALUES (?, ?, datetime('now'))", (student_id, badge_id))
    conn.commit()
    conn.close()
    return points, new_level

@app.route('/api/leaderboard')
@login_required
def api_leaderboard():
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT s.name, sp.total_points, sp.level, s.grade, s.final_score
        FROM student_points sp
        JOIN students s ON sp.student_id = s.student_id
        ORDER BY sp.total_points DESC
        LIMIT 20
    ''')
    leaderboard = [{'name': row[0], 'points': row[1], 'level': row[2], 'grade': row[3], 'score': row[4]} for row in cursor.fetchall()]
    conn.close()
    return jsonify(leaderboard)

@app.route('/api/my-badges')
@login_required
def api_my_badges():
    if current_user.role != 'student':
        return jsonify([])
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT b.badge_id, b.badge_name, b.badge_icon, b.description, sb.earned_date
        FROM student_badges sb
        JOIN badges b ON sb.badge_id = b.badge_id
        WHERE sb.student_id = ?
    ''', (current_user.student_id,))
    badges = [{'id': row[0], 'name': row[1], 'icon': row[2], 'description': row[3], 'earned_date': row[4]} for row in cursor.fetchall()]
    conn.close()
    return jsonify(badges)

@app.route('/api/my-points')
@login_required
def api_my_points():
    if current_user.role != 'student':
        return jsonify({'points': 0, 'level': 1, 'next_level_points': 500})
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    cursor.execute("SELECT total_points, level, xp FROM student_points WHERE student_id = ?", (current_user.student_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return jsonify({'points': result[0], 'level': result[1], 'next_level_points': result[1] * 500})
    return jsonify({'points': 0, 'level': 1, 'next_level_points': 500})

# ============ STUDY ROOM API ============

@app.route('/api/study-rooms')
@login_required
def api_get_study_rooms():
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT DISTINCT r.room_id, r.room_name, r.room_code, r.subject, r.created_by, 
               r.created_at, COUNT(DISTINCT rm.student_id) as member_count,
               (SELECT COUNT(*) FROM room_messages WHERE room_id = r.room_id) as message_count
        FROM study_rooms r
        LEFT JOIN room_members rm ON r.room_id = rm.room_id
        WHERE r.created_by = ? OR rm.student_id = ?
        GROUP BY r.room_id
        ORDER BY r.created_at DESC
    ''', (current_user.id, current_user.id))
    rooms = []
    for row in cursor.fetchall():
        rooms.append({
            'room_id': row[0],
            'room_name': row[1],
            'room_code': row[2],
            'subject': row[3],
            'created_by': row[4],
            'created_at': row[5],
            'member_count': row[6],
            'message_count': row[7]
        })
    conn.close()
    return jsonify(rooms)

@app.route('/api/create-study-room', methods=['POST'])
@login_required
def api_create_study_room():
    try:
        data = request.get_json()
        room_name = data.get('room_name')
        subject = data.get('subject')
        room_code = generate_room_code()
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO study_rooms (room_name, room_code, created_by, subject)
            VALUES (?, ?, ?, ?)
        ''', (room_name, room_code, current_user.id, subject))
        room_id = cursor.lastrowid
        cursor.execute('''
            INSERT INTO room_members (room_id, student_id, last_active)
            VALUES (?, ?, datetime('now'))
        ''', (room_id, current_user.id))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'room_id': room_id, 'room_code': room_code})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/join-study-room', methods=['POST'])
@login_required
def api_join_study_room():
    try:
        data = request.get_json()
        room_code = data.get('room_code').upper()
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        cursor.execute("SELECT room_id, room_name FROM study_rooms WHERE room_code = ? AND is_active = 1", (room_code,))
        room = cursor.fetchone()
        if not room:
            return jsonify({'success': False, 'error': 'Invalid room code'})
        cursor.execute("SELECT * FROM room_members WHERE room_id = ? AND student_id = ?", (room[0], current_user.id))
        existing = cursor.fetchone()
        if not existing:
            cursor.execute('''
                INSERT INTO room_members (room_id, student_id, last_active)
                VALUES (?, ?, datetime('now'))
            ''', (room[0], current_user.id))
            conn.commit()
        conn.close()
        return jsonify({'success': True, 'room_id': room[0], 'room_name': room[1]})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/room-messages/<int:room_id>')
@login_required
def api_room_messages(room_id):
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT m.message_id, m.student_id, s.name, m.message, m.sent_at
        FROM room_messages m
        JOIN students s ON m.student_id = s.student_id
        WHERE m.room_id = ?
        ORDER BY m.sent_at ASC
        LIMIT 100
    ''', (room_id,))
    messages = []
    for row in cursor.fetchall():
        messages.append({
            'message_id': row[0],
            'student_id': row[1],
            'student_name': row[2],
            'message': row[3],
            'sent_at': row[4]
        })
    conn.close()
    return jsonify(messages)

@app.route('/api/send-message', methods=['POST'])
@login_required
def api_send_message():
    try:
        data = request.get_json()
        room_id = data.get('room_id')
        message = data.get('message')
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO room_messages (room_id, student_id, message, sent_at)
            VALUES (?, ?, ?, datetime('now'))
        ''', (room_id, current_user.id, message))
        cursor.execute('''
            UPDATE room_members SET last_active = datetime('now')
            WHERE room_id = ? AND student_id = ?
        ''', (room_id, current_user.id))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/room-members/<int:room_id>')
@login_required
def api_room_members(room_id):
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT s.student_id, s.name, s.grade, rm.last_active
        FROM room_members rm
        JOIN students s ON rm.student_id = s.student_id
        WHERE rm.room_id = ?
        ORDER BY rm.last_active DESC
    ''', (room_id,))
    members = []
    for row in cursor.fetchall():
        members.append({
            'student_id': row[0],
            'name': row[1],
            'grade': row[2],
            'last_active': row[3]
        })
    conn.close()
    return jsonify(members)

@app.route('/api/room-files/<int:room_id>')
@login_required
def api_room_files(room_id):
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT f.file_id, f.file_name, f.file_url, f.file_size, f.file_type, 
               f.uploaded_at, s.name as uploaded_by
        FROM room_files f
        JOIN students s ON f.uploaded_by = s.student_id
        WHERE f.room_id = ?
        ORDER BY f.uploaded_at DESC
    ''', (room_id,))
    files = []
    for row in cursor.fetchall():
        files.append({
            'file_id': row[0],
            'file_name': row[1],
            'file_url': row[2],
            'file_size': row[3],
            'file_type': row[4],
            'uploaded_at': row[5],
            'uploaded_by': row[6]
        })
    conn.close()
    return jsonify(files)

@app.route('/api/upload-file', methods=['POST'])
@login_required
def api_upload_file():
    try:
        room_id = request.form.get('room_id')
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'})
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'})
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'File type not allowed'})
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        if file_size > 10 * 1024 * 1024:
            return jsonify({'success': False, 'error': 'File too large. Max size: 10MB'})
        filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
        filepath = os.path.join('static/uploads', filename)
        file.save(filepath)
        file_type = file.filename.rsplit('.', 1)[1].lower()
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO room_files (room_id, uploaded_by, file_name, file_url, file_size, file_type)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (room_id, current_user.id, file.filename, filename, file_size, file_type))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'filename': file.filename, 'file_url': filename})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/download-file/<filename>')
@login_required
def api_download_file(filename):
    try:
        filepath = os.path.join('static/uploads', filename)
        return send_file(filepath, as_attachment=True, download_name=filename)
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@app.route('/api/delete-file/<int:file_id>', methods=['DELETE'])
@login_required
def api_delete_file(file_id):
    try:
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        cursor.execute("SELECT file_url, uploaded_by FROM room_files WHERE file_id = ?", (file_id,))
        file = cursor.fetchone()
        if not file:
            return jsonify({'success': False, 'error': 'File not found'})
        if file[1] != current_user.id and current_user.role != 'admin':
            return jsonify({'success': False, 'error': 'Permission denied'})
        filepath = os.path.join('static/uploads', file[0])
        if os.path.exists(filepath):
            os.remove(filepath)
        cursor.execute("DELETE FROM room_files WHERE file_id = ?", (file_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/whiteboard/<int:room_id>', methods=['GET'])
@login_required
def api_get_whiteboard(room_id):
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    cursor.execute("SELECT drawing_data FROM whiteboard_data WHERE room_id = ? ORDER BY updated_at DESC LIMIT 1", (room_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return jsonify({'success': True, 'drawing_data': result[0]})
    return jsonify({'success': True, 'drawing_data': ''})

@app.route('/api/whiteboard/<int:room_id>', methods=['POST'])
@login_required
def api_save_whiteboard(room_id):
    try:
        data = request.get_json()
        drawing_data = data.get('drawing_data', '')
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM whiteboard_data WHERE room_id = ?", (room_id,))
        existing = cursor.fetchone()
        if existing:
            cursor.execute("UPDATE whiteboard_data SET drawing_data = ?, updated_at = datetime('now') WHERE room_id = ?", (drawing_data, room_id))
        else:
            cursor.execute("INSERT INTO whiteboard_data (room_id, drawing_data) VALUES (?, ?)", (room_id, drawing_data))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============ GOALS API ============

@app.route('/api/my-goals')
@login_required
def api_my_goals():
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT g.goal_id, g.goal_title, g.target_score, g.current_score, 
               g.target_date, g.status, g.created_at, g.completed_at,
               (SELECT COUNT(*) FROM goal_checkpoints WHERE goal_id = g.goal_id AND is_completed = 1) as completed_checkpoints,
               (SELECT COUNT(*) FROM goal_checkpoints WHERE goal_id = g.goal_id) as total_checkpoints
        FROM student_goals g
        WHERE g.student_id = ?
        ORDER BY 
            CASE g.status 
                WHEN 'active' THEN 1 
                WHEN 'completed' THEN 2 
                ELSE 3 
            END,
            g.target_date ASC
    ''', (current_user.id,))
    goals = []
    for row in cursor.fetchall():
        goals.append({
            'goal_id': row[0],
            'goal_title': row[1],
            'target_score': row[2],
            'current_score': row[3],
            'target_date': row[4],
            'status': row[5],
            'created_at': row[6],
            'completed_at': row[7],
            'completed_checkpoints': row[8],
            'total_checkpoints': row[9]
        })
    conn.close()
    return jsonify(goals)

@app.route('/api/create-goal', methods=['POST'])
@login_required
def api_create_goal():
    try:
        data = request.get_json()
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        cursor.execute("SELECT final_score FROM students WHERE student_id = ?", (current_user.id,))
        current_score = cursor.fetchone()[0]
        cursor.execute('''
            INSERT INTO student_goals (student_id, goal_title, target_score, current_score, target_date)
            VALUES (?, ?, ?, ?, ?)
        ''', (current_user.id, data['goal_title'], data['target_score'], current_score, data['target_date']))
        goal_id = cursor.lastrowid
        for checkpoint in data.get('checkpoints', []):
            cursor.execute('''
                INSERT INTO goal_checkpoints (goal_id, checkpoint_title)
                VALUES (?, ?)
            ''', (goal_id, checkpoint))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'goal_id': goal_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/update-goal-progress', methods=['POST'])
@login_required
def api_update_goal_progress():
    try:
        data = request.get_json()
        goal_id = data.get('goal_id')
        checkpoint_id = data.get('checkpoint_id')
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE goal_checkpoints 
            SET is_completed = 1, completed_at = datetime('now')
            WHERE checkpoint_id = ?
        ''', (checkpoint_id,))
        cursor.execute('''
            SELECT COUNT(*) FROM goal_checkpoints 
            WHERE goal_id = ? AND is_completed = 0
        ''', (goal_id,))
        remaining = cursor.fetchone()[0]
        if remaining == 0:
            cursor.execute('''
                UPDATE student_goals 
                SET status = 'completed', completed_at = datetime('now')
                WHERE goal_id = ?
            ''', (goal_id,))
            cursor.execute("SELECT total_points FROM student_points WHERE student_id = ?", (current_user.id,))
            current_points = cursor.fetchone()
            if current_points:
                cursor.execute("UPDATE student_points SET total_points = ? WHERE student_id = ?", (current_points[0] + 100, current_user.id))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'completed': remaining == 0})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/goal-details/<int:goal_id>')
@login_required
def api_goal_details(goal_id):
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT goal_title, target_score, current_score, target_date, status
        FROM student_goals WHERE goal_id = ?
    ''', (goal_id,))
    goal = cursor.fetchone()
    cursor.execute('''
        SELECT checkpoint_id, checkpoint_title, is_completed, completed_at
        FROM goal_checkpoints WHERE goal_id = ?
        ORDER BY checkpoint_id
    ''', (goal_id,))
    checkpoints = []
    for row in cursor.fetchall():
        checkpoints.append({
            'checkpoint_id': row[0],
            'title': row[1],
            'is_completed': row[2],
            'completed_at': row[3]
        })
    conn.close()
    return jsonify({
        'goal_title': goal[0],
        'target_score': goal[1],
        'current_score': goal[2],
        'target_date': goal[3],
        'status': goal[4],
        'checkpoints': checkpoints
    })

# ============ QUIZ API ============

@app.route('/api/quizzes')
@login_required
def api_get_quizzes():
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT q.quiz_id, q.title, q.description, q.created_at, 
               COUNT(qu.question_id) as question_count,
               (SELECT COUNT(*) FROM quiz_results WHERE quiz_id = q.quiz_id) as attempts
        FROM quizzes q
        LEFT JOIN questions qu ON q.quiz_id = qu.quiz_id
        GROUP BY q.quiz_id
        ORDER BY q.created_at DESC
    ''')
    quizzes = []
    for row in cursor.fetchall():
        quizzes.append({
            'quiz_id': row[0],
            'title': row[1],
            'description': row[2],
            'created_at': row[3],
            'question_count': row[4],
            'attempts': row[5]
        })
    conn.close()
    return jsonify(quizzes)

@app.route('/api/quiz/<int:quiz_id>')
@login_required
def api_get_quiz(quiz_id):
    try:
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT title, description, time_limit FROM quizzes WHERE quiz_id = ?", (quiz_id,))
        quiz = cursor.fetchone()
        
        if not quiz:
            conn.close()
            return jsonify({'error': 'Quiz not found'}), 404
        
        cursor.execute('''
            SELECT question_id, question_text, option_a, option_b, option_c, option_d, points
            FROM questions WHERE quiz_id = ?
        ''', (quiz_id,))
        
        questions = []
        for row in cursor.fetchall():
            questions.append({
                'question_id': row[0],
                'question_text': row[1],
                'options': [row[2] or '', row[3] or '', row[4] or '', row[5] or ''],
                'points': row[6] or 1
            })
        
        conn.close()
        
        return jsonify({
            'title': quiz[0],
            'description': quiz[1] or '',
            'time_limit': quiz[2] or 30,
            'questions': questions
        })
        
    except Exception as e:
        print(f"Error in get_quiz: {str(e)}")
        return jsonify({'error': str(e)}), 500




@app.route('/api/create-quiz', methods=['POST'])
@login_required
def api_create_quiz():
    try:
        data = request.get_json()
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO quizzes (created_by, title, description, time_limit)
            VALUES (?, ?, ?, ?)
        ''', (current_user.id, data['title'], data['description'], data.get('time_limit', 30)))
        quiz_id = cursor.lastrowid
        for q in data['questions']:
            cursor.execute('''
                INSERT INTO questions (quiz_id, question_text, option_a, option_b, option_c, option_d, correct_answer, points)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (quiz_id, q['text'], q['opt_a'], q['opt_b'], q['opt_c'], q['opt_d'], q['correct'], q.get('points', 1)))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'quiz_id': quiz_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============ MEETINGS API ============
# ============ ENHANCED MEETINGS API ============

# ============ FIXED MEETINGS API ============
@app.route('/api/schedule-meeting', methods=['POST'])
@login_required
def api_schedule_meeting():
    try:
        data = request.get_json()
        print(f"=== SCHEDULING MEETING ===")
        print(f"Received data: {data}")
        
        # Validate required fields
        required_fields = ['student_id', 'parent_email', 'date', 'time']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'Missing required field: {field}'})
        
        # Generate meeting link based on type
        meeting_type = data.get('meeting_type', 'video')
        meeting_link = None
        if meeting_type == 'video':
            meeting_link = f"https://meet.google.com/new?meet_{int(datetime.now().timestamp())}"
        elif meeting_type == 'audio':
            meeting_link = f"https://meet.jit.si/NexusLearn_{int(datetime.now().timestamp())}"
        
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        
        # Get teacher_id from current user
        teacher_id = current_user.id
        
        cursor.execute('''
            INSERT INTO meetings (teacher_id, parent_email, student_id, meeting_date, meeting_time, meeting_link, notes, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'scheduled')
        ''', (
            teacher_id, 
            data['parent_email'], 
            data['student_id'], 
            data['date'], 
            data['time'], 
            meeting_link, 
            data.get('notes', '')
        ))
        
        meeting_id = cursor.lastrowid
        conn.commit()
        print(f"✅ Meeting inserted with ID: {meeting_id}")
        
        # Verify insertion
        cursor.execute("SELECT * FROM meetings WHERE meeting_id = ?", (meeting_id,))
        new_meeting = cursor.fetchone()
        print(f"Verified meeting: {new_meeting}")
        
        # Get student name for notification
        cursor.execute("SELECT name FROM students WHERE student_id = ?", (data['student_id'],))
        student_result = cursor.fetchone()
        student_name = student_result[0] if student_result else 'Student'
        
        conn.close()
        
        # Send notifications
        try:
            send_unified_notification(
                data['parent_email'],
                'meeting',
                '📅 Parent-Teacher Meeting Scheduled',
                f'A meeting has been scheduled for your child {student_name} on {data["date"]} at {data["time"]}.',
                'fa-calendar',
                '/meetings'
            )
            print(f"✅ Notification sent to parent: {data['parent_email']}")
        except Exception as e:
            print(f"Error sending parent notification: {e}")
        
        try:
            send_unified_notification(
                data['student_id'],
                'meeting',
                '📅 Parent-Teacher Meeting Scheduled',
                f'A meeting has been scheduled for you on {data["date"]} at {data["time"]}.',
                'fa-calendar',
                '/meetings'
            )
            print(f"✅ Notification sent to student: {data['student_id']}")
        except Exception as e:
            print(f"Error sending student notification: {e}")
        
        return jsonify({'success': True, 'meeting_id': meeting_id, 'meeting_link': meeting_link})
        
    except Exception as e:
        print(f"Error scheduling meeting: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/test-parent-notification', methods=['GET'])
@login_required
def test_parent_notification():
    """Test endpoint to send a test notification to parent"""
    try:
        parent_email = current_user.id if current_user.role == 'parent' else 'parent1@example.com'
        
        send_unified_notification(
            parent_email,
            'test',
            '🔔 Test Notification',
            'This is a test notification to verify parent notifications are working!',
            'fa-bell',
            '/meetings'
        )
        
        return jsonify({'success': True, 'message': f'Test notification sent to {parent_email}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/meetings', methods=['GET'])
@login_required
def api_get_meetings():
    try:
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        
        print(f"=== GETTING MEETINGS ===")
        print(f"User role: {current_user.role}, User ID: {current_user.id}")
        
        if current_user.role == 'admin' or current_user.role == 'teacher':
            cursor.execute('''
                SELECT m.meeting_id, s.name as student_name, m.parent_email, 
                       m.meeting_date, m.meeting_time, m.status, m.meeting_link, m.notes,
                       m.created_at
                FROM meetings m
                LEFT JOIN students s ON m.student_id = s.student_id
                ORDER BY m.meeting_date DESC, m.meeting_time DESC
            ''')
        elif current_user.role == 'parent':
            cursor.execute('''
                SELECT m.meeting_id, s.name as student_name, m.parent_email, 
                       m.meeting_date, m.meeting_time, m.status, m.meeting_link, m.notes,
                       m.created_at
                FROM meetings m
                LEFT JOIN students s ON m.student_id = s.student_id
                WHERE m.parent_email = ? OR m.student_id IN (SELECT student_id FROM student_users WHERE parent_email = ?)
                ORDER BY m.meeting_date DESC, m.meeting_time DESC
            ''', (current_user.id, current_user.id))
        else:  # student
            cursor.execute('''
                SELECT m.meeting_id, s.name as student_name, m.parent_email,
                       m.meeting_date, m.meeting_time, m.status, m.meeting_link, m.notes,
                       m.created_at
                FROM meetings m
                LEFT JOIN students s ON m.student_id = s.student_id
                WHERE m.student_id = ?
                ORDER BY m.meeting_date DESC, m.meeting_time DESC
            ''', (current_user.id,))
        
        meetings = []
        for row in cursor.fetchall():
            meeting = {
                'meeting_id': row[0],
                'student_name': row[1] or 'Unknown',
                'parent_email': row[2] if len(row) > 2 else None,
                'date': row[3],
                'time': row[4],
                'status': row[5],
                'link': row[6],
                'notes': row[7] if len(row) > 7 else None,
                'created_at': row[8] if len(row) > 8 else None
            }
            meetings.append(meeting)
        
        conn.close()
        print(f"✅ Found {len(meetings)} meetings")
        return jsonify(meetings)
        
    except Exception as e:
        print(f"Error getting meetings: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([])

@app.route('/api/debug-all-meetings')
@login_required
def debug_all_meetings():
    """Debug endpoint to see all meetings"""
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM meetings")
    meetings = cursor.fetchall()
    
    conn.close()
    
    return jsonify({
        'count': len(meetings),
        'meetings': [list(m) for m in meetings],
        'current_user': {
            'id': current_user.id,
            'role': current_user.role
        }
    })

@app.route('/api/cancel-meeting/<int:meeting_id>', methods=['DELETE'])
@login_required
def api_cancel_meeting(meeting_id):
    try:
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        
        # Get meeting details for notification
        cursor.execute("SELECT parent_email, student_id, meeting_date, meeting_time, student_id FROM meetings WHERE meeting_id = ?", (meeting_id,))
        meeting = cursor.fetchone()
        
        if meeting:
            parent_email, student_id, meeting_date, meeting_time, stud_id = meeting
            
            cursor.execute("UPDATE meetings SET status = 'cancelled' WHERE meeting_id = ?", (meeting_id,))
            conn.commit()
            
            # Send cancellation notification to Parent
            try:
                send_unified_notification(
                    parent_email,
                    'meeting_cancelled',
                    '❌ Meeting Cancelled',
                    f'A meeting scheduled for {meeting_date} at {meeting_time} has been cancelled.',
                    'fa-calendar-times',
                    '/meetings'
                )
            except:
                pass
            
            # Send cancellation notification to Student
            try:
                send_unified_notification(
                    student_id,
                    'meeting_cancelled',
                    '❌ Meeting Cancelled',
                    f'A meeting scheduled for {meeting_date} at {meeting_time} has been cancelled.',
                    'fa-calendar-times',
                    '/meetings'
                )
            except:
                pass
        
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/debug-meetings')
@login_required
def debug_meetings():
    """Debug endpoint to check meetings"""
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM meetings")
    meetings = cursor.fetchall()
    
    conn.close()
    
    return jsonify({
        'count': len(meetings),
        'meetings': [list(m) for m in meetings],
        'current_user': {
            'id': current_user.id,
            'role': current_user.role,
            'name': current_user.name
        }
    })

@app.route('/api/delete-meeting/<int:meeting_id>', methods=['DELETE'])
@login_required
def api_delete_meeting(meeting_id):
    """Permanently delete a meeting (admin/teacher only)"""
    if current_user.role != 'admin' and current_user.role != 'teacher':
        return jsonify({'success': False, 'error': 'Unauthorized'})
    
    try:
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM meetings WHERE meeting_id = ?", (meeting_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============ CERTIFICATES API ============

@app.route('/api/certificates')
@login_required
def api_get_certificates():
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    
    if current_user.role == 'student':
        # Student sees only their own certificates
        cursor.execute('''
            SELECT certificate_id, certificate_type, issue_date, file_path, verified, certificate_code
            FROM certificates WHERE student_id = ?
            ORDER BY issue_date DESC
        ''', (current_user.id,))
    elif current_user.role == 'parent':
        # Parent sees only their child's certificates
        cursor.execute('''
            SELECT c.certificate_id, c.certificate_type, c.issue_date, c.file_path, c.verified, c.certificate_code
            FROM certificates c
            JOIN students s ON c.student_id = s.student_id
            JOIN student_users su ON s.student_id = su.student_id
            WHERE su.parent_email = ?
            ORDER BY c.issue_date DESC
        ''', (current_user.id,))
    else:
        # Admin/Teacher sees all certificates
        cursor.execute('''
            SELECT c.certificate_id, s.name, c.certificate_type, c.issue_date, c.verified
            FROM certificates c
            JOIN students s ON c.student_id = s.student_id
            ORDER BY c.issue_date DESC
        ''')
    
    certificates = []
    for row in cursor.fetchall():
        if current_user.role == 'admin' or current_user.role == 'teacher':
            certificates.append({
                'id': row[0],
                'student_name': row[1],
                'type': row[2],
                'issue_date': row[3],
                'verified': row[4]
            })
        else:
            certificates.append({
                'id': row[0],
                'type': row[1],
                'issue_date': row[2],
                'verified': row[3],
                'code': row[4] if len(row) > 4 else ''
            })
    
    conn.close()
    return jsonify(certificates)





@app.route('/api/upvote-reply/<int:reply_id>', methods=['POST'])
@login_required
def api_upvote_reply(reply_id):
    try:
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE forum_replies SET upvotes = upvotes + 1 WHERE reply_id = ?", (reply_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============ AI QUESTION GENERATOR API ============

@app.route('/api/generate-questions', methods=['POST'])
@login_required
def api_generate_questions():
    try:
        data = request.get_json()
        topic = data.get('topic')
        num_questions = data.get('num_questions', 5)
        
        prompt = f"""Generate {num_questions} multiple choice questions about {topic} for students.
        
        For each question, provide:
        - Question text
        - 4 options (A, B, C, D)
        - Correct answer (A, B, C, or D)
        
        Format as JSON:
        {{
            "questions": [
                {{
                    "text": "question here",
                    "options": ["option A", "option B", "option C", "option D"],
                    "correct": "A"
                }}
            ]
        }}
        
        Make questions educational and appropriate for high school students.
        """
        
        completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are an educational AI that generates high-quality multiple choice questions."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        response_text = completion.choices[0].message.content
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            questions_data = json.loads(json_match.group())
        else:
            questions_data = {
                "questions": [
                    {"text": f"What is the main concept of {topic}?", 
                     "options": ["Option A", "Option B", "Option C", "Option D"], 
                     "correct": "A"}
                ]
            }
        
        return jsonify({'success': True, 'questions': questions_data.get('questions', [])})
        
    except Exception as e:
        print(f"Error generating questions: {e}")
        return jsonify({
            'success': True,
            'questions': [
                {"text": f"What is the fundamental principle of {topic}?", 
                 "options": ["Understanding basics", "Advanced concepts", "Practical application", "Theoretical knowledge"], 
                 "correct": "A"},
                {"text": f"Which of the following is most important when studying {topic}?", 
                 "options": ["Regular practice", "Memorization", "Group study", "Online resources"], 
                 "correct": "A"}
            ]
        })

# ============ DOUBTS API ============

# ============ UPDATED DOUBT API ENDPOINTS ============

@app.route('/api/doubts')
@login_required
def api_get_doubts():
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    
    if current_user.role == 'admin' or current_user.role == 'teacher':
        # Fixed query to get student names from both students and student_users tables
        cursor.execute('''
            SELECT 
                d.doubt_id, 
                d.student_id, 
                COALESCE(s.name, u.name, 'Unknown') as student_name,
                d.question, 
                d.ai_answer, 
                d.teacher_answer, 
                d.status, 
                d.created_at, 
                d.resolved_at
            FROM doubts d
            LEFT JOIN students s ON d.student_id = s.student_id
            LEFT JOIN student_users u ON d.student_id = u.student_id
            ORDER BY 
                CASE d.status 
                    WHEN 'pending' THEN 1 
                    WHEN 'ai_answered' THEN 2 
                    ELSE 3 
                END,
                d.created_at DESC
        ''')
    else:
        cursor.execute('''
            SELECT doubt_id, question, ai_answer, teacher_answer, status, created_at, resolved_at
            FROM doubts
            WHERE student_id = ?
            ORDER BY created_at DESC
        ''', (current_user.id,))
    
    doubts = []
    for row in cursor.fetchall():
        if current_user.role == 'admin' or current_user.role == 'teacher':
            doubts.append({
                'doubt_id': row[0],
                'student_id': row[1],
                'student_name': row[2] or 'Unknown',
                'question': row[3],
                'ai_answer': row[4],
                'teacher_answer': row[5],
                'status': row[6],
                'created_at': row[7],
                'resolved_at': row[8]
            })
        else:
            doubts.append({
                'doubt_id': row[0],
                'question': row[1],
                'ai_answer': row[2],
                'teacher_answer': row[3],
                'status': row[4],
                'created_at': row[5],
                'resolved_at': row[6]
            })
    
    conn.close()
    return jsonify(doubts)

@app.route('/api/answer-doubt', methods=['POST'])
@login_required
def api_answer_doubt():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data received'})
        
        doubt_id = data.get('doubt_id')
        teacher_answer = data.get('answer')
        
        print(f"Answering doubt {doubt_id} with answer: {teacher_answer[:50]}...")  # Debug
        
        if not doubt_id:
            return jsonify({'success': False, 'error': 'Doubt ID is required'})
        
        if not teacher_answer:
            return jsonify({'success': False, 'error': 'Answer is required'})
        
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        
        # Get student_id for notification
        cursor.execute("SELECT student_id FROM doubts WHERE doubt_id = ?", (doubt_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return jsonify({'success': False, 'error': 'Doubt not found'})
        
        student_id = result[0]
        
        # Update the doubt
        cursor.execute('''
            UPDATE doubts 
            SET teacher_answer = ?, status = 'resolved', resolved_at = datetime('now')
            WHERE doubt_id = ?
        ''', (teacher_answer, doubt_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error in answer-doubt: {e}")
        return jsonify({'success': False, 'error': str(e)})
    

@app.route('/api/delete-doubt/<int:doubt_id>', methods=['DELETE'])
@login_required
def api_delete_doubt(doubt_id):
    try:
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        
        # Check if user has permission to delete
        if current_user.role == 'admin' or current_user.role == 'teacher':
            # Admin/Teacher can delete any doubt
            cursor.execute("DELETE FROM doubts WHERE doubt_id = ?", (doubt_id,))
        else:
            # Student can only delete their own doubts
            cursor.execute("DELETE FROM doubts WHERE doubt_id = ? AND student_id = ?", (doubt_id, current_user.id))
        
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        
        if affected > 0:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Not authorized or doubt not found'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/ask-doubt', methods=['POST'])
@login_required
def api_ask_doubt():
    try:
        data = request.get_json()
        question = data.get('question')
        
        completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are an expert tutor. Provide clear, concise, and helpful answers to student questions. Keep answers educational and easy to understand."},
                {"role": "user", "content": question}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        ai_answer = completion.choices[0].message.content
        
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO doubts (student_id, question, ai_answer, status)
            VALUES (?, ?, ?, 'ai_answered')
        ''', (current_user.id, question, ai_answer))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'answer': ai_answer})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ============ STUDY BUDDY API ============

@app.route('/api/study-session', methods=['POST'])
@login_required
def api_study_session():
    try:
        data = request.get_json()
        action = data.get('action')
        
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        
        if action == 'start':
            cursor.execute('''
                INSERT INTO study_sessions (student_id, start_time)
                VALUES (?, datetime('now'))
            ''', (current_user.id,))
            session_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'session_id': session_id})
            
        elif action == 'end':
            session_id = data.get('session_id')
            cursor.execute('''
                UPDATE study_sessions 
                SET end_time = datetime('now'),
                    duration_minutes = (strftime('%s', datetime('now')) - strftime('%s', start_time)) / 60
                WHERE session_id = ?
            ''', (session_id,))
            conn.commit()
            conn.close()
            return jsonify({'success': True})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/study-streak')
@login_required
def api_study_streak():
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT COUNT(DISTINCT date(start_time)) 
        FROM study_sessions 
        WHERE student_id = ? 
        AND start_time >= date('now', '-30 days')
    ''', (current_user.id,))
    streak = cursor.fetchone()[0] or 0
    
    cursor.execute('''
        SELECT COALESCE(SUM(duration_minutes), 0) 
        FROM study_sessions 
        WHERE student_id = ? 
        AND date(start_time) = date('now')
    ''', (current_user.id,))
    today_minutes = cursor.fetchone()[0] or 0
    
    conn.close()
    return jsonify({'streak': streak, 'today_minutes': today_minutes})



# ============ AI LEARNING PATH API ============

@app.route('/api/learning-path')
@login_required
def api_learning_path():
    if current_user.role != 'student':
        return jsonify({'error': 'Student only'})
    
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name, final_score, grade, study_hours, attendance_percentage, midterm_score, assignment_score, quiz_score, project_score FROM students WHERE student_id = ?", (current_user.student_id,))
    student = cursor.fetchone()
    conn.close()
    
    scores = {'Midterm': student[5], 'Assignment': student[6], 'Quiz': student[7], 'Project': student[8]}
    weakest = min(scores, key=scores.get)
    
    if student[1] >= 85:
        focus = "Advanced topics and competitive preparation"
        resources = ["Advanced problem sets", "Research papers", "Online courses"]
        daily_tasks = ["Teach concepts to peers", "Solve advanced problems", "Prepare for competitions"]
    elif student[1] >= 70:
        focus = "Concept strengthening and practice"
        resources = ["Practice worksheets", "Video tutorials", "Study groups"]
        daily_tasks = ["Review weak topics", "Practice 20 problems", "Take mock tests"]
    else:
        focus = "Foundation building and basic concepts"
        resources = ["Basic concept videos", "Step-by-step guides", "One-on-one tutoring"]
        daily_tasks = ["Learn 2 new concepts daily", "Solve 10 basic problems", "Revise previous topics"]
    
    recommended_hours = max(5, 8 - int(student[3])) if student[1] < 70 else student[3]
    
    learning_path = {
        'student_name': student[0],
        'current_score': student[1],
        'current_grade': student[2],
        'weakest_area': weakest,
        'focus_area': focus,
        'recommended_study_hours': recommended_hours,
        'recommended_attendance': max(85, student[4] + 5) if student[4] < 85 else student[4],
        'daily_tasks': daily_tasks,
        'weekly_goals': [
            f"Increase {weakest} score by 10%",
            "Complete all assignments on time",
            "Review notes daily",
            "Take one practice test"
        ],
        'resources': resources,
        'estimated_improvement': round((8 - student[3]) * 1.5, 1) if student[1] < 70 else 5,
        'predicted_grade': 'A' if student[1] >= 70 else 'B' if student[1] >= 60 else 'C'
    }
    
    return jsonify(learning_path)


# Add these DELETE endpoints if not already present

@app.route('/api/delete-study-room/<int:room_id>', methods=['DELETE'])
@login_required
def api_delete_study_room(room_id):
    try:
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM room_messages WHERE room_id = ?", (room_id,))
        cursor.execute("DELETE FROM room_members WHERE room_id = ?", (room_id,))
        cursor.execute("DELETE FROM room_files WHERE room_id = ?", (room_id,))
        cursor.execute("DELETE FROM whiteboard_data WHERE room_id = ?", (room_id,))
        cursor.execute("DELETE FROM study_rooms WHERE room_id = ?", (room_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})



@app.route('/api/delete-topic/<int:topic_id>', methods=['DELETE'])
@login_required
def api_delete_topic(topic_id):
    try:
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM forum_replies WHERE topic_id = ?", (topic_id,))
        cursor.execute("DELETE FROM forum_topics WHERE topic_id = ?", (topic_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/delete-reply/<int:reply_id>', methods=['DELETE'])
@login_required
def api_delete_reply(reply_id):
    try:
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM forum_replies WHERE reply_id = ?", (reply_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/delete-goal/<int:goal_id>', methods=['DELETE'])
@login_required
def api_delete_goal(goal_id):
    try:
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM goal_checkpoints WHERE goal_id = ?", (goal_id,))
        cursor.execute("DELETE FROM student_goals WHERE goal_id = ?", (goal_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    
@app.route('/api/public-statistics')
def api_public_statistics():
    """Public API for index page - no login required"""
    try:
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM students")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT AVG(final_score) FROM students")
        avg_score = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT AVG(attendance_percentage) FROM students")
        avg_att = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT grade, COUNT(*) FROM students GROUP BY grade ORDER BY grade")
        grade_dist = [{'grade': row[0], 'count': row[1]} for row in cursor.fetchall()]
        
        cursor.execute("SELECT name, final_score, grade FROM students ORDER BY final_score DESC LIMIT 3")
        top_performers = [{'name': row[0], 'score': row[1], 'grade': row[2]} for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'total_students': total,
            'avg_final_score': round(avg_score, 1),
            'avg_attendance': round(avg_att, 1),
            'grade_distribution': grade_dist,
            'top_performers': top_performers
        })
    except Exception as e:
        print(f"Public stats error: {e}")
        return jsonify({
            'total_students': 500,
            'avg_final_score': 68.5,
            'avg_attendance': 82.3,
            'grade_distribution': [
                {'grade': 'A+', 'count': 25}, {'grade': 'A', 'count': 85},
                {'grade': 'B', 'count': 150}, {'grade': 'C', 'count': 140},
                {'grade': 'D', 'count': 60}, {'grade': 'F', 'count': 30}
            ],
            'top_performers': [
                {'name': 'John Collins', 'score': 89.5, 'grade': 'A'},
                {'name': 'Emma Watson', 'score': 87.2, 'grade': 'A'},
                {'name': 'Michael Brown', 'score': 85.8, 'grade': 'A'}
            ]
        })

# ============ NOTIFICATION SYSTEM ============

@app.route('/api/notifications')
@login_required
def api_get_notifications():
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    
    user_id = current_user.id if current_user.role == 'student' else current_user.username
    user_type = current_user.role
    
    cursor.execute('''
        SELECT id, title, message, type, is_read, created_at, action_url, icon
        FROM notifications 
        WHERE user_id = ? AND user_type = ?
        ORDER BY created_at DESC LIMIT 50
    ''', (user_id, user_type))
    
    notifications = []
    for row in cursor.fetchall():
        notifications.append({
            'id': row[0],
            'title': row[1],
            'message': row[2],
            'type': row[3],
            'is_read': row[4],
            'created_at': row[5],
            'action_url': row[6],
            'icon': row[7]
        })
    
    # Get unread count
    cursor.execute('''
        SELECT COUNT(*) FROM notifications 
        WHERE user_id = ? AND user_type = ? AND is_read = 0
    ''', (user_id, user_type))
    unread_count = cursor.fetchone()[0]
    
    conn.close()
    
    return jsonify({
        'notifications': notifications,
        'unread_count': unread_count
    })

@app.route('/api/notifications/mark-read', methods=['POST'])
@login_required
def api_mark_notification_read():
    try:
        data = request.get_json()
        notification_id = data.get('notification_id')
        
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE notifications SET is_read = 1 WHERE id = ?", (notification_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/notifications/mark-all-read', methods=['POST'])
@login_required
def api_mark_all_notifications_read():
    try:
        user_id = current_user.id if current_user.role == 'student' else current_user.username
        user_type = current_user.role
        
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ? AND user_type = ?", (user_id, user_type))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def send_notification(user_id, user_type, title, message, notif_type='info', action_url=None, icon=None):
    """Helper function to send notification"""
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO notifications (user_id, user_type, title, message, type, action_url, icon)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, user_type, title, message, notif_type, action_url, icon))
    
    conn.commit()
    conn.close()
    
    # Also send via Socket.IO for real-time
    socketio.emit('new_notification', {
        'title': title,
        'message': message,
        'type': notif_type,
        'icon': icon
    }, room=f'user_{user_id}')


@app.route('/notifications')
@login_required
def notifications():
    return render_template('notifications.html')

# ============ USER ACTIVITY LOGGING ============

import time
from datetime import datetime

def log_activity(user_id, user_name, user_role, action, details=None):
    """Log user activity to database"""
    try:
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        
        # Get IP address and user agent
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr) if hasattr(request, 'headers') else 'unknown'
        user_agent = request.headers.get('User-Agent', 'unknown') if hasattr(request, 'headers') else 'unknown'
        
        cursor.execute('''
            INSERT INTO activity_logs (user_id, user_name, user_role, action, details, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, user_name, user_role, action, details, ip_address, user_agent))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error logging activity: {e}")

# Add logging to existing endpoints
# Call this function in login, logout, add/update/delete operations




@app.route('/api/activity-stats')
@login_required
def api_activity_stats():
    """Get activity statistics (admin only)"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        
        # Total activities
        cursor.execute("SELECT COUNT(*) FROM activity_logs")
        total = cursor.fetchone()[0]
        
        # Today's activities
        cursor.execute("SELECT COUNT(*) FROM activity_logs WHERE DATE(created_at) = DATE('now')")
        today = cursor.fetchone()[0]
        
        # Last 7 days activity
        cursor.execute("""
            SELECT DATE(created_at) as date, COUNT(*) 
            FROM activity_logs 
            WHERE created_at >= DATE('now', '-7 days')
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        """)
        weekly = [{'date': row[0], 'count': row[1]} for row in cursor.fetchall()]
        
        # Activities by action type
        cursor.execute("""
            SELECT action, COUNT(*) 
            FROM activity_logs 
            GROUP BY action 
            ORDER BY COUNT(*) DESC 
            LIMIT 5
        """)
        by_action = [{'action': row[0], 'count': row[1]} for row in cursor.fetchall()]
        
        # Activities by user role
        cursor.execute("SELECT user_role, COUNT(*) FROM activity_logs GROUP BY user_role")
        by_role = [{'role': row[0], 'count': row[1]} for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'total': total,
            'today': today,
            'weekly': weekly,
            'by_action': by_action,
            'by_role': by_role
        })
        
    except Exception as e:
        print(f"Error in activity-stats: {e}")
        return jsonify({
            'total': 0,
            'today': 0,
            'weekly': [],
            'by_action': [],
            'by_role': []
        })


@app.route('/api/delete-all-activity-logs', methods=['DELETE'])
@login_required
def api_delete_all_activity_logs():
    """Delete all activity logs (admin only)"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        
        # Get count before deletion
        cursor.execute("SELECT COUNT(*) FROM activity_logs")
        count = cursor.fetchone()[0]
        
        # Delete all logs
        cursor.execute("DELETE FROM activity_logs")
        
        # Reset autoincrement
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='activity_logs'")
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'deleted_count': count})
        
    except Exception as e:
        print(f"Error deleting logs: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/log-activity', methods=['POST'])
@login_required
def api_log_activity():
    """Log user activity (automatic)"""
    try:
        data = request.get_json()
        
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO activity_logs (user_id, user_name, user_role, action, details, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            current_user.id,
            current_user.name,
            current_user.role,
            data.get('action', 'unknown'),
            data.get('details', ''),
            request.remote_addr,
            request.headers.get('User-Agent', 'Unknown')[:200]
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/test-audit')
@login_required
def test_audit():
    """Test page for audit system"""
    if current_user.role != 'admin':
        return "Admin only"
    
    # Insert a test log
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO activity_logs (user_id, user_name, user_role, action, details, ip_address)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (current_user.id, current_user.name, current_user.role, 'test_action', 'Test from debug page', request.remote_addr))
    conn.commit()
    conn.close()
    
    return "Test log added. Check /api/activity-logs"

@app.route('/activity-logs')
@login_required
def activity_logs():
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    return render_template('activity_logs.html')

# ============ DELETE QUIZ ============

@app.route('/api/delete-quiz/<int:quiz_id>', methods=['DELETE'])
@login_required
def api_delete_quiz(quiz_id):
    """Delete a quiz (admin/teacher only)"""
    if current_user.role != 'admin' and current_user.role != 'teacher':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        
        # Check if quiz exists
        cursor.execute("SELECT quiz_id FROM quizzes WHERE quiz_id = ?", (quiz_id,))
        if not cursor.fetchone():
            return jsonify({'success': False, 'error': 'Quiz not found'})
        
        # Delete all related data
        cursor.execute("DELETE FROM quiz_attempt_details WHERE result_id IN (SELECT result_id FROM quiz_results WHERE quiz_id = ?)", (quiz_id,))
        cursor.execute("DELETE FROM quiz_results WHERE quiz_id = ?", (quiz_id,))
        cursor.execute("DELETE FROM questions WHERE quiz_id = ?", (quiz_id,))
        cursor.execute("DELETE FROM quizzes WHERE quiz_id = ?", (quiz_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/submit-quiz', methods=['POST'])
@login_required
def api_submit_quiz():
    try:
        data = request.get_json()
        quiz_id = data.get('quiz_id')
        answers = data.get('answers', {})
        
        print(f"Submitting quiz {quiz_id} for student {current_user.id}")
        print(f"Answers received: {answers}")
        
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        
        # Get all questions for this quiz
        cursor.execute("SELECT question_id, correct_answer, points FROM questions WHERE quiz_id = ?", (quiz_id,))
        questions = cursor.fetchall()
        
        if not questions:
            return jsonify({'success': False, 'error': 'No questions found for this quiz'})
        
        score = 0
        total_possible = 0
        answer_details = []
        
        for q in questions:
            q_id = q[0]
            correct = q[1]
            points = q[2]
            total_possible += points
            
            user_answer = answers.get(str(q_id))
            is_correct = 1 if user_answer and user_answer == correct else 0
            if is_correct:
                score += points
            
            answer_details.append({
                'question_id': q_id,
                'student_answer': user_answer or '',
                'is_correct': is_correct,
                'points_earned': points if is_correct else 0
            })
        
        percentage = (score / total_possible) * 100 if total_possible > 0 else 0
        
        # Insert into quiz_results
        cursor.execute('''
            INSERT INTO quiz_results (student_id, quiz_id, score, total_possible, percentage, submitted_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
        ''', (current_user.id, quiz_id, score, total_possible, percentage))
        
        result_id = cursor.lastrowid
        print(f"Result saved with ID: {result_id}")
        
        # Insert answer details
        for detail in answer_details:
            cursor.execute('''
                INSERT INTO quiz_attempt_details (result_id, question_id, student_answer, is_correct, points_earned)
                VALUES (?, ?, ?, ?, ?)
            ''', (result_id, detail['question_id'], detail['student_answer'], detail['is_correct'], detail['points_earned']))
        
        conn.commit()
        conn.close()
        
        # Award points for good score
        if percentage >= 80:
            try:
                calculate_points(current_user.id)
            except Exception as e:
                print(f"Error awarding points: {e}")
        
        return jsonify({
            'success': True,
            'score': score,
            'total_possible': total_possible,
            'percentage': round(percentage, 1),
            'result_id': result_id
        })
        
    except Exception as e:
        print(f"Error in submit_quiz: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})   

@app.route('/api/quiz-review/<int:result_id>')
@login_required
def api_quiz_review(result_id):
    """Get quiz attempt details for review"""
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    
    # Get quiz info
    cursor.execute('''
        SELECT qr.quiz_id, qr.score, qr.total_possible, qr.percentage, qr.completed_at, qz.title
        FROM quiz_results qr
        JOIN quizzes qz ON qr.quiz_id = qz.quiz_id
        WHERE qr.result_id = ? AND qr.student_id = ?
    ''', (result_id, current_user.id))
    
    result = cursor.fetchone()
    if not result:
        conn.close()
        return jsonify({'error': 'Not found'}), 404
    
    quiz_id, score, total_possible, percentage, completed_at, title = result
    
    # Get questions and answers
    cursor.execute('''
        SELECT q.question_id, q.question_text, q.option_a, q.option_b, q.option_c, q.option_d, q.correct_answer,
               ad.student_answer, ad.is_correct, ad.points_earned
        FROM questions q
        LEFT JOIN quiz_attempt_details ad ON q.question_id = ad.question_id
        LEFT JOIN quiz_results qr ON ad.result_id = qr.result_id
        WHERE q.quiz_id = ? AND qr.result_id = ?
    ''', (quiz_id, result_id))
    
    questions = []
    for row in cursor.fetchall():
        questions.append({
            'question_id': row[0],
            'question_text': row[1],
            'options': [row[2], row[3], row[4], row[5]],
            'correct_answer': row[6],
            'student_answer': row[7] or '',
            'is_correct': row[8] or 0,
            'points_earned': row[9] or 0
        })
    
    conn.close()
    
    return jsonify({
        'quiz_title': title,
        'score': score,
        'total_possible': total_possible,
        'percentage': percentage,
        'completed_at': completed_at,
        'questions': questions
    })

@app.route('/api/quiz-results')
@login_required
def api_quiz_results():
    try:
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT qr.result_id, qr.quiz_id, q.title, qr.score, qr.total_possible, qr.percentage, qr.submitted_at
            FROM quiz_results qr
            JOIN quizzes q ON qr.quiz_id = q.quiz_id
            WHERE qr.student_id = ?
            ORDER BY qr.submitted_at DESC
        ''', (current_user.id,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'result_id': row[0],
                'quiz_id': row[1],
                'title': row[2],
                'score': row[3],
                'total_possible': row[4],
                'percentage': row[5],
                'submitted_at': row[6]
            })
        
        conn.close()
        return jsonify(results)
        
    except Exception as e:
        print(f"Error in quiz_results: {str(e)}")
        return jsonify([])

# ============ ADMIN QUIZ ANALYTICS ============

@app.route('/api/quiz-analytics')
@login_required
def api_quiz_analytics():
    """Get all quiz attempts with student details for admin/teacher"""
    if current_user.role != 'admin' and current_user.role != 'teacher':
        return jsonify({'error': 'Unauthorized'}), 403
    
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    
    # Get all quiz attempts with student info
    cursor.execute('''
        SELECT 
            qr.result_id,
            qr.quiz_id,
            qz.title as quiz_title,
            qr.student_id,
            s.name as student_name,
            qr.score,
            qr.total_possible,
            qr.percentage,
            qr.submitted_at
        FROM quiz_results qr
        JOIN students s ON qr.student_id = s.student_id
        JOIN quizzes qz ON qr.quiz_id = qz.quiz_id
        ORDER BY qr.submitted_at DESC
    ''')
    
    attempts = []
    for row in cursor.fetchall():
        attempts.append({
            'result_id': row[0],
            'quiz_id': row[1],
            'quiz_title': row[2],
            'student_id': row[3],
            'student_name': row[4],
            'score': row[5],
            'total_possible': row[6],
            'percentage': round(row[7], 1),
            'submitted_at': row[8]
        })
    
    conn.close()
    return jsonify(attempts)

@app.route('/api/quiz-analytics/<int:result_id>')
@login_required
def api_quiz_analytics_detail(result_id):
    """Get detailed answer analysis for a specific attempt"""
    if current_user.role != 'admin' and current_user.role != 'teacher':
        return jsonify({'error': 'Unauthorized'}), 403
    
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    
    # Get attempt info
    cursor.execute('''
        SELECT 
            qr.result_id,
            qr.quiz_id,
            qz.title as quiz_title,
            qr.student_id,
            s.name as student_name,
            qr.score,
            qr.total_possible,
            qr.percentage,
            qr.submitted_at
        FROM quiz_results qr
        JOIN students s ON qr.student_id = s.student_id
        JOIN quizzes qz ON qr.quiz_id = qz.quiz_id
        WHERE qr.result_id = ?
    ''', (result_id,))
    
    attempt = cursor.fetchone()
    if not attempt:
        conn.close()
        return jsonify({'error': 'Attempt not found'}), 404
    
    # Get all questions and answers for this attempt
    cursor.execute('''
        SELECT 
            q.question_id,
            q.question_text,
            q.option_a,
            q.option_b,
            q.option_c,
            q.option_d,
            q.correct_answer,
            ad.student_answer,
            ad.is_correct,
            ad.points_earned,
            q.points
        FROM questions q
        LEFT JOIN quiz_attempt_details ad ON q.question_id = ad.question_id AND ad.result_id = ?
        WHERE q.quiz_id = ?
    ''', (result_id, attempt[1]))
    
    questions = []
    for row in cursor.fetchall():
        # Find the option text for student's answer
        student_answer_text = ''
        if row[7]:
            opt_index = ord(row[7]) - 65
            if opt_index == 0: student_answer_text = row[2]
            elif opt_index == 1: student_answer_text = row[3]
            elif opt_index == 2: student_answer_text = row[4]
            elif opt_index == 3: student_answer_text = row[5]
        
        # Find correct answer text
        correct_answer_text = ''
        correct_index = ord(row[6]) - 65
        if correct_index == 0: correct_answer_text = row[2]
        elif correct_index == 1: correct_answer_text = row[3]
        elif correct_index == 2: correct_answer_text = row[4]
        elif correct_index == 3: correct_answer_text = row[5]
        
        questions.append({
            'question_id': row[0],
            'question_text': row[1],
            'options': [row[2] or '', row[3] or '', row[4] or '', row[5] or ''],
            'correct_answer': row[6],
            'correct_answer_text': correct_answer_text,
            'student_answer': row[7] or 'Not answered',
            'student_answer_text': student_answer_text or 'Not answered',
            'is_correct': row[8] or 0,
            'points_earned': row[9] or 0,
            'total_points': row[10] or 1
        })
    
    conn.close()
    
    return jsonify({
        'result_id': attempt[0],
        'quiz_id': attempt[1],
        'quiz_title': attempt[2],
        'student_id': attempt[3],
        'student_name': attempt[4],
        'score': attempt[5],
        'total_possible': attempt[6],
        'percentage': attempt[7],
        'submitted_at': attempt[8],
        'questions': questions
    })

@app.route('/api/quiz-summary')
@login_required
def api_quiz_summary():
    """Get summary statistics for all quizzes"""
    if current_user.role != 'admin' and current_user.role != 'teacher':
        return jsonify({'error': 'Unauthorized'}), 403
    
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    
    # Total quizzes
    cursor.execute("SELECT COUNT(*) FROM quizzes")
    total_quizzes = cursor.fetchone()[0]
    
    # Total attempts
    cursor.execute("SELECT COUNT(*) FROM quiz_results")
    total_attempts = cursor.fetchone()[0]
    
    # Average score across all attempts
    cursor.execute("SELECT AVG(percentage) FROM quiz_results")
    avg_score = cursor.fetchone()[0] or 0
    
    # Total students who attempted at least one quiz
    cursor.execute("SELECT COUNT(DISTINCT student_id) FROM quiz_results")
    active_students = cursor.fetchone()[0]
    
    # Quiz-wise statistics
    cursor.execute('''
        SELECT 
            q.quiz_id,
            q.title,
            COUNT(qr.result_id) as attempts,
            AVG(qr.percentage) as avg_score,
            MAX(qr.percentage) as best_score,
            MIN(qr.percentage) as worst_score
        FROM quizzes q
        LEFT JOIN quiz_results qr ON q.quiz_id = qr.quiz_id
        GROUP BY q.quiz_id
        ORDER BY attempts DESC
    ''')
    
    quiz_stats = []
    for row in cursor.fetchall():
        quiz_stats.append({
            'quiz_id': row[0],
            'title': row[1],
            'attempts': row[2] or 0,
            'avg_score': round(row[3] or 0, 1),
            'best_score': round(row[4] or 0, 1),
            'worst_score': round(row[5] or 0, 1)
        })
    
    conn.close()
    
    return jsonify({
        'total_quizzes': total_quizzes,
        'total_attempts': total_attempts,
        'avg_score': round(avg_score, 1),
        'active_students': active_students,
        'quiz_stats': quiz_stats
    })

@app.route('/quiz-analytics')
@login_required
def quiz_analytics():
    if current_user.role != 'admin' and current_user.role != 'teacher':
        return redirect(url_for('dashboard'))
    return render_template('quiz_analytics.html')

# ============ EXAM PROCTORING SYSTEM ============

@app.route('/proctored-exam/<int:quiz_id>')
@login_required
def proctored_exam(quiz_id):
    """Start a proctored exam"""
    # Create proctoring session
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO proctoring_sessions (student_id, quiz_id, start_time)
        VALUES (?, ?, datetime('now'))
    ''', (current_user.id, quiz_id))
    session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return render_template('proctored_exam.html', quiz_id=quiz_id, session_id=session_id)

@app.route('/api/log-proctoring-event', methods=['POST'])
@login_required
def api_log_proctoring_event():
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        event_type = data.get('event_type')
        event_data = data.get('event_data', '')
        
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO proctoring_logs (session_id, event_type, event_data)
            VALUES (?, ?, ?)
        ''', (session_id, event_type, event_data))
        
        # Don't flag fullscreen_entered as violation
        if event_type in ['tab_switch', 'copy_attempt', 'paste_attempt', 'right_click', 'exit_fullscreen']:
            severity = 2 if event_type == 'tab_switch' else 1
            cursor.execute('''
                INSERT INTO proctoring_violations (session_id, student_id, violation_type, severity, details)
                VALUES (?, ?, ?, ?, ?)
            ''', (session_id, current_user.id, event_type, severity, event_data))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/end-proctored-exam', methods=['POST'])
@login_required
def api_end_proctored_exam():
    """End proctoring session"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE proctoring_sessions 
            SET end_time = datetime('now'), status = 'completed'
            WHERE session_id = ?
        ''', (session_id,))
        
        # Get violation count
        cursor.execute('''
            SELECT COUNT(*) FROM proctoring_violations 
            WHERE session_id = ? AND severity >= 2
        ''', (session_id,))
        serious_violations = cursor.fetchone()[0]
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'serious_violations': serious_violations})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/proctoring-report/<int:session_id>')
@login_required
def api_proctoring_report(session_id):
    """Get proctoring report for admin/teacher"""
    if current_user.role != 'admin' and current_user.role != 'teacher':
        return jsonify({'error': 'Unauthorized'}), 403
    
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    
    # Get session info
    cursor.execute('''
        SELECT ps.session_id, ps.student_id, s.name, ps.quiz_id, q.title, 
               ps.start_time, ps.end_time, ps.status
        FROM proctoring_sessions ps
        JOIN students s ON ps.student_id = s.student_id
        JOIN quizzes q ON ps.quiz_id = q.quiz_id
        WHERE ps.session_id = ?
    ''', (session_id,))
    session = cursor.fetchone()
    
    # Get violations
    cursor.execute('''
        SELECT violation_type, severity, details, timestamp
        FROM proctoring_violations
        WHERE session_id = ?
        ORDER BY timestamp
    ''', (session_id,))
    violations = [{'type': row[0], 'severity': row[1], 'details': row[2], 'timestamp': row[3]} for row in cursor.fetchall()]
    
    # Get logs
    cursor.execute('''
        SELECT event_type, event_data, timestamp
        FROM proctoring_logs
        WHERE session_id = ?
        ORDER BY timestamp
        LIMIT 100
    ''', (session_id,))
    logs = [{'event': row[0], 'data': row[1], 'timestamp': row[2]} for row in cursor.fetchall()]
    
    conn.close()
    
    return jsonify({
        'session': {
            'id': session[0], 'student_id': session[1], 'student_name': session[2],
            'quiz_id': session[3], 'quiz_title': session[4],
            'start_time': session[5], 'end_time': session[6], 'status': session[7]
        },
        'violations': violations,
        'logs': logs,
        'total_violations': len(violations),
        'serious_violations': len([v for v in violations if v['severity'] >= 2])
    })

@app.route('/api/proctoring-sessions')
@login_required
def api_proctoring_sessions():
    """Get all proctoring sessions for admin/teacher"""
    if current_user.role != 'admin' and current_user.role != 'teacher':
        return jsonify({'error': 'Unauthorized'}), 403
    
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT ps.session_id, ps.student_id, s.name, ps.quiz_id, q.title, 
               ps.start_time, ps.end_time, ps.status,
               (SELECT COUNT(*) FROM proctoring_violations WHERE session_id = ps.session_id) as total_violations,
               (SELECT COUNT(*) FROM proctoring_violations WHERE session_id = ps.session_id AND severity >= 2) as serious_violations
        FROM proctoring_sessions ps
        JOIN students s ON ps.student_id = s.student_id
        JOIN quizzes q ON ps.quiz_id = q.quiz_id
        ORDER BY ps.start_time DESC
        LIMIT 50
    ''')
    
    sessions = []
    for row in cursor.fetchall():
        sessions.append({
            'session_id': row[0], 'student_id': row[1], 'student_name': row[2],
            'quiz_id': row[3], 'quiz_title': row[4], 'start_time': row[5],
            'end_time': row[6], 'status': row[7], 'total_violations': row[8],
            'serious_violations': row[9]
        })
    
    conn.close()
    return jsonify(sessions)

@app.route('/api/flag-proctoring-session/<int:session_id>', methods=['POST'])
@login_required
def api_flag_proctoring_session(session_id):
    """Flag a session for review"""
    if current_user.role != 'admin' and current_user.role != 'teacher':
        return jsonify({'error': 'Unauthorized'}), 403
    
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE proctoring_sessions SET status = "flagged" WHERE session_id = ?', (session_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/approve-proctoring-session/<int:session_id>', methods=['POST'])
@login_required
def api_approve_proctoring_session(session_id):
    """Approve a session"""
    if current_user.role != 'admin' and current_user.role != 'teacher':
        return jsonify({'error': 'Unauthorized'}), 403
    
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE proctoring_sessions SET status = "approved" WHERE session_id = ?', (session_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})



@app.route('/api/test-violation', methods=['POST'])
@login_required
def api_test_violation():
    """Test endpoint to manually add a violation"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        violation_type = data.get('violation_type', 'test_violation')
        
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO proctoring_violations (session_id, student_id, violation_type, severity, details)
            VALUES (?, ?, ?, ?, ?)
        ''', (session_id, current_user.id, violation_type, 1, 'Test violation from button'))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Test violation added'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/proctoring-reports')
@login_required
def proctoring_reports():
    if current_user.role != 'admin' and current_user.role != 'teacher':
        return redirect(url_for('dashboard'))
    return render_template('proctoring_reports.html')


def generate_certificate_code():
    return 'CERT-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

@app.route('/api/generate-certificate', methods=['POST'])
@login_required
def api_generate_certificate():
    if current_user.role != 'admin' and current_user.role != 'teacher':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        student_id = data.get('student_id')
        cert_type = data.get('type', 'achievement')
        custom_message = data.get('message', '')
        
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        
        # Get student name and parent email
        cursor.execute("""
            SELECT s.name, su.parent_email, su.email 
            FROM students s 
            LEFT JOIN student_users su ON s.student_id = su.student_id 
            WHERE s.student_id = ?
        """, (student_id,))
        
        student = cursor.fetchone()
        
        if not student:
            conn.close()
            return jsonify({'success': False, 'error': 'Student not found'})
        
        student_name = student[0]
        parent_email = student[1] if len(student) > 1 else None
        student_email = student[2] if len(student) > 2 else None
        
        certificate_code = generate_certificate_code()
        
        # Insert certificate
        cursor.execute('''
            INSERT INTO certificates (student_id, certificate_type, issue_date, certificate_code, issued_by, reason)
            VALUES (?, ?, datetime('now'), ?, ?, ?)
        ''', (student_id, cert_type, certificate_code, current_user.name, custom_message))
        
        cert_id = cursor.lastrowid
        
        # Create notification for student
        cursor.execute('''
            INSERT INTO notifications (user_id, user_type, title, message, type, action_url, icon)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (student_id, 'student', '🎉 New Certificate Earned!', 
              f'Congratulations! You have received a {cert_type} certificate.', 
              'success', f'/certificate-view/{cert_id}', 'fa-certificate'))
        
        # Create notification for parent
        if parent_email:
            cursor.execute('''
                INSERT INTO notifications (user_id, user_type, title, message, type, action_url, icon)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (parent_email, 'parent', '📜 Your Child Earned a Certificate', 
                  f'Your child {student_name} has received a {cert_type} certificate.', 
                  'info', f'/certificate-view/{cert_id}', 'fa-certificate'))
        
        conn.commit()
        conn.close()
        
        # Send real-time notification via Socket.IO
        socketio.emit('new_notification', {
            'title': 'New Certificate!',
            'message': f'You have received a {cert_type} certificate!',
            'type': 'success'
        }, room=f'user_{student_id}')
        
        if parent_email:
            socketio.emit('new_notification', {
                'title': 'Child Earned Certificate',
                'message': f'Your child {student_name} received a certificate!',
                'type': 'info'
            }, room=f'user_{parent_email}')
        
        return jsonify({'success': True, 'certificate_id': cert_id, 'code': certificate_code, 'student_name': student_name})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
        
@app.route('/certificate-view/<int:cert_id>')
@login_required
def certificate_view(cert_id):
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    
    # FIXED: Use table aliases to avoid ambiguous column names
    cursor.execute('''
        SELECT c.certificate_id, c.certificate_type, c.issue_date, c.certificate_code, 
               c.reason, s.name, s.final_score, s.grade
        FROM certificates c
        JOIN students s ON c.student_id = s.student_id
        WHERE c.certificate_id = ?
    ''', (cert_id,))
    
    cert = cursor.fetchone()
    conn.close()
    
    if not cert:
        return "Certificate not found", 404
    
    # Update download count
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE certificates SET download_count = download_count + 1 WHERE certificate_id = ?', (cert_id,))
    conn.commit()
    conn.close()
    
    cert_type_map = {
        'achievement': 'Academic Achievement',
        'topper': 'Top Performer',
        'improvement': 'Most Improved',
        'attendance': 'Perfect Attendance',
        'quiz_master': 'Quiz Master',
        'project_excellence': 'Project Excellence'
    }
    
    # Parse date safely
    try:
        issue_date = datetime.strptime(cert[2], '%Y-%m-%d %H:%M:%S').strftime('%B %d, %Y')
    except:
        issue_date = str(cert[2])
    
    return render_template('certificate_template.html', 
        student_name=cert[5],
        cert_type=cert_type_map.get(cert[1], 'Achievement'),
        issue_date=issue_date,
        cert_id=f"CERT-{cert[0]:06d}",
        cert_code=cert[3],
        score=cert[6],
        grade=cert[7],
        reason=cert[4] if cert[4] else ''
    )

@app.route('/api/forum-stats')
@login_required
def api_forum_stats():
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM forum_topics")
    total_topics = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM forum_replies")
    total_replies = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT student_id) FROM forum_replies")
    active_members = cursor.fetchone()[0] or 0
    
    cursor.execute('''
        SELECT s.name, COUNT(r.reply_id) as count
        FROM forum_replies r
        JOIN students s ON r.student_id = s.student_id
        GROUP BY r.student_id
        ORDER BY count DESC LIMIT 1
    ''')
    most_active = cursor.fetchone()
    
    conn.close()
    
    return jsonify({
        'total_topics': total_topics,
        'total_replies': total_replies,
        'active_members': active_members,
        'most_active': most_active[0] if most_active else 'None'
    })

@app.route('/forum-test')
@login_required
def forum_test():
    return render_template('forum_test.html')
@app.route('/forum')
@login_required
def forum():
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    
    # FIXED: Use LEFT JOIN to include admin-created topics
    cursor.execute('''
        SELECT t.topic_id, t.title, t.content, t.views, t.created_at, 
               COALESCE(s.name, u.name) as author, 
               COUNT(DISTINCT r.reply_id) as reply_count
        FROM forum_topics t
        LEFT JOIN students s ON t.student_id = s.student_id
        LEFT JOIN student_users u ON t.student_id = u.student_id
        LEFT JOIN forum_replies r ON t.topic_id = r.topic_id
        GROUP BY t.topic_id
        ORDER BY t.created_at DESC
    ''')
    
    topics = []
    for row in cursor.fetchall():
        topics.append({
            'topic_id': row[0],
            'title': row[1],
            'content': row[2],
            'views': row[3],
            'created_at': row[4],
            'author': row[5] or 'Unknown',
            'reply_count': row[6] or 0
        })
    
    conn.close()
    return render_template('forum.html', topics=topics)

@app.route('/create-topic', methods=['POST'])
@login_required
def create_topic():
    title = request.form.get('title')
    content = request.form.get('content')
    
    if not title or not content:
        flash('Please fill both fields', 'error')
        return redirect(url_for('forum'))
    
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO forum_topics (student_id, title, content)
        VALUES (?, ?, ?)
    ''', (current_user.id, title, content))
    conn.commit()
    conn.close()
    
    flash('Topic created successfully!', 'success')
    return redirect(url_for('forum'))

@app.route('/forum/topic/<int:topic_id>')
@login_required
def forum_topic(topic_id):
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    
    # Update views
    cursor.execute("UPDATE forum_topics SET views = views + 1 WHERE topic_id = ?", (topic_id,))
    conn.commit()
    
    # Get topic - FIXED to work with both students and admins
    cursor.execute('''
        SELECT t.topic_id, t.title, t.content, t.views, t.created_at, 
               COALESCE(s.name, u.name) as author
        FROM forum_topics t
        LEFT JOIN students s ON t.student_id = s.student_id
        LEFT JOIN student_users u ON t.student_id = u.student_id
        WHERE t.topic_id = ?
    ''', (topic_id,))
    topic = cursor.fetchone()
    
    if not topic:
        conn.close()
        return redirect(url_for('forum'))
    
    # Get replies - FIXED to work with both students and admins
    cursor.execute('''
        SELECT r.reply_id, r.content, COALESCE(r.upvotes, 0) as upvotes, r.created_at, 
               COALESCE(s.name, u.name) as author
        FROM forum_replies r
        LEFT JOIN students s ON r.student_id = s.student_id
        LEFT JOIN student_users u ON r.student_id = u.student_id
        WHERE r.topic_id = ?
        ORDER BY r.created_at ASC
    ''', (topic_id,))
    replies = cursor.fetchall()
    
    conn.close()
    
    return render_template('forum_topic.html', topic=topic, replies=replies, topic_id=topic_id)

@app.route('/add-reply', methods=['POST'])
@login_required
def add_reply():
    topic_id = request.form.get('topic_id')
    content = request.form.get('content')
    
    if not content:
        flash('Please enter a reply', 'error')
        return redirect(url_for('forum_topic', topic_id=topic_id))
    
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO forum_replies (topic_id, student_id, content)
        VALUES (?, ?, ?)
    ''', (topic_id, current_user.id, content))
    conn.commit()
    conn.close()
    
    flash('Reply posted!', 'success')
    return redirect(url_for('forum_topic', topic_id=topic_id))

@app.route('/upvote-reply/<int:reply_id>')
@login_required
def upvote_reply(reply_id):
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE forum_replies SET upvotes = upvotes + 1 WHERE reply_id = ?", (reply_id,))
    conn.commit()
    conn.close()
    
    # Get topic_id to redirect back
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    cursor.execute("SELECT topic_id FROM forum_replies WHERE reply_id = ?", (reply_id,))
    topic_id = cursor.fetchone()[0]
    conn.close()
    
    return redirect(url_for('forum_topic', topic_id=topic_id))

@app.route('/debug-forum', methods=['GET'])
@login_required
def debug_forum():
    """Debug endpoint to check forum table structure"""
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    
    # Check table structure
    cursor.execute("PRAGMA table_info(forum_topics)")
    columns = cursor.fetchall()
    
    # Check if any topics exist
    cursor.execute("SELECT COUNT(*) FROM forum_topics")
    count = cursor.fetchone()[0]
    
    conn.close()
    
    return jsonify({
        'table_columns': columns,
        'topic_count': count,
        'current_user': {
            'id': current_user.id,
            'role': current_user.role,
            'name': current_user.name
        }
    })

# ============ FORUM LIKE/DISLIKE API ============



# Update the forum API to include user reactions



# ============ FORUM TOPICS API (UPDATED) ============
@app.route('/api/forum-topics')
@login_required
def api_forum_topics():
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    
    page = request.args.get('page', 1, type=int)
    limit = 10
    offset = (page - 1) * limit
    
    cursor.execute("SELECT COUNT(*) FROM forum_topics")
    total_topics = cursor.fetchone()[0]
    total_pages = (total_topics + limit - 1) // limit
    
    # FIXED: Use COALESCE to get author name from either table
    cursor.execute('''
        SELECT t.topic_id, t.title, t.content, t.views, t.created_at, 
               t.student_id, 
               COALESCE(s.name, u.name) as author,
               COUNT(DISTINCT r.reply_id) as reply_count,
               COALESCE(t.likes, 0) as likes,
               COALESCE(t.dislikes, 0) as dislikes
        FROM forum_topics t
        LEFT JOIN students s ON t.student_id = s.student_id
        LEFT JOIN student_users u ON t.student_id = u.student_id
        LEFT JOIN forum_replies r ON t.topic_id = r.topic_id
        GROUP BY t.topic_id
        ORDER BY t.created_at DESC
        LIMIT ? OFFSET ?
    ''', (limit, offset))
    
    topics = []
    user_id = current_user.id
    
    for row in cursor.fetchall():
        cursor.execute("SELECT reaction_type FROM topic_reactions WHERE topic_id = ? AND user_id = ?", (row[0], user_id))
        reaction = cursor.fetchone()
        user_liked = reaction and reaction[0] == 'like'
        user_disliked = reaction and reaction[0] == 'dislike'
        
        topics.append({
            'topic_id': row[0],
            'title': row[1],
            'content': row[2],
            'views': row[3],
            'created_at': row[4],
            'student_id': row[5],
            'author': row[6] or 'Unknown',
            'reply_count': row[7] or 0,
            'likes': row[8] or 0,
            'dislikes': row[9] or 0,
            'user_liked': user_liked,
            'user_disliked': user_disliked
        })
    
    conn.close()
    
    return jsonify({
        'topics': topics,
        'total_topics': total_topics,
        'total_pages': total_pages,
        'current_page': page
    })


@app.route('/api/topic/<int:topic_id>')
@login_required
def api_get_topic(topic_id):
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    
    # Update views
    cursor.execute("UPDATE forum_topics SET views = views + 1 WHERE topic_id = ?", (topic_id,))
    conn.commit()
    
    # Get topic details - FIXED to work with both students and admins
    cursor.execute('''
        SELECT t.topic_id, t.title, t.content, t.views, t.created_at, 
               t.student_id, 
               COALESCE(s.name, u.name) as author,
               COALESCE(t.likes, 0) as likes,
               COALESCE(t.dislikes, 0) as dislikes
        FROM forum_topics t
        LEFT JOIN students s ON t.student_id = s.student_id
        LEFT JOIN student_users u ON t.student_id = u.student_id
        WHERE t.topic_id = ?
    ''', (topic_id,))
    
    topic_row = cursor.fetchone()
    if not topic_row:
        conn.close()
        return jsonify({'error': 'Topic not found'}), 404
    
    # Get replies with author info - FIXED
    cursor.execute('''
        SELECT r.reply_id, r.content, r.created_at, 
               r.student_id, 
               COALESCE(s.name, u.name) as author,
               COALESCE(r.likes, 0) as likes,
               COALESCE(r.dislikes, 0) as dislikes
        FROM forum_replies r
        LEFT JOIN students s ON r.student_id = s.student_id
        LEFT JOIN student_users u ON r.student_id = u.student_id
        WHERE r.topic_id = ?
        ORDER BY r.created_at ASC
    ''', (topic_id,))
    
    user_id = current_user.id
    replies = []
    
    for row in cursor.fetchall():
        # Check if user liked/disliked this reply
        cursor.execute("SELECT reaction_type FROM reply_reactions WHERE reply_id = ? AND user_id = ?", (row[0], user_id))
        reaction = cursor.fetchone()
        user_liked = reaction and reaction[0] == 'like'
        user_disliked = reaction and reaction[0] == 'dislike'
        
        replies.append({
            'reply_id': row[0],
            'content': row[1],
            'created_at': row[2],
            'student_id': row[3],
            'author': row[4] or 'Unknown',
            'likes': row[5] or 0,
            'dislikes': row[6] or 0,
            'user_liked': user_liked,
            'user_disliked': user_disliked
        })
    
    conn.close()
    
    return jsonify({
        'topic_id': topic_row[0],
        'title': topic_row[1],
        'content': topic_row[2],
        'views': topic_row[3],
        'created_at': topic_row[4],
        'student_id': topic_row[5],
        'author': topic_row[6] or 'Unknown',
        'likes': topic_row[7] or 0,
        'dislikes': topic_row[8] or 0,
        'replies': replies
    })




@app.route('/api/dislike-topic', methods=['POST'])
@login_required
def api_dislike_topic():
    try:
        data = request.get_json()
        topic_id = data.get('topic_id')
        user_id = current_user.id
        
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        
        # Check existing reaction
        cursor.execute("SELECT reaction_type FROM topic_reactions WHERE topic_id = ? AND user_id = ?", (topic_id, user_id))
        existing = cursor.fetchone()
        
        if existing:
            if existing[0] == 'dislike':
                # Remove dislike
                cursor.execute("DELETE FROM topic_reactions WHERE topic_id = ? AND user_id = ?", (topic_id, user_id))
                cursor.execute("UPDATE forum_topics SET dislikes = dislikes - 1 WHERE topic_id = ?", (topic_id,))
                print(f"Removed dislike from topic {topic_id}")
            elif existing[0] == 'like':
                # Change like to dislike
                cursor.execute("UPDATE topic_reactions SET reaction_type = 'dislike' WHERE topic_id = ? AND user_id = ?", (topic_id, user_id))
                cursor.execute("UPDATE forum_topics SET likes = likes - 1, dislikes = dislikes + 1 WHERE topic_id = ?", (topic_id,))
                print(f"Changed like to dislike on topic {topic_id}")
        else:
            # Add new dislike
            cursor.execute("INSERT INTO topic_reactions (topic_id, user_id, reaction_type) VALUES (?, ?, 'dislike')", (topic_id, user_id))
            cursor.execute("UPDATE forum_topics SET dislikes = dislikes + 1 WHERE topic_id = ?", (topic_id,))
            print(f"Added dislike to topic {topic_id}")
        
        conn.commit()
        
        # Get updated counts
        cursor.execute("SELECT likes, dislikes FROM forum_topics WHERE topic_id = ?", (topic_id,))
        result = cursor.fetchone()
        likes = result[0] if result else 0
        dislikes = result[1] if result else 0
        conn.close()
        
        return jsonify({'success': True, 'likes': likes, 'dislikes': dislikes})
    except Exception as e:
        print(f"Error in dislike-topic: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ============ UPDATED FORUM TOPICS API WITH NOTIFICATIONS ============

@app.route('/api/create-topic', methods=['POST'])
@login_required
def api_create_topic():
    try:
        data = request.get_json()
        title = data.get('title')
        content = data.get('content')
        
        if not title or not content:
            return jsonify({'success': False, 'error': 'Title and content are required'})
        
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        
        # Get student_id - works for both regular students and admin/teacher
        if current_user.role == 'student':
            student_id = current_user.id
        else:
            student_id = current_user.id
        
        # Ensure the user exists in student_users table
        cursor.execute("SELECT student_id FROM student_users WHERE student_id = ?", (student_id,))
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO student_users (student_id, name, email, password)
                VALUES (?, ?, ?, ?)
            ''', (student_id, current_user.name, f"{student_id}@nexuslearn.com", "dummy123"))
        
        cursor.execute('''
            INSERT INTO forum_topics (student_id, title, content)
            VALUES (?, ?, ?)
        ''', (student_id, title, content))
        
        topic_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'topic_id': topic_id})
    except Exception as e:
        print(f"Error creating topic: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/add-reply', methods=['POST'])
@login_required
def api_add_reply():
    try:
        data = request.get_json()
        topic_id = data.get('topic_id')
        content = data.get('content')
        
        if not content:
            return jsonify({'success': False, 'error': 'Content is required'})
        
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        
        # Get topic info to know who to notify
        cursor.execute("SELECT student_id, title FROM forum_topics WHERE topic_id = ?", (topic_id,))
        topic = cursor.fetchone()
        if not topic:
            conn.close()
            return jsonify({'success': False, 'error': 'Topic not found'})
        
        topic_author_id = topic[0]
        topic_title = topic[1]
        
        # Get student_id for current user
        if current_user.role == 'student':
            student_id = current_user.id
        else:
            student_id = current_user.id
        
        # Ensure the user exists
        cursor.execute("SELECT student_id FROM student_users WHERE student_id = ?", (student_id,))
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO student_users (student_id, name, email, password)
                VALUES (?, ?, ?, ?)
            ''', (student_id, current_user.name, f"{student_id}@nexuslearn.com", "dummy123"))
        
        cursor.execute('''
            INSERT INTO forum_replies (topic_id, student_id, content)
            VALUES (?, ?, ?)
        ''', (topic_id, student_id, content))
        
        reply_id = cursor.lastrowid
        conn.commit()
        
        # Send notification to topic author (if not replying to own topic)
        if topic_author_id != student_id:
            send_forum_notification(
                topic_author_id,
                'reply',
                f'New reply on "{topic_title[:50]}"',
                f'{current_user.name} replied to your discussion: "{content[:100]}"',
                f'/forum/topic/{topic_id}'
            )
        
        conn.close()
        
        return jsonify({'success': True, 'reply_id': reply_id})
    except Exception as e:
        print(f"Error adding reply: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/like-topic', methods=['POST'])
@login_required
def api_like_topic():
    try:
        data = request.get_json()
        topic_id = data.get('topic_id')
        user_id = current_user.id
        
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        
        # Get topic author for notification
        cursor.execute("SELECT student_id, title FROM forum_topics WHERE topic_id = ?", (topic_id,))
        topic = cursor.fetchone()
        if not topic:
            conn.close()
            return jsonify({'success': False, 'error': 'Topic not found'})
        
        topic_author_id = topic[0]
        topic_title = topic[1]
        
        # Check existing reaction
        cursor.execute("SELECT reaction_type FROM topic_reactions WHERE topic_id = ? AND user_id = ?", (topic_id, user_id))
        existing = cursor.fetchone()
        
        notification_sent = False
        
        if existing:
            if existing[0] == 'like':
                # Remove like
                cursor.execute("DELETE FROM topic_reactions WHERE topic_id = ? AND user_id = ?", (topic_id, user_id))
                cursor.execute("UPDATE forum_topics SET likes = likes - 1 WHERE topic_id = ?", (topic_id,))
            elif existing[0] == 'dislike':
                # Change dislike to like
                cursor.execute("UPDATE topic_reactions SET reaction_type = 'like' WHERE topic_id = ? AND user_id = ?", (topic_id, user_id))
                cursor.execute("UPDATE forum_topics SET likes = likes + 1, dislikes = dislikes - 1 WHERE topic_id = ?", (topic_id,))
                # Send notification for like (when changing from dislike)
                if topic_author_id != user_id:
                    send_forum_notification(
                        topic_author_id,
                        'like',
                        f'Someone liked your topic "{topic_title[:50]}"',
                        f'{current_user.name} liked your discussion',
                        f'/forum/topic/{topic_id}'
                    )
                    notification_sent = True
        else:
            # Add new like
            cursor.execute("INSERT INTO topic_reactions (topic_id, user_id, reaction_type) VALUES (?, ?, 'like')", (topic_id, user_id))
            cursor.execute("UPDATE forum_topics SET likes = likes + 1 WHERE topic_id = ?", (topic_id,))
            # Send notification for new like
            if topic_author_id != user_id:
                send_forum_notification(
                    topic_author_id,
                    'like',
                    f'Someone liked your topic "{topic_title[:50]}"',
                    f'{current_user.name} liked your discussion',
                    f'/forum/topic/{topic_id}'
                )
                notification_sent = True
        
        conn.commit()
        
        # Get updated counts
        cursor.execute("SELECT likes, dislikes FROM forum_topics WHERE topic_id = ?", (topic_id,))
        result = cursor.fetchone()
        likes = result[0] if result else 0
        dislikes = result[1] if result else 0
        conn.close()
        
        return jsonify({'success': True, 'likes': likes, 'dislikes': dislikes})
    except Exception as e:
        print(f"Error in like-topic: {e}")
        return jsonify({'success': False, 'error': str(e)})


# ============ NOTIFICATION API ENDPOINTS ============

@app.route('/api/forum-notifications')
@login_required
def api_forum_notifications():
    """Get notifications for current user"""
    try:
        user_id = current_user.id
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, notification_type, title, message, link, is_read, created_at
            FROM forum_notifications
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 50
        ''', (user_id,))
        
        notifications = []
        for row in cursor.fetchall():
            notifications.append({
                'id': row[0],
                'type': row[1],
                'title': row[2],
                'message': row[3],
                'link': row[4],
                'is_read': row[5],
                'created_at': row[6]
            })
        
        conn.close()
        return jsonify({'notifications': notifications})
    except Exception as e:
        return jsonify({'notifications': [], 'error': str(e)})


@app.route('/api/forum-notification-count')
@login_required
def api_forum_notification_count():
    """Get unread notification count"""
    try:
        user_id = current_user.id
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM forum_notifications WHERE user_id = ? AND is_read = 0", (user_id,))
        count = cursor.fetchone()[0]
        conn.close()
        return jsonify({'count': count})
    except:
        return jsonify({'count': 0})




@app.route('/api/dislike-reply', methods=['POST'])
@login_required
def api_dislike_reply():
    try:
        data = request.get_json()
        reply_id = data.get('reply_id')
        user_id = current_user.id
        
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT reaction_type FROM reply_reactions WHERE reply_id = ? AND user_id = ?", (reply_id, user_id))
        existing = cursor.fetchone()
        
        if existing:
            if existing[0] == 'dislike':
                cursor.execute("DELETE FROM reply_reactions WHERE reply_id = ? AND user_id = ?", (reply_id, user_id))
                cursor.execute("UPDATE forum_replies SET dislikes = dislikes - 1 WHERE reply_id = ?", (reply_id,))
            elif existing[0] == 'like':
                cursor.execute("UPDATE reply_reactions SET reaction_type = 'dislike' WHERE reply_id = ? AND user_id = ?", (reply_id, user_id))
                cursor.execute("UPDATE forum_replies SET likes = likes - 1, dislikes = dislikes + 1 WHERE reply_id = ?", (reply_id,))
        else:
            cursor.execute("INSERT INTO reply_reactions (reply_id, user_id, reaction_type) VALUES (?, ?, 'dislike')", (reply_id, user_id))
            cursor.execute("UPDATE forum_replies SET dislikes = dislikes + 1 WHERE reply_id = ?", (reply_id,))
        
        conn.commit()
        cursor.execute("SELECT likes, dislikes FROM forum_replies WHERE reply_id = ?", (reply_id,))
        result = cursor.fetchone()
        likes = result[0] if result else 0
        dislikes = result[1] if result else 0
        conn.close()
        
        return jsonify({'success': True, 'likes': likes, 'dislikes': dislikes})
    except Exception as e:
        print(f"Error in dislike-reply: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ============ NOTIFICATION SYSTEM (UPDATED FOR FORUM) ============

def send_forum_notification(user_id, notification_type, title, message, link=None):
    """Send a notification to a user"""
    try:
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        
        # Check if forum_notifications table exists, if not create it
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='forum_notifications'")
        if not cursor.fetchone():
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS forum_notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    notification_type TEXT,
                    title TEXT,
                    message TEXT,
                    link TEXT,
                    is_read INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
        
        cursor.execute('''
            INSERT INTO forum_notifications (user_id, notification_type, title, message, link)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, notification_type, title, message, link))
        
        conn.commit()
        conn.close()
        
        # Also emit via Socket.IO for real-time notification
        try:
            socketio.emit('new_forum_notification', {
                'title': title,
                'message': message,
                'type': notification_type
            }, room=f'user_{user_id}')
        except:
            pass
            
        return True
    except Exception as e:
        print(f"Error sending notification: {e}")
        return False




@app.route('/api/mark-forum-notification-read', methods=['POST'])
@login_required
def api_mark_forum_notification_read():
    """Mark a notification as read"""
    try:
        data = request.get_json()
        notification_id = data.get('notification_id')
        user_id = current_user.id
        
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE forum_notifications SET is_read = 1 WHERE id = ? AND user_id = ?", (notification_id, user_id))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/mark-all-forum-notifications-read', methods=['POST'])
@login_required
def api_mark_all_forum_notifications_read():
    """Mark all notifications as read"""
    try:
        user_id = current_user.id
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE forum_notifications SET is_read = 1 WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/debug-topics')
@login_required
def debug_topics():
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM forum_topics")
    count = cursor.fetchone()[0]
    
    cursor.execute("SELECT topic_id, title, student_id FROM forum_topics")
    topics = cursor.fetchall()
    
    conn.close()
    
    return jsonify({
        'total_topics': count,
        'topics': [{'id': t[0], 'title': t[1], 'student_id': t[2]} for t in topics],
        'current_user': {
            'id': current_user.id,
            'role': current_user.role,
            'name': current_user.name
        }
    })

# ============ UNIFIED NOTIFICATION SYSTEM ============

def send_unified_notification(user_id, notification_type, title, message, icon=None, link=None):
    """Send a unified notification to a user"""
    try:
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        
        # Set default icon based on type
        if not icon:
            icons = {
                'achievement': 'fa-trophy',
                'badge': 'fa-medal',
                'certificate': 'fa-certificate',
                'reply': 'fa-comment',
                'like': 'fa-heart',
                'forum': 'fa-comments',
                'quiz': 'fa-question-circle',
                'meeting': 'fa-calendar',
                'points': 'fa-star'
            }
            icon = icons.get(notification_type, 'fa-bell')
        
        cursor.execute('''
            INSERT INTO unified_notifications (user_id, notification_type, title, message, icon, link)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, notification_type, title, message, icon, link))
        
        conn.commit()
        conn.close()
        
        # Emit via Socket.IO for real-time
        try:
            socketio.emit('new_unified_notification', {
                'title': title,
                'message': message,
                'type': notification_type,
                'icon': icon
            }, room=f'user_{user_id}')
        except:
            pass
            
        return True
    except Exception as e:
        print(f"Error sending notification: {e}")
        return False


@app.route('/api/unified-notifications')
@login_required
def api_unified_notifications():
    """Get all notifications for current user"""
    try:
        user_id = current_user.id
        limit = request.args.get('limit', 50, type=int)
        
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, notification_type, title, message, icon, link, is_read, created_at
            FROM unified_notifications
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (user_id, limit))
        
        notifications = []
        for row in cursor.fetchall():
            notifications.append({
                'id': row[0],
                'type': row[1],
                'title': row[2],
                'message': row[3],
                'icon': row[4] or 'fa-bell',
                'link': row[5],
                'is_read': row[6],
                'created_at': row[7]
            })
        
        # Get unread count
        cursor.execute("SELECT COUNT(*) FROM unified_notifications WHERE user_id = ? AND is_read = 0", (user_id,))
        unread_count = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'notifications': notifications,
            'unread_count': unread_count
        })
    except Exception as e:
        print(f"Error in unified-notifications: {e}")
        return jsonify({'notifications': [], 'unread_count': 0})


@app.route('/api/unified-notifications/mark-read', methods=['POST'])
@login_required
def api_unified_mark_read():
    """Mark a notification as read"""
    try:
        data = request.get_json()
        notification_id = data.get('notification_id')
        user_id = current_user.id
        
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE unified_notifications SET is_read = 1 WHERE id = ? AND user_id = ?", (notification_id, user_id))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/unified-notifications/mark-all-read', methods=['POST'])
@login_required
def api_unified_mark_all_read():
    """Mark all notifications as read"""
    try:
        user_id = current_user.id
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE unified_notifications SET is_read = 1 WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/test-answer', methods=['GET'])
@login_required
def test_answer():
    return jsonify({
        'status': 'working',
        'user_role': current_user.role,
        'user_id': current_user.id
    })

@app.route('/test-doubt')
@login_required
def test_doubt():
    return render_template('test_doubt.html')

# ============ ENHANCED DOUBT API ENDPOINTS ============

@app.route('/api/doubts/enhanced')
@login_required
def api_get_enhanced_doubts():
    """Get doubts with categories, upvotes, filters"""
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    
    # Get filter parameters
    category = request.args.get('category', 'all')
    priority = request.args.get('priority', 'all')
    sort_by = request.args.get('sort', 'latest')
    
    # Build query
    query = '''
        SELECT 
            d.doubt_id, d.student_id, 
            COALESCE(s.name, u.name, 'Unknown') as student_name,
            d.question, d.ai_answer, d.teacher_answer, 
            d.status, d.created_at, d.resolved_at,
            d.category, d.priority, d.image_url, d.tags,
            COALESCE(d.response_time, 0) as response_time,
            COALESCE(l.likes, 0) as likes,
            COALESCE(dis.dislikes, 0) as dislikes,
            c.icon as category_icon,
            c.color as category_color
        FROM doubts d
        LEFT JOIN students s ON d.student_id = s.student_id
        LEFT JOIN student_users u ON d.student_id = u.student_id
        LEFT JOIN (
            SELECT doubt_id, COUNT(*) as likes FROM doubt_upvotes WHERE vote_type = 'like' GROUP BY doubt_id
        ) l ON d.doubt_id = l.doubt_id
        LEFT JOIN (
            SELECT doubt_id, COUNT(*) as dislikes FROM doubt_upvotes WHERE vote_type = 'dislike' GROUP BY doubt_id
        ) dis ON d.doubt_id = dis.doubt_id
        LEFT JOIN doubt_categories c ON d.category = c.name
        WHERE 1=1
    '''
    
    params = []
    
    if category != 'all':
        query += " AND d.category = ?"
        params.append(category)
    
    if priority != 'all':
        query += " AND d.priority = ?"
        params.append(priority)
    
    # Sorting
    if sort_by == 'latest':
        query += " ORDER BY d.created_at DESC"
    elif sort_by == 'popular':
        query += " ORDER BY likes DESC"
    elif sort_by == 'unanswered':
        query += " ORDER BY CASE WHEN d.status = 'pending' THEN 0 ELSE 1 END, d.created_at DESC"
    else:
        query += " ORDER BY d.created_at DESC"
    
    if current_user.role != 'admin' and current_user.role != 'teacher':
        query += " LIMIT 100"
    
    cursor.execute(query, params)
    
    doubts = []
    for row in cursor.fetchall():
        doubts.append({
            'doubt_id': row[0],
            'student_id': row[1],
            'student_name': row[2],
            'question': row[3],
            'ai_answer': row[4],
            'teacher_answer': row[5],
            'status': row[6],
            'created_at': row[7],
            'resolved_at': row[8],
            'category': row[9] or 'General',
            'priority': row[10] or 'normal',
            'image_url': row[11],
            'tags': row[12].split(',') if row[12] else [],
            'response_time': row[13],
            'likes': row[14] or 0,
            'dislikes': row[15] or 0,
            'category_icon': row[16] or 'fa-question-circle',
            'category_color': row[17] or '#6b6b6b'
        })
    
    conn.close()
    return jsonify(doubts)


@app.route('/api/doubt/upvote', methods=['POST'])
@login_required
def api_doubt_upvote():
    try:
        data = request.get_json()
        doubt_id = data.get('doubt_id')
        user_id = current_user.id
        
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        
        # Check existing vote
        cursor.execute("SELECT vote_type FROM doubt_upvotes WHERE doubt_id = ? AND user_id = ?", (doubt_id, user_id))
        existing = cursor.fetchone()
        
        if existing:
            if existing[0] == 'like':
                cursor.execute("DELETE FROM doubt_upvotes WHERE doubt_id = ? AND user_id = ?", (doubt_id, user_id))
            else:
                cursor.execute("UPDATE doubt_upvotes SET vote_type = 'like' WHERE doubt_id = ? AND user_id = ?", (doubt_id, user_id))
        else:
            cursor.execute("INSERT INTO doubt_upvotes (doubt_id, user_id, vote_type) VALUES (?, ?, 'like')", (doubt_id, user_id))
        
        conn.commit()
        
        # Get updated counts
        cursor.execute("SELECT COUNT(*) FROM doubt_upvotes WHERE doubt_id = ? AND vote_type = 'like'", (doubt_id,))
        likes = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM doubt_upvotes WHERE doubt_id = ? AND vote_type = 'dislike'", (doubt_id,))
        dislikes = cursor.fetchone()[0]
        
        conn.close()
        return jsonify({'success': True, 'likes': likes, 'dislikes': dislikes})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/doubt/dislike', methods=['POST'])
@login_required
def api_doubt_dislike():
    try:
        data = request.get_json()
        doubt_id = data.get('doubt_id')
        user_id = current_user.id
        
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT vote_type FROM doubt_upvotes WHERE doubt_id = ? AND user_id = ?", (doubt_id, user_id))
        existing = cursor.fetchone()
        
        if existing:
            if existing[0] == 'dislike':
                cursor.execute("DELETE FROM doubt_upvotes WHERE doubt_id = ? AND user_id = ?", (doubt_id, user_id))
            else:
                cursor.execute("UPDATE doubt_upvotes SET vote_type = 'dislike' WHERE doubt_id = ? AND user_id = ?", (doubt_id, user_id))
        else:
            cursor.execute("INSERT INTO doubt_upvotes (doubt_id, user_id, vote_type) VALUES (?, ?, 'dislike')", (doubt_id, user_id))
        
        conn.commit()
        
        cursor.execute("SELECT COUNT(*) FROM doubt_upvotes WHERE doubt_id = ? AND vote_type = 'like'", (doubt_id,))
        likes = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM doubt_upvotes WHERE doubt_id = ? AND vote_type = 'dislike'", (doubt_id,))
        dislikes = cursor.fetchone()[0]
        
        conn.close()
        return jsonify({'success': True, 'likes': likes, 'dislikes': dislikes})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/doubt/categories')
@login_required
def api_doubt_categories():
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name, icon, color FROM doubt_categories ORDER BY name")
    categories = [{'name': row[0], 'icon': row[1], 'color': row[2]} for row in cursor.fetchall()]
    conn.close()
    return jsonify(categories)


@app.route('/api/doubt/analytics')
@login_required
def api_doubt_analytics():
    """Get analytics for teacher dashboard"""
    if current_user.role != 'admin' and current_user.role != 'teacher':
        return jsonify({'error': 'Unauthorized'}), 403
    
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    
    # Total doubts
    cursor.execute("SELECT COUNT(*) FROM doubts")
    total = cursor.fetchone()[0]
    
    # Resolved vs Pending
    cursor.execute("SELECT COUNT(*) FROM doubts WHERE status = 'resolved'")
    resolved = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM doubts WHERE status = 'pending' OR status = 'ai_answered'")
    pending = cursor.fetchone()[0]
    
    # Average response time (in minutes)
    cursor.execute("SELECT AVG(response_time) FROM doubts WHERE response_time > 0")
    avg_response = cursor.fetchone()[0] or 0
    
    # Doubts by category
    cursor.execute('''
        SELECT category, COUNT(*) FROM doubts GROUP BY category ORDER BY COUNT(*) DESC LIMIT 5
    ''')
    by_category = [{'category': row[0], 'count': row[1]} for row in cursor.fetchall()]
    
    # Most active students
    cursor.execute('''
        SELECT COALESCE(s.name, u.name), COUNT(*) 
        FROM doubts d
        LEFT JOIN students s ON d.student_id = s.student_id
        LEFT JOIN student_users u ON d.student_id = u.student_id
        GROUP BY d.student_id
        ORDER BY COUNT(*) DESC LIMIT 5
    ''')
    top_students = [{'name': row[0] or 'Unknown', 'count': row[1]} for row in cursor.fetchall()]
    
    conn.close()
    
    return jsonify({
        'total': total,
        'resolved': resolved,
        'pending': pending,
        'resolution_rate': round((resolved / total * 100), 1) if total > 0 else 0,
        'avg_response_time': round(avg_response / 60, 1),  # Convert to hours
        'by_category': by_category,
        'top_students': top_students
    })


@app.route('/api/ask-doubt-enhanced', methods=['POST'])
@login_required
def api_ask_doubt_enhanced():
    try:
        data = request.get_json()
        question = data.get('question')
        category = data.get('category', 'General')
        priority = data.get('priority', 'normal')
        tags = data.get('tags', '')
        
        if not question:
            return jsonify({'success': False, 'error': 'Question is required'})
        
        # Get AI answer
        completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are an expert tutor. Provide clear, concise, and helpful answers to student questions. Keep answers educational and easy to understand."},
                {"role": "user", "content": question}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        ai_answer = completion.choices[0].message.content
        
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        
        # Get student_id
        if current_user.role == 'student':
            student_id = current_user.id
        else:
            student_id = current_user.id
        
        cursor.execute('''
            INSERT INTO doubts (student_id, question, ai_answer, status, category, priority, tags)
            VALUES (?, ?, ?, 'ai_answered', ?, ?, ?)
        ''', (student_id, question, ai_answer, category, priority, tags))
        
        doubt_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Notify teachers (optional)
        # send_notification_to_teachers('New doubt posted', question[:100])
        
        return jsonify({'success': True, 'answer': ai_answer, 'doubt_id': doubt_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ============ PARENT COMMUNICATION API ============

@app.route('/api/school-authorities')
@login_required
def api_school_authorities():
    """Get list of school authorities"""
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, designation, department, email, phone FROM school_authorities WHERE is_active = 1")
    authorities = []
    for row in cursor.fetchall():
        authorities.append({
            'id': row[0],
            'name': row[1],
            'designation': row[2],
            'department': row[3],
            'email': row[4],
            'phone': row[5]
        })
    conn.close()
    return jsonify(authorities)


@app.route('/api/send-message-to-authority', methods=['POST'])
@login_required
def api_send_message_to_authority():
    """Send message from parent to school authority"""
    try:
        data = request.get_json()
        
        # Get parent and student info
        parent_name = current_user.name
        parent_id = current_user.id
        student_id = current_user.student_id if hasattr(current_user, 'student_id') else None
        
        # Get student name
        student_name = ''
        if student_id:
            conn = sqlite3.connect('database/students.db')
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM students WHERE student_id = ?", (student_id,))
            student = cursor.fetchone()
            student_name = student[0] if student else ''
            conn.close()
        
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO parent_messages (parent_id, parent_name, student_id, student_name, recipient_type, recipient_name, subject, message, priority)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            parent_id,
            parent_name,
            student_id,
            student_name,
            data['recipient_type'],
            data['recipient_name'],
            data['subject'],
            data['message'],
            data.get('priority', 'normal')
        ))
        
        msg_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Send notification to admin about new message
        send_unified_notification(
            'admin',
            'parent_message',
            f'📨 New Message from {parent_name}',
            f'Subject: {data["subject"]} - Sent to {data["recipient_name"]}',
            'fa-envelope',
            '/admin/messages'
        )
        
        return jsonify({'success': True, 'message_id': msg_id})
        
    except Exception as e:
        print(f"Error sending message: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/parent-messages')
@login_required
def api_parent_messages():
    """Get messages for parent"""
    if current_user.role != 'parent':
        return jsonify({'error': 'Unauthorized'}), 403
    
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, recipient_type, recipient_name, subject, message, status, priority, reply_from, reply_message, replied_at, created_at
        FROM parent_messages
        WHERE parent_id = ?
        ORDER BY created_at DESC
    ''', (current_user.id,))
    
    messages = []
    for row in cursor.fetchall():
        messages.append({
            'id': row[0],
            'recipient_type': row[1],
            'recipient_name': row[2],
            'subject': row[3],
            'message': row[4],
            'status': row[5],
            'priority': row[6],
            'reply_from': row[7],
            'reply_message': row[8],
            'replied_at': row[9],
            'created_at': row[10]
        })
    conn.close()
    return jsonify(messages)


@app.route('/api/admin-messages')
@login_required
def api_admin_messages():
    """Get all messages for admin/teacher"""
    if current_user.role != 'admin' and current_user.role != 'teacher':
        return jsonify({'error': 'Unauthorized'}), 403
    
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, parent_name, student_name, recipient_type, recipient_name, subject, message, status, priority, created_at
        FROM parent_messages
        ORDER BY 
            CASE status WHEN 'unread' THEN 0 ELSE 1 END,
            created_at DESC
    ''')
    
    messages = []
    for row in cursor.fetchall():
        messages.append({
            'id': row[0],
            'parent_name': row[1],
            'student_name': row[2] or 'N/A',
            'recipient_type': row[3],
            'recipient_name': row[4],
            'subject': row[5],
            'message': row[6],
            'status': row[7],
            'priority': row[8],
            'created_at': row[9]
        })
    conn.close()
    return jsonify(messages)


@app.route('/api/reply-to-parent', methods=['POST'])
@login_required
def api_reply_to_parent():
    """Reply to parent message (admin/teacher only)"""
    if current_user.role != 'admin' and current_user.role != 'teacher':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE parent_messages 
            SET status = 'replied', 
                reply_from = ?, 
                reply_message = ?, 
                replied_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (current_user.name, data['reply'], data['message_id']))
        
        # Get parent info for notification
        cursor.execute("SELECT parent_id, parent_name, subject FROM parent_messages WHERE id = ?", (data['message_id'],))
        msg = cursor.fetchone()
        
        conn.commit()
        conn.close()
        
        # Send notification to parent
        if msg:
            send_unified_notification(
                msg[0],
                'message_reply',
                f'📨 Reply to your message',
                f'{current_user.name} replied to: {msg[2]}',
                'fa-reply',
                '/parent/communication'
            )
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/mark-message-read/<int:msg_id>', methods=['POST'])
@login_required
def api_mark_message_read(msg_id):
    """Mark message as read (admin only)"""
    if current_user.role != 'admin' and current_user.role != 'teacher':
        return jsonify({'error': 'Unauthorized'}), 403
    
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE parent_messages SET status = 'read' WHERE id = ?", (msg_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/parent/communication')
@login_required
def parent_communication():
    if current_user.role != 'parent':
        return redirect(url_for('dashboard'))
    return render_template('parent_communication.html')

@app.route('/admin/messages')
@login_required
def admin_messages():
    if current_user.role != 'admin' and current_user.role != 'teacher':
        return redirect(url_for('dashboard'))
    return render_template('admin_messages.html')

@app.route('/api/delete-parent-message/<int:msg_id>', methods=['DELETE'])
@login_required
def api_delete_parent_message(msg_id):
    """Delete a parent message (parent only)"""
    if current_user.role != 'parent':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        
        # Verify message belongs to this parent
        cursor.execute("SELECT id FROM parent_messages WHERE id = ? AND parent_id = ?", (msg_id, current_user.id))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': 'Message not found or unauthorized'})
        
        cursor.execute("DELETE FROM parent_messages WHERE id = ?", (msg_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/parent-unread-count')
@login_required
def api_parent_unread_count():
    """Get unread message count for parent"""
    if current_user.role != 'parent':
        return jsonify({'count': 0})
    
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM parent_messages WHERE parent_id = ? AND status = 'unread'", (current_user.id,))
    count = cursor.fetchone()[0]
    conn.close()
    return jsonify({'count': count})

@app.route('/parent/messages')
@login_required
def parent_messages():
    if current_user.role != 'parent':
        return redirect(url_for('dashboard'))
    return render_template('parent_messages.html')

@app.route('/api/get-parent-credentials/<student_id>')
@login_required
def get_parent_credentials(student_id):
    """Get parent credentials for a student (admin only)"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    cursor.execute("SELECT parent_email, parent_password FROM student_users WHERE student_id = ?", (student_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return jsonify({
            'success': True,
            'parent_email': result[0],
            'parent_password': result[1]
        })
    return jsonify({'success': False, 'error': 'Student not found'})

@app.route('/api/student-credentials/<student_id>')
@login_required
def api_student_credentials(student_id):
    """Get student and parent login credentials (admin only)"""
    if current_user.role != 'admin' and current_user.role != 'teacher':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        
        # Get student info and credentials
        cursor.execute("""
            SELECT s.name, u.email, u.password, u.parent_email, u.parent_password
            FROM students s
            LEFT JOIN student_users u ON s.student_id = u.student_id
            WHERE s.student_id = ?
        """, (student_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            # Check if credentials exist, if not generate them
            if not result[2]:  # No password found
                # Generate credentials
                student_password = f"{student_id.lower()}123"
                student_email = f"{result[0].lower().replace(' ', '.')}@student.com"
                parent_email = f"parent.{student_id.lower()}@example.com"
                parent_password = f"parent{student_id[1:]}123"
                
                # Insert into database
                conn2 = sqlite3.connect('database/students.db')
                cursor2 = conn2.cursor()
                cursor2.execute('''
                    INSERT OR REPLACE INTO student_users 
                    (student_id, name, email, password, parent_email, parent_password)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (student_id, result[0], student_email, student_password, parent_email, parent_password))
                conn2.commit()
                conn2.close()
                
                return jsonify({
                    'success': True,
                    'student_id': student_id,
                    'student_name': result[0],
                    'student_email': student_email,
                    'student_password': student_password,
                    'parent_email': parent_email,
                    'parent_password': parent_password
                })
            else:
                return jsonify({
                    'success': True,
                    'student_id': student_id,
                    'student_name': result[0],
                    'student_email': result[1] or f"{result[0].lower().replace(' ', '.')}@student.com",
                    'student_password': result[2],
                    'parent_email': result[3] or f"parent.{student_id.lower()}@example.com",
                    'parent_password': result[4] or f"parent{student_id[1:]}123"
                })
        else:
            return jsonify({'success': False, 'error': 'Student not found'})
            
    except Exception as e:
        print(f"Error in student-credentials: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/test-credentials/<student_id>')
@login_required
def test_credentials(student_id):
    """Test endpoint to check credentials"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    
    # Check if student exists
    cursor.execute("SELECT student_id, name FROM students WHERE student_id = ?", (student_id,))
    student = cursor.fetchone()
    
    # Check if user exists in student_users
    cursor.execute("SELECT * FROM student_users WHERE student_id = ?", (student_id,))
    user = cursor.fetchone()
    
    conn.close()
    
    return jsonify({
        'student_exists': student is not None,
        'student_data': student,
        'user_exists': user is not None,
        'user_data': user
    })

@app.template_filter('local_time')
def local_time_filter(timestamp):
    """Convert UTC timestamp to IST"""
    if timestamp:
        try:
            # Parse the timestamp
            if isinstance(timestamp, str):
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                dt = timestamp
            # Convert to IST
            ist = pytz.timezone('Asia/Kolkata')
            if dt.tzinfo is None:
                dt = pytz.UTC.localize(dt)
            local_dt = dt.astimezone(ist)
            return local_dt.strftime('%Y-%m-%d %I:%M:%S %p')
        except:
            return str(timestamp)
    return ''

@app.route('/time-test')
def time_test():
    return render_template('time_test.html')

import pytz
from datetime import datetime

@app.route('/api/activity-logs')
@login_required
def api_activity_logs():
    """Get user activity logs (admin only)"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        
        limit = request.args.get('limit', 500, type=int)
        search = request.args.get('search', '')
        role_filter = request.args.get('role', '')
        date_filter = request.args.get('date', '')
        
        query = """
            SELECT id, user_id, user_name, user_role, action, details, ip_address, created_at 
            FROM activity_logs 
            WHERE 1=1
        """
        params = []
        
        if search:
            query += " AND (user_name LIKE ? OR action LIKE ? OR details LIKE ?)"
            params.extend([f'%{search}%', f'%{search}%', f'%{search}%'])
        
        if role_filter:
            query += " AND user_role = ?"
            params.append(role_filter)
        
        if date_filter:
            query += " AND DATE(created_at) = ?"
            params.append(date_filter)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        
        # Set IST timezone
        ist = pytz.timezone('Asia/Kolkata')
        
        logs = []
        for row in cursor.fetchall():
            # Convert created_at to IST
            created_at = row[7]
            if created_at:
                try:
                    # Parse the timestamp
                    if isinstance(created_at, str):
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    else:
                        dt = created_at
                    
                    # Add UTC timezone if naive
                    if dt.tzinfo is None:
                        dt = pytz.UTC.localize(dt)
                    
                    # Convert to IST
                    dt_ist = dt.astimezone(ist)
                    created_at_ist = dt_ist.strftime('%Y-%m-%d %I:%M:%S %p')
                except:
                    created_at_ist = str(created_at)
            else:
                created_at_ist = ''
            
            logs.append({
                'id': row[0],
                'user_id': row[1],
                'user_name': row[2],
                'user_role': row[3],
                'action': row[4],
                'details': row[5] if row[5] else '',
                'ip_address': row[6],
                'created_at': created_at_ist
            })
        
        conn.close()
        return jsonify(logs)
        
    except Exception as e:
        print(f"Error in activity-logs: {e}")
        return jsonify([])


# ============ ACTIVITY LOGGING HELPER ============

def log_user_activity(action, details=None):
    """Automatically log user activity"""
    try:
        if not current_user.is_authenticated:
            return
        
        conn = sqlite3.connect('database/students.db')
        cursor = conn.cursor()
        
        # Get user info
        user_id = current_user.id
        user_name = current_user.name
        user_role = current_user.role
        
        # Get IP address
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr) if request else 'unknown'
        
        # Get user agent
        user_agent = request.headers.get('User-Agent', 'unknown') if request else 'unknown'
        
        cursor.execute('''
            INSERT INTO activity_logs (user_id, user_name, user_role, action, details, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, user_name, user_role, action, details, ip_address, user_agent[:200]))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error logging activity: {e}")



if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 STUDENT PERFORMANCE DASHBOARD")
    print("="*60)
    print("\n📍 Access at: http://127.0.0.1:5000")
    print("\n🔐 Login Credentials:")
    print("   Admin:     admin / admin123")
    print("   Student:   S0001 / john123")
    print("   Parent:    parent1@example.com / john123")
    print("\n" + "="*60)
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)