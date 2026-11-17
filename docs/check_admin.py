import sqlite3

conn = sqlite3.connect("data/campusassist.db")
cur = conn.cursor()
cur.execute("SELECT id, username, role, is_active FROM users")
rows = cur.fetchall()
print("Existing users in data/campusassist.db:")
for r in rows:
    print(r)
conn.close()

