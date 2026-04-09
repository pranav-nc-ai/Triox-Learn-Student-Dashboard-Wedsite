import sqlite3

conn = sqlite3.connect('database/students.db')
cursor = conn.cursor()

# Create messages table
cursor.execute('''
CREATE TABLE IF NOT EXISTS parent_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_id TEXT,
    parent_name TEXT,
    student_id TEXT,
    student_name TEXT,
    recipient_type TEXT,
    recipient_name TEXT,
    subject TEXT,
    message TEXT,
    status TEXT DEFAULT 'unread',
    priority TEXT DEFAULT 'normal',
    reply_from TEXT,
    reply_message TEXT,
    replied_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')
print("✅ Created parent_messages table")

# Create authorities list table
cursor.execute('''
CREATE TABLE IF NOT EXISTS school_authorities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    designation TEXT,
    department TEXT,
    email TEXT,
    phone TEXT,
    is_active INTEGER DEFAULT 1
)
''')
print("✅ Created school_authorities table")

# Insert default authorities
authorities = [
    ('Dr. Sarah Johnson', 'Principal', 'Administration', 'principal@nexuslearn.com', '+1-555-0101'),
    ('Prof. Michael Chen', 'Vice Principal', 'Academics', 'vp@nexuslearn.com', '+1-555-0102'),
    ('Ms. Emily Davis', 'Head of Academics', 'Academics', 'academics@nexuslearn.com', '+1-555-0103'),
    ('Mr. Robert Wilson', 'Class Teacher Coordinator', 'Teaching', 'teacher.coordinator@nexuslearn.com', '+1-555-0104'),
    ('Dr. Lisa Anderson', 'Counselor', 'Student Welfare', 'counselor@nexuslearn.com', '+1-555-0105'),
    ('Mr. James Taylor', 'Sports Coordinator', 'Sports', 'sports@nexuslearn.com', '+1-555-0106'),
    ('Ms. Maria Garcia', 'Parent Relations', 'Parent Support', 'parentrelations@nexuslearn.com', '+1-555-0107'),
]

for auth in authorities:
    cursor.execute('''
        INSERT OR IGNORE INTO school_authorities (name, designation, department, email, phone)
        VALUES (?, ?, ?, ?, ?)
    ''', auth)

conn.commit()

# Verify
cursor.execute("SELECT COUNT(*) FROM parent_messages")
msg_count = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM school_authorities")
auth_count = cursor.fetchone()[0]
print(f"\n✅ Total messages: {msg_count}")
print(f"✅ Total authorities: {auth_count}")

conn.close()
print("\n🎉 Communication system ready!")