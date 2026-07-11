import sqlite3
from datetime import datetime

DB_NAME = "monopoly_notes.db"

# دالة لتهيئة قاعدة البيانات (تمت إضافتها لحل الخطأ)
def init_notes_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS admin_notes 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                       member_name TEXT, 
                       note_content TEXT, 
                       admin_id INTEGER, 
                       date_added TEXT,
                       status TEXT DEFAULT 'active')''')
    conn.commit()
    conn.close()

def manage_note(action, data=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    res = None
    
    if action == "add":
        name, content, admin_id = data
        cursor.execute("INSERT INTO admin_notes (member_name, note_content, admin_id, date_added) VALUES (?, ?, ?, ?)", 
                       (name, content, admin_id, datetime.now().strftime("%Y-%m-%d %H:%M")))
        res = "success"

    elif action == "get_active":
        cursor.execute("SELECT member_name FROM admin_notes WHERE status = 'active' GROUP BY member_name")
        res = cursor.fetchall()

    elif action == "search":
        cursor.execute("SELECT member_name, note_content, date_added FROM admin_notes WHERE member_name = ? ORDER BY id ASC", (data,))
        res = cursor.fetchall()

    elif action == "edit_by_index":
        name, index, new_content = data
        cursor.execute("SELECT id FROM admin_notes WHERE member_name = ? ORDER BY id ASC", (name,))
        ids = cursor.fetchall()
        if len(ids) >= int(index):
            cursor.execute("UPDATE admin_notes SET note_content = ? WHERE id = ?", (new_content, ids[int(index)-1][0]))
            res = "success"

    elif action == "delete_by_index":
        name, index = data
        cursor.execute("SELECT id FROM admin_notes WHERE member_name = ? ORDER BY id ASC", (name,))
        ids = cursor.fetchall()
        if len(ids) >= int(index):
            cursor.execute("DELETE FROM admin_notes WHERE id = ?", (ids[int(index)-1][0],))
            res = "success"

    elif action == "delete_all":
        cursor.execute("DELETE FROM admin_notes WHERE member_name = ?", (data,))
        res = "success" if cursor.rowcount > 0 else "not_found"

    conn.commit()
    conn.close()
    return res
