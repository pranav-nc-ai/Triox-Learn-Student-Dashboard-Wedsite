import sqlite3

def calculate_points_for_all():
    conn = sqlite3.connect('database/students.db')
    cursor = conn.cursor()
    
    # Get all students
    cursor.execute("SELECT student_id, final_score, grade, study_hours, attendance_percentage, project_score FROM students")
    students = cursor.fetchall()
    
    for student in students:
        student_id = student[0]
        final_score = student[1]
        grade = student[2]
        study_hours = student[3]
        attendance = student[4]
        project_score = student[5]
        
        points = 0
        earned_badges = []
        
        # Points based on grade
        if grade == 'A+':
            points += 100
            earned_badges.append(2)
        elif grade == 'A':
            points += 80
        elif grade == 'B':
            points += 50
        elif grade == 'C':
            points += 30
        else:
            points += 10
        
        # Points based on attendance
        if attendance >= 95:
            points += 50
            earned_badges.append(1)
        elif attendance >= 90:
            points += 30
        elif attendance >= 85:
            points += 20
        else:
            points += 5
        
        # Points based on study hours
        if study_hours >= 8:
            points += 40
        elif study_hours >= 7:
            points += 30
        elif study_hours >= 5:
            points += 20
        else:
            points += 5
        
        # Points based on project score
        if project_score >= 95:
            points += 50
            earned_badges.append(7)
        elif project_score >= 85:
            points += 30
        
        # Insert or update points
        cursor.execute("SELECT * FROM student_points WHERE student_id = ?", (student_id,))
        existing = cursor.fetchone()
        
        if existing:
            cursor.execute("UPDATE student_points SET total_points = ?, xp = ? WHERE student_id = ?", (points, points, student_id))
        else:
            cursor.execute("INSERT INTO student_points VALUES (?, ?, ?, ?)", (student_id, points, 1, points))
        
        # Update level
        new_level = min(10, max(1, points // 500 + 1))
        cursor.execute("UPDATE student_points SET level = ? WHERE student_id = ?", (new_level, student_id))
        
        # Award badges
        for badge_id in earned_badges:
            cursor.execute("INSERT OR IGNORE INTO student_badges (student_id, badge_id, earned_date) VALUES (?, ?, datetime('now'))", (student_id, badge_id))
        
        print(f"✅ {student_id}: {points} points, Level {new_level}, Badges: {len(earned_badges)}")
    
    conn.commit()
    conn.close()
    print("\n🎉 All students updated successfully!")

if __name__ == "__main__":
    calculate_points_for_all()