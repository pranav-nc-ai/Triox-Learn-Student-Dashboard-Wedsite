import sqlite3

conn = sqlite3.connect('database/students.db')
cursor = conn.cursor()

# First, check if table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='student_users'")
table_exists = cursor.fetchone()

if not table_exists:
    print("Creating student_users table...")
    cursor.execute('''
        CREATE TABLE student_users (
            student_id TEXT PRIMARY KEY,
            name TEXT,
            email TEXT,
            password TEXT,
            parent_email TEXT
        )
    ''')

# Add student users
student_users = [
    ('S0001', 'John Collins', 'john@example.com', 'john123', 'parent1@example.com'),
    ('S0002', 'Emma Watson', 'emma@example.com', 'emma123', 'parent2@example.com'),
    ('S0003', 'Michael Brown', 'michael@example.com', 'michael123', 'parent3@example.com'),
    ('S0004', 'Sophia Lee', 'sophia@example.com', 'sophia123', 'parent4@example.com'),
    ('S0005', 'James Wilson', 'james@example.com', 'james123', 'parent5@example.com'),
]

for su in student_users:
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO student_users (student_id, name, email, password, parent_email)
            VALUES (?, ?, ?, ?, ?)
        ''', su)
        print(f"Added/Updated: {su[0]} - {su[1]}")
    except Exception as e:
        print(f"Error adding {su[0]}: {e}")

conn.commit()
conn.close()

print("\n✅ Student users added successfully!")
print("\n📋 Login Credentials:")
print("   Student ID: S0001, Password: john123")
print("   Student ID: S0002, Password: emma123")
print("   Student ID: S0003, Password: michael123")
print("   Parent Email: parent1@example.com, Password: john123")