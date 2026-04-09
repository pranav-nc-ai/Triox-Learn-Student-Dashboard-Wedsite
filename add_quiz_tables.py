import sqlite3

conn = sqlite3.connect('database/students.db')
cursor = conn.cursor()

# Create quizzes table
cursor.execute('''
CREATE TABLE IF NOT EXISTS quizzes (
    quiz_id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_by TEXT,
    title TEXT,
    description TEXT,
    time_limit INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES students(student_id)
)
''')

# Create questions table
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
    points INTEGER DEFAULT 1,
    FOREIGN KEY (quiz_id) REFERENCES quizzes(quiz_id)
)
''')

# Create quiz results table
cursor.execute('''
CREATE TABLE IF NOT EXISTS quiz_results (
    result_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT,
    quiz_id INTEGER,
    score INTEGER,
    total_possible INTEGER,
    percentage REAL,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (quiz_id) REFERENCES quizzes(quiz_id)
)
''')

# Create parent-teacher meetings table
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (teacher_id) REFERENCES students(student_id),
    FOREIGN KEY (student_id) REFERENCES students(student_id)
)
''')

# Create certificates table
cursor.execute('''
CREATE TABLE IF NOT EXISTS certificates (
    certificate_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT,
    certificate_type TEXT,
    issue_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    file_path TEXT,
    verified TEXT DEFAULT 'pending',
    FOREIGN KEY (student_id) REFERENCES students(student_id)
)
''')

# Create forum topics table
cursor.execute('''
CREATE TABLE IF NOT EXISTS forum_topics (
    topic_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT,
    title TEXT,
    content TEXT,
    views INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(student_id)
)
''')

# Create forum replies table
cursor.execute('''
CREATE TABLE IF NOT EXISTS forum_replies (
    reply_id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER,
    student_id TEXT,
    content TEXT,
    upvotes INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (topic_id) REFERENCES forum_topics(topic_id),
    FOREIGN KEY (student_id) REFERENCES students(student_id)
)
''')

conn.commit()
conn.close()
print("✅ Quiz, Meetings, Certificates, Forum tables created!")