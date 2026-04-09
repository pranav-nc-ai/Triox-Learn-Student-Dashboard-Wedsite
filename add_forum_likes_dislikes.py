import sqlite3

conn = sqlite3.connect('database/students.db')
cursor = conn.cursor()

# Add likes/dislikes columns to forum_topics
try:
    cursor.execute("ALTER TABLE forum_topics ADD COLUMN likes INTEGER DEFAULT 0")
    print("✅ Added likes column to forum_topics")
except:
    print("⚠️ likes column already exists")

try:
    cursor.execute("ALTER TABLE forum_topics ADD COLUMN dislikes INTEGER DEFAULT 0")
    print("✅ Added dislikes column to forum_topics")
except:
    print("⚠️ dislikes column already exists")

# Add likes/dislikes columns to forum_replies
try:
    cursor.execute("ALTER TABLE forum_replies ADD COLUMN likes INTEGER DEFAULT 0")
    print("✅ Added likes column to forum_replies")
except:
    print("⚠️ likes column already exists in forum_replies")

try:
    cursor.execute("ALTER TABLE forum_replies ADD COLUMN dislikes INTEGER DEFAULT 0")
    print("✅ Added dislikes column to forum_replies")
except:
    print("⚠️ dislikes column already exists in forum_replies")

# Create topic likes tracking table
cursor.execute('''
CREATE TABLE IF NOT EXISTS topic_reactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER,
    user_id TEXT,
    reaction_type TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(topic_id, user_id),
    FOREIGN KEY (topic_id) REFERENCES forum_topics(topic_id)
)
''')
print("✅ Created topic_reactions table")

# Create reply likes tracking table
cursor.execute('''
CREATE TABLE IF NOT EXISTS reply_reactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reply_id INTEGER,
    user_id TEXT,
    reaction_type TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(reply_id, user_id),
    FOREIGN KEY (reply_id) REFERENCES forum_replies(reply_id)
)
''')
print("✅ Created reply_reactions table")

conn.commit()
conn.close()
print("\n🎉 All forum tables updated successfully!")