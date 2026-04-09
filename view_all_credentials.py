import sqlite3

conn = sqlite3.connect('database/students.db')
cursor = conn.cursor()

print("=" * 80)
print("📊 NEXUSLEARN - ALL STUDENT & PARENT LOGIN CREDENTIALS")
print("=" * 80)

cursor.execute("""
    SELECT student_id, name, password, parent_email, parent_password 
    FROM student_users 
    WHERE student_id NOT IN ('admin', 'teacher')
    ORDER BY student_id
""")

all_users = cursor.fetchall()

print(f"\n{'Student ID':<12} {'Name':<25} {'Student PW':<15} {'Parent Email':<30} {'Parent PW':<15}")
print("-" * 100)

for user in all_users:
    print(f"{user[0]:<12} {user[1][:24]:<25} {user[2]:<15} {user[3][:29]:<30} {user[4]:<15}")

print("-" * 100)
print(f"\n✅ Total Students: {len(all_users)}")
print(f"✅ Total Parent Accounts: {len(all_users)}")
print("=" * 80)

conn.close()