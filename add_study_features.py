import sqlite3

conn = sqlite3.connect('database/students.db')
cursor = conn.cursor()

# Add file sharing table
cursor.execute('''
CREATE TABLE IF NOT EXISTS room_files (
    file_id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER,
    uploaded_by TEXT,
    file_name TEXT,
    file_url TEXT,
    file_size INTEGER,
    file_type TEXT,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (room_id) REFERENCES study_rooms(room_id),
    FOREIGN KEY (uploaded_by) REFERENCES students(student_id)
)
''')

# Add whiteboard data table
cursor.execute('''
CREATE TABLE IF NOT EXISTS whiteboard_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER,
    drawing_data TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (room_id) REFERENCES study_rooms(room_id)
)
''')

print("✅ Study Room features added successfully!")
conn.commit()
conn.close()