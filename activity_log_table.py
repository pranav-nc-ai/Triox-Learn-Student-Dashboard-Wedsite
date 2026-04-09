import sqlite3

conn = sqlite3.connect('database/students.db')
cursor = conn.cursor()

# Create activity logs table
cursor.execute('''
CREATE TABLE IF NOT EXISTS activity_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    user_name TEXT,
    user_role TEXT,
    action TEXT,
    details TEXT,
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

print("✅ Activity logs table created!")
conn.commit()
conn.close()