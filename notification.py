import sqlite3

conn = sqlite3.connect('database/students.db')
cursor = conn.cursor()

# Create notifications table
cursor.execute('''
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    user_type TEXT,
    title TEXT,
    message TEXT,
    type TEXT,
    is_read INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    action_url TEXT,
    icon TEXT,
    FOREIGN KEY (user_id) REFERENCES students(student_id)
)
''')

print("✅ Notifications table created!")
conn.commit()
conn.close()