import sqlite3

conn = sqlite3.connect('database/students.db')
cursor = conn.cursor()

# Create forum_notifications table
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
print("✅ Created forum_notifications table")

# Add index for faster queries
cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_user ON forum_notifications(user_id)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_read ON forum_notifications(is_read)")
print("✅ Added indexes")

conn.commit()
conn.close()
print("\n🎉 Notification system ready!")