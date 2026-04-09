import os
import re

templates_dir = 'templates'

# List of files to fix
files_to_fix = [
    'forum.html',
    'forum_topic.html', 
    'notifications.html',
    'activity_logs.html',
    'meetings.html',
    'dashboard.html',
    'student_dashboard.html',
    'parent_dashboard.html',
    'certificates.html',
    'doubts.html'
]

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # Replace common time patterns
    replacements = [
        (r"new Date\(([^)]+)\)\.toLocaleString\(\)", r"TrioxTime.toIST(\1)"),
        (r"\.toLocaleString\(\)", r".toLocaleString('en-IN', {timeZone: 'Asia/Kolkata'})"),
    ]
    
    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content)
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Fixed: {filepath}")

# Fix files
for filename in files_to_fix:
    filepath = os.path.join(templates_dir, filename)
    if os.path.exists(filepath):
        fix_file(filepath)
    else:
        print(f"⚠️ File not found: {filepath}")

print("\n✅ All time displays fixed!")