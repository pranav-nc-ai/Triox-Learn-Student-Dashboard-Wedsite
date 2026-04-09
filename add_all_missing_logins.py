import sqlite3
import random
import string

conn = sqlite3.connect('database/students.db')
cursor = conn.cursor()

print("=" * 60)
print("📊 ADDING MISSING STUDENT & PARENT LOGINS")
print("=" * 60)

# Get all students from students table
cursor.execute("SELECT student_id, name FROM students ORDER BY student_id")
all_students = cursor.fetchall()

# Get existing logins
cursor.execute("SELECT student_id FROM student_users WHERE student_id NOT IN ('admin', 'teacher')")
existing_logins = set(row[0] for row in cursor.fetchall())

print(f"\n📌 Total students in database: {len(all_students)}")
print(f"📌 Existing student logins: {len(existing_logins)}")
print(f"⚠️ Missing logins: {len(all_students) - len(existing_logins)}")

print("\n🔄 Adding login credentials for missing students...\n")

added_count = 0
for student in all_students:
    student_id = student[0]
    name = student[1]
    
    # Skip if already has login
    if student_id in existing_logins:
        continue
    
    # Generate credentials
    student_password = f"{student_id.lower()}123"
    student_email = f"{name.lower().replace(' ', '.')}@student.com"
    
    # Generate parent credentials
    parent_email = f"parent.{student_id.lower()}@example.com"
    parent_password = f"parent{student_id[1:]}123"
    
    # Insert into student_users
    cursor.execute('''
        INSERT OR REPLACE INTO student_users 
        (student_id, name, email, password, parent_email, parent_password, is_active)
        VALUES (?, ?, ?, ?, ?, ?, 1)
    ''', (student_id, name, student_email, student_password, parent_email, parent_password))
    
    added_count += 1
    if added_count <= 10:  # Show first 10 as sample
        print(f"✅ {student_id} - {name[:20]:20} | Student PW: {student_password} | Parent PW: {parent_password}")
    elif added_count == 11:
        print(f"   ... and {len(all_students) - len(existing_logins) - 10} more students")

conn.commit()
conn.close()

print(f"\n{'='*60}")
print(f"✅ Successfully added {added_count} new student logins!")
print(f"📌 Total student accounts now: {len(existing_logins) + added_count}")
print(f"📌 Total parent accounts: {len(existing_logins) + added_count}")
print("=" * 60)

# Show summary
print("\n📝 CREDENTIALS FORMAT:")
print("   Student ID: S0501")
print("   Student Password: s0501123")
print("   Student Email: name@student.com")
print("   Parent Email: parent.s0501@example.com")
print("   Parent Password: parent501123")