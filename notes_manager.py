import sqlite3
from datetime import datetime

DB_NAME = "monopoly_radar_core.db"

def init_notes_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # جدول الملاحظات الحالية
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
    
    if action == "add":
        name, content, admin_id = data
        # فحص التكرار في المفكرة النشطة فقط
        cursor.execute("SELECT * FROM admin_notes WHERE member_name = ? AND status = 'active'", (name,))
        if cursor.fetchone():
            conn.close()
            return "duplicate"
        
        cursor.execute("INSERT INTO admin_notes (member_name, note_content, admin_id, date_added) VALUES (?, ?, ?, ?)", 
                       (name, content, admin_id, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        
    elif action == "get_active":
        cursor.execute("SELECT member_name, note_content, date_added FROM admin_notes WHERE status = 'active' ORDER BY id DESC")
        notes = cursor.fetchall()
        conn.close()
        return notes

    elif action == "new_notebook":
        # أرشفة الملاحظات الحالية (تحويلها لغير نشطة)
        cursor.execute("UPDATE admin_notes SET status = 'archived' WHERE status = 'active'")
        conn.commit()
    
    conn.close()
    return "success"
