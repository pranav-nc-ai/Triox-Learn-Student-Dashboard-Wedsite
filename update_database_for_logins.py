import sqlite3

conn = sqlite3.connect('database/students.db')
cursor = conn.cursor()

# Ensure student_users table has all required fields
cursor.execute('''
CREATE TABLE IF NOT EXISTS student_users (
    student_id TEXT PRIMARY KEY,
    name TEXT,
    email TEXT,
    password TEXT,
    parent_email TEXT,
    parent_password TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')
print("✅ student_users table ready")

# Add parent_password column if not exists
try:
    cursor.execute("ALTER TABLE student_users ADD COLUMN parent_password TEXT")
    print("✅ Added parent_password column")
except:
    print("⚠️ parent_password column already exists")

# Add is_active column if not exists
try:
    cursor.execute("ALTER TABLE student_users ADD COLUMN is_active INTEGER DEFAULT 1")
    print("✅ Added is_active column")
except:
    print("⚠️ is_active column already exists")

conn.commit()
conn.close()
print("\n🎉 Database updated successfully!")