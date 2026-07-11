import sqlite3
from datetime import datetime

DB_NAME = "monopoly_notes.db"

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
        conn.commit()
        res = "success"

    elif action == "get_active":
        cursor.execute("SELECT member_name FROM admin_notes WHERE status = 'active' GROUP BY member_name")
        res = cursor.fetchall()

    elif action == "search":
        name = data
        cursor.execute("SELECT member_name, note_content, date_added, status FROM admin_notes WHERE member_name = ? ORDER BY id ASC", (name,))
        res = cursor.fetchall()

    elif action == "edit_by_index":
        # إضافة التعديل المطلوب: البحث عن الملاحظة عبر الاسم وترتيبها ثم تحديثها
        name, index, new_content = data
        cursor.execute("SELECT id FROM admin_notes WHERE member_name = ? ORDER BY id ASC", (name,))
        results = cursor.fetchall()
        
        if len(results) >= int(index):
            target_id = results[int(index)-1][0] # جلب الـ ID الحقيقي
            cursor.execute("UPDATE admin_notes SET note_content = ? WHERE id = ?", (new_content, target_id))
            conn.commit()
            res = "success"
        else:
            res = "not_found"

    elif action == "delete_all":
        name = data
        cursor.execute("DELETE FROM admin_notes WHERE member_name = ?", (name,))
        conn.commit()
        res = "success" if cursor.rowcount > 0 else "not_found"

    elif action == "archive":
        cursor.execute("UPDATE admin_notes SET status = 'archived' WHERE status = 'active'")
        conn.commit()
        res = "success"

    conn.close()
    return res
