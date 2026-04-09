import pandas as pd
import numpy as np
from datetime import datetime

# Set random seed for reproducibility
np.random.seed(42)

# Number of students - 500 for impressive analysis
num_students = 500

# Generate student IDs
student_ids = [f"S{i:04d}" for i in range(1, num_students + 1)]

# Generate names (first names and last names)
first_names = ['John', 'Emma', 'Michael', 'Sophia', 'James', 'Olivia', 'William', 'Ava', 'Benjamin', 'Mia',
               'Lucas', 'Isabella', 'Ethan', 'Amelia', 'Alexander', 'Charlotte', 'Daniel', 'Emily', 'Matthew', 'Abigail',
               'David', 'Madison', 'Joseph', 'Elizabeth', 'Charles', 'Grace', 'Andrew', 'Chloe', 'Christopher', 'Natalie',
               'Joshua', 'Samantha', 'Ryan', 'Victoria', 'Nicholas', 'Lily', 'Jonathan', 'Hannah', 'Christian', 'Sarah',
               'Brandon', 'Zoe', 'Samuel', 'Leah', 'Dylan', 'Audrey', 'Nathan', 'Brooklyn', 'Gabriel', 'Savannah']

last_names = ['Smith', 'Johnson', 'Brown', 'Williams', 'Jones', 'Garcia', 'Martinez', 'Rodriguez', 'Lee', 'Wilson',
              'Anderson', 'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin', 'Thompson', 'White', 'Harris', 'Clark',
              'Lewis', 'Robinson', 'Walker', 'Hall', 'Young', 'Allen', 'King', 'Wright', 'Scott', 'Green',
              'Baker', 'Adams', 'Nelson', 'Carter', 'Mitchell', 'Perez', 'Roberts', 'Turner', 'Phillips', 'Campbell',
              'Parker', 'Evans', 'Edwards', 'Collins', 'Stewart', 'Sanchez', 'Morris', 'Rogers', 'Reed', 'Cook']

# Generate random names
names = [f"{np.random.choice(first_names)} {np.random.choice(last_names)}" for _ in range(num_students)]

# Gender distribution (slightly balanced)
genders = np.random.choice(['Male', 'Female'], size=num_students, p=[0.48, 0.52])

# Age distribution (15-19 years)
ages = np.random.choice([15, 16, 17, 18, 19], size=num_students, p=[0.05, 0.20, 0.40, 0.25, 0.10])

# Study hours (correlated with final score)
study_hours_base = np.random.normal(5, 1.5, num_students)
study_hours = np.clip(study_hours_base, 1, 12).round(1)

# Previous score (correlated with final score)
previous_score_base = np.random.normal(75, 12, num_students)
previous_score = np.clip(previous_score_base, 40, 98).round(0).astype(int)

# Attendance percentage (correlated with final score)
attendance_base = np.random.normal(82, 10, num_students)
attendance = np.clip(attendance_base, 50, 100).round(0).astype(int)

# Parent education level (affects performance)
parent_education = np.random.choice(
    ['High School', 'Bachelor\'s', 'Master\'s', 'PhD'],
    size=num_students,
    p=[0.25, 0.40, 0.25, 0.10]
)

# Parent income (correlated with education)
parent_income = []
for edu in parent_education:
    if edu == 'High School':
        income = np.random.randint(30000, 55000)
    elif edu == 'Bachelor\'s':
        income = np.random.randint(55000, 85000)
    elif edu == 'Master\'s':
        income = np.random.randint(85000, 120000)
    else:  # PhD
        income = np.random.randint(110000, 180000)
    parent_income.append(income)

# Internet access at home
internet_access = np.random.choice(['Yes', 'No'], size=num_students, p=[0.85, 0.15])

# Sleep hours
sleep_hours = np.random.choice([5, 6, 7, 8, 9], size=num_students, p=[0.05, 0.20, 0.40, 0.25, 0.10])

# Extracurricular activities
extracurricular = np.random.choice(['Yes', 'No'], size=num_students, p=[0.60, 0.40])

# Tuition classes
tuition_classes = np.random.choice(['Yes', 'No'], size=num_students, p=[0.55, 0.45])

# Library access
library_access = np.random.choice(['Yes', 'No'], size=num_students, p=[0.75, 0.25])

# Transport facility
transport_facility = np.random.choice(['Yes', 'No'], size=num_students, p=[0.50, 0.50])

# Generate component scores based on study hours and previous score
def generate_scores(study_hours, prev_score, attendance):
    base = (study_hours * 3) + (prev_score * 0.4) + (attendance * 0.2)
    noise = np.random.normal(0, 5)
    score = base + noise
    return np.clip(score, 40, 100).round(0).astype(int)

midterm_scores = []
assignment_scores = []
quiz_scores = []
project_scores = []

for i in range(num_students):
    midterm_scores.append(generate_scores(study_hours[i], previous_score[i], attendance[i]))
    assignment_scores.append(generate_scores(study_hours[i], previous_score[i], attendance[i]) - np.random.randint(-3, 3))
    quiz_scores.append(generate_scores(study_hours[i], previous_score[i], attendance[i]) - np.random.randint(-5, 5))
    project_scores.append(generate_scores(study_hours[i], previous_score[i], attendance[i]) + np.random.randint(-2, 4))

# Final score (weighted average)
final_scores = []
for i in range(num_students):
    final = (midterm_scores[i] * 0.25 + 
             assignment_scores[i] * 0.20 + 
             quiz_scores[i] * 0.15 + 
             project_scores[i] * 0.40)
    final_scores.append(round(final, 1))

# Grade based on final score
def get_grade(score):
    if score >= 90:
        return 'A+'
    elif score >= 80:
        return 'A'
    elif score >= 70:
        return 'B'
    elif score >= 60:
        return 'C'
    elif score >= 50:
        return 'D'
    else:
        return 'F'

grades = [get_grade(score) for score in final_scores]

# Create DataFrame
data = {
    'student_id': student_ids,
    'name': names,
    'gender': genders,
    'age': ages,
    'study_hours': study_hours,
    'previous_score': previous_score,
    'attendance_percentage': attendance,
    'parent_education_level': parent_education,
    'parent_income': parent_income,
    'internet_access_at_home': internet_access,
    'sleep_hours': sleep_hours,
    'extracurricular_activities': extracurricular,
    'tuition_classes': tuition_classes,
    'library_access': library_access,
    'transport_facility': transport_facility,
    'midterm_score': midterm_scores,
    'assignment_score': assignment_scores,
    'quiz_score': quiz_scores,
    'project_score': project_scores,
    'final_score': final_scores,
    'grade': grades
}

df = pd.DataFrame(data)

# Save to CSV
df.to_csv('data/raw/student_data.csv', index=False)
df.to_csv('data/processed/student_data_cleaned.csv', index=False)

print(f"✅ Generated {len(df)} student records!")
print("\n📊 Dataset Summary:")
print(f"   - Total Students: {len(df)}")
print(f"   - Features: {len(df.columns)}")
print(f"   - Grade Distribution:")
print(df['grade'].value_counts().sort_index())
print("\n📁 Files saved to:")
print("   - data/raw/student_data.csv")
print("   - data/processed/student_data_cleaned.csv")