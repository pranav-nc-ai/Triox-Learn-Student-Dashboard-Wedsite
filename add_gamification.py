import sqlite3

conn = sqlite3.connect('database/students.db')
cursor = conn.cursor()

# Create badges table
cursor.execute('''
CREATE TABLE IF NOT EXISTS badges (
    badge_id INTEGER PRIMARY KEY,
    badge_name TEXT,
    badge_icon TEXT,
    description TEXT,
    requirement TEXT
)
''')

# Create student_badges table
cursor.execute('''
CREATE TABLE IF NOT EXISTS student_badges (
    student_id TEXT,
    badge_id INTEGER,
    earned_date TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (badge_id) REFERENCES badges(badge_id)
)
''')

# Create points table
cursor.execute('''
CREATE TABLE IF NOT EXISTS student_points (
    student_id TEXT PRIMARY KEY,
    total_points INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    xp INTEGER DEFAULT 0,
    FOREIGN KEY (student_id) REFERENCES students(student_id)
)
''')

# Insert badges
badges = [
    (1, 'Perfect Attendance', 'fa-calendar-check', 'Maintained 95%+ attendance for a month', 'Attendance >= 95% for 30 days'),
    (2, 'Grade Master', 'fa-star', 'Scored A+ in any subject', 'Grade = A+'),
    (3, 'Study Champion', 'fa-clock', 'Studied 7+ hours daily for 2 weeks', 'Study hours >= 7 for 14 days'),
    (4, 'Improvement Star', 'fa-chart-line', 'Improved score by 15+ points', 'Score improvement >= 15 points'),
    (5, 'Assignment Hero', 'fa-tasks', 'Completed all assignments on time', 'All assignments submitted on time'),
    (6, 'Quiz Master', 'fa-brain', 'Scored 90%+ in 5 quizzes', 'Quiz score >= 90% for 5 quizzes'),
    (7, 'Project Pro', 'fa-project-diagram', 'Scored 95%+ in project', 'Project score >= 95%'),
    (8, 'Attendance King', 'fa-crown', '100% attendance for a month', 'Attendance = 100% for 30 days'),
    (9, 'Top Performer', 'fa-trophy', 'Ranked in top 5 of class', 'Top 5 rank'),
    (10, 'Consistency Champion', 'fa-chart-simple', 'Maintained B+ grade for 2 months', 'Grade >= B for 60 days'),
]

cursor.executemany('INSERT OR IGNORE INTO badges VALUES (?,?,?,?,?)', badges)

conn.commit()
conn.close()
print("✅ Gamification tables created!")