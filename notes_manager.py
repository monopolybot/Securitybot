import sqlite3
from datetime import datetime, timedelta
from kings_db import update_king_note, process_king_note

DB_NAME = "monopoly_notes.db"

# دالة لتهيئة قاعدة البيانات
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
    
    # حساب توقيت الأردن (UTC + 3 ساعات)
    amman_time = (datetime.utcnow() + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M")
    
    try:
        if action == "add":
            name, content, admin_id = data
            cursor.execute("INSERT INTO admin_notes (member_name, note_content, admin_id, date_added) VALUES (?, ?, ?, ?)", 
                           (name, content, admin_id, amman_time))
            res = "success"

        elif action == "get_active":
            cursor.execute("SELECT member_name FROM admin_notes WHERE status = 'active' GROUP BY member_name")
            res = cursor.fetchall()

        elif action == "search":
            cursor.execute("SELECT member_name, note_content, date_added FROM admin_notes WHERE member_name = ? ORDER BY id ASC", (data,))
            res = cursor.fetchall()

        elif action == "edit_by_index":
            name, index, new_content = data
            # جلب معرف الملاحظة والنص القديم قبل التعديل
            cursor.execute("SELECT id, note_content, admin_id FROM admin_notes WHERE member_name = ? ORDER BY id ASC", (name,))
            rows = cursor.fetchall()
            idx = int(index)
            if len(rows) >= idx:
                note_id = rows[idx-1][0]
                old_content = rows[idx-1][1]
                admin_id = rows[idx-1][2] # أو يمكن أن يكون admin_id هو نفسه user_id حسب نظامك
                
                # تنفيذ التعديل في جدول الملاحظات
                cursor.execute("UPDATE admin_notes SET note_content = ? WHERE id = ?", (new_content, note_id))
                
                # استدعاء دالة تحديث نقاط الملوك تلقائياً (خصم القديم وإضافة الجديد)
                # ملاحظة: إذا كان admin_id أو member_name هو ما تعتمد عليه كـ user_id، يمكنك تمريره هنا:
                try:
                    # نفترض أن admin_id أو المعرف هو المستخدم، أو يتم تمريره
                    update_king_note(admin_id, old_content, new_content)
                except Exception as e_king:
                    print(f"King points update error: {e_king}")
                    
                res = "success"

        elif action == "delete_by_index":
            name, index = data
            cursor.execute("SELECT id FROM admin_notes WHERE member_name = ? ORDER BY id ASC", (name,))
            ids = cursor.fetchall()
            idx = int(index)
            if len(ids) >= idx:
                cursor.execute("DELETE FROM admin_notes WHERE id = ?", (ids[idx-1][0],))
                res = "success"

        elif action == "delete_all":
            cursor.execute("DELETE FROM admin_notes WHERE member_name = ?", (data,))
            res = "success" if cursor.rowcount > 0 else "not_found"

        conn.commit()
    except Exception as e:
        print(f"Error in manage_note: {e}")
        res = None
    finally:
        conn.close()
    
    return res
