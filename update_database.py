import sqlite3

conn = sqlite3.connect('database/students.db')
cursor = conn.cursor()

# Create student_users table for login
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

# Add sample student logins
students = [
    ('S0001', 'John Collins', 'john@example.com', 'john123', 'parent1@example.com'),
    ('S0002', 'Emma Watson', 'emma@example.com', 'emma123', 'parent2@example.com'),
    ('S0003', 'Michael Brown', 'michael@example.com', 'michael123', 'parent3@example.com'),
    ('S0004', 'Sophia Lee', 'sophia@example.com', 'sophia123', 'parent4@example.com'),
    ('S0005', 'James Wilson', 'james@example.com', 'james123', 'parent5@example.com'),
]

for s in students:
    cursor.execute('''
    INSERT OR IGNORE INTO student_users (student_id, name, email, password, parent_email)
    VALUES (?, ?, ?, ?, ?)
    ''', s)

conn.commit()
conn.close()
print("✅ Student users table created successfully!")