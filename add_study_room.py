import sqlite3

conn = sqlite3.connect('database/students.db')
cursor = conn.cursor()

# Create study rooms table
cursor.execute('''
CREATE TABLE IF NOT EXISTS study_rooms (
    room_id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_name TEXT,
    room_code TEXT UNIQUE,
    created_by TEXT,
    subject TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active INTEGER DEFAULT 1,
    FOREIGN KEY (created_by) REFERENCES students(student_id)
)
''')

# Create room members table
cursor.execute('''
CREATE TABLE IF NOT EXISTS room_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER,
    student_id TEXT,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP,
    FOREIGN KEY (room_id) REFERENCES study_rooms(room_id),
    FOREIGN KEY (student_id) REFERENCES students(student_id)
)
''')

# Create room messages table
cursor.execute('''
CREATE TABLE IF NOT EXISTS room_messages (
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER,
    student_id TEXT,
    message TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (room_id) REFERENCES study_rooms(room_id),
    FOREIGN KEY (student_id) REFERENCES students(student_id)
)
''')

# Create study resources table
cursor.execute('''
CREATE TABLE IF NOT EXISTS study_resources (
    resource_id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER,
    uploaded_by TEXT,
    title TEXT,
    description TEXT,
    file_url TEXT,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (room_id) REFERENCES study_rooms(room_id)
)
''')

# Create goals table
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
    completed_at TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(student_id)
)
''')

# Create goal_checkpoints table
cursor.execute('''
CREATE TABLE IF NOT EXISTS goal_checkpoints (
    checkpoint_id INTEGER PRIMARY KEY AUTOINCREMENT,
    goal_id INTEGER,
    checkpoint_title TEXT,
    is_completed INTEGER DEFAULT 0,
    completed_at TIMESTAMP,
    FOREIGN KEY (goal_id) REFERENCES student_goals(goal_id)
)
''')

conn.commit()
conn.close()
print("✅ Study Room and Goals tables created successfully!")