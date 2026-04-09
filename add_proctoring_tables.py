import sqlite3

conn = sqlite3.connect('database/students.db')
cursor = conn.cursor()

# Create proctoring sessions table
cursor.execute('''
CREATE TABLE IF NOT EXISTS proctoring_sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT,
    quiz_id INTEGER,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    status TEXT DEFAULT 'active',
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (quiz_id) REFERENCES quizzes(quiz_id)
)
''')

# Create proctoring logs table
cursor.execute('''
CREATE TABLE IF NOT EXISTS proctoring_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER,
    event_type TEXT,
    event_data TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES proctoring_sessions(session_id)
)
''')

# Create proctoring violations table
cursor.execute('''
CREATE TABLE IF NOT EXISTS proctoring_violations (
    violation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER,
    student_id TEXT,
    violation_type TEXT,
    severity INTEGER DEFAULT 1,
    details TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES proctoring_sessions(session_id),
    FOREIGN KEY (student_id) REFERENCES students(student_id)
)
''')

print("✅ Proctoring tables created!")
conn.commit()
conn.close()