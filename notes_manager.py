import sqlite3
from datetime import datetime

DB_NAME = "monopoly_notes.db"

def init_notes_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # جدول الملاحظات النشطة والمؤرشفة
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
    
    # 1. إضافة ملاحظة مع منع التكرار
    if action == "add":
        name, content, admin_id = data
        cursor.execute("SELECT * FROM admin_notes WHERE member_name = ? AND status = 'active'", (name,))
        if cursor.fetchone():
            conn.close()
            return "duplicate"
        cursor.execute("INSERT INTO admin_notes (member_name, note_content, admin_id, date_added) VALUES (?, ?, ?, ?)", 
                       (name, content, admin_id, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        res = "success"

    # 2. عرض المفكرة الحالية
    elif action == "get_active":
        cursor.execute("SELECT member_name, note_content, date_added FROM admin_notes WHERE status = 'active' ORDER BY id DESC")
        res = cursor.fetchall()

    # 3. تعديل ملاحظة موجودة
    elif action == "edit":
        name, new_content = data
        cursor.execute("UPDATE admin_notes SET note_content = ? WHERE member_name = ? AND status = 'active'", (new_content, name))
        conn.commit()
        res = "success" if cursor.rowcount > 0 else "not_found"

    # 4. حذف ملاحظة
    elif action == "delete":
        name = data
        cursor.execute("DELETE FROM admin_notes WHERE member_name = ? AND status = 'active'", (name,))
        conn.commit()
        res = "success" if cursor.rowcount > 0 else "not_found"

    # 5. أرشفة المفكرة (بدء مفكرة جديدة)
    elif action == "archive":
        cursor.execute("UPDATE admin_notes SET status = 'archived' WHERE status = 'active'")
        conn.commit()
        res = "success"

    # 6. جلب التاريخ (ملاحظات قديمة بناءً على التاريخ)
    elif action == "get_history":
        date_query = data # بصيغة YYYY-MM-DD
        cursor.execute("SELECT member_name, note_content, date_added FROM admin_notes WHERE date_added LIKE ? AND status = 'archived'", (f"{date_query}%",))
        res = cursor.fetchall()

    conn.close()
    return res
