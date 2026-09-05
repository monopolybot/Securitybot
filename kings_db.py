import sqlite3
import re

DB_KINGS_NAME = "monopoly_kings.db"

# دالة لتهيئة قاعدة البيانات وجدول الملوك
def init_kings_db():
    conn = sqlite3.connect(DB_KINGS_NAME)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS kings_ranking 
                      (user_id INTEGER PRIMARY KEY, 
                       member_name TEXT, 
                       stars_6 INTEGER DEFAULT 0,
                       stars_5 INTEGER DEFAULT 0,
                       stars_4 INTEGER DEFAULT 0,
                       stars_3 INTEGER DEFAULT 0,
                       stars_2 INTEGER DEFAULT 0,
                       stars_1 INTEGER DEFAULT 0,
                       total_stars INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

# تنفيذ التهيئة فور استدعاء الملف
init_kings_db()

# دالة مساعدة لاستخراج فئة النجوم وقيمتها من نص الملاحظة
def extract_star_category(note_content):
    content = note_content.lower()
    
    if any(w in content for w in ["6 نجوم", "ستة نجوم", "ست نجوم", "6ن"]):
        return "stars_6", 6
    elif any(w in content for w in ["5 نجوم", "خمس نجوم", "خمسه نجوم", "5ن"]):
        return "stars_5", 5
    elif any(w in content for w in ["4 نجوم", "أربعة نجوم", "اربعة نجوم", "4ن"]):
        return "stars_4", 4
    elif any(w in content for w in ["3 نجوم", "ثلاثة نجوم", "ثلاث نجوم", "3n", "3ن"]):
        return "stars_3", 3
    elif any(w in content for w in ["نجمتين", "نجمتان", "2 نجوم", "2ن"]):
        return "stars_2", 2
    elif any(w in content for w in ["نجمة", "نجمه", "1 نجوم", "1ن"]):
        return "stars_1", 1
        
    return None, 0

# دالة التحليل الذكي للنص وتحديث السجلات تراكمياً
def process_king_note(user_id, member_name, note_content):
    star_category, star_value = extract_star_category(note_content)
    
    if not star_category:
        return False
        
    conn = sqlite3.connect(DB_KINGS_NAME)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT user_id, stars_6, stars_5, stars_4, stars_3, stars_2, stars_1, total_stars FROM kings_ranking WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        
        if row:
            s6, s5, s4, s3, s2, s1, total = row[1], row[2], row[3], row[4], row[5], row[6], row[7]
            
            if star_category == "stars_6": s6 += 1
            elif star_category == "stars_5": s5 += 1
            elif star_category == "stars_4": s4 += 1
            elif star_category == "stars_3": s3 += 1
            elif star_category == "stars_2": s2 += 1
            elif star_category == "stars_1": s1 += 1
            
            total += star_value
            
            cursor.execute("""UPDATE kings_ranking 
                              SET member_name = ?, stars_6 = ?, stars_5 = ?, stars_4 = ?, stars_3 = ?, stars_2 = ?, stars_1 = ?, total_stars = ? 
                              WHERE user_id = ?""", 
                           (member_name, s6, s5, s4, s3, s2, s1, total, user_id))
        else:
            s6 = 1 if star_category == "stars_6" else 0
            s5 = 1 if star_category == "stars_5" else 0
            s4 = 1 if star_category == "stars_4" else 0
            s3 = 1 if star_category == "stars_3" else 0
            s2 = 1 if star_category == "stars_2" else 0
            s1 = 1 if star_category == "stars_1" else 0
            total = star_value
            
            cursor.execute("""INSERT INTO kings_ranking 
                              (user_id, member_name, stars_6, stars_5, stars_4, stars_3, stars_2, stars_1, total_stars) 
                              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
                           (user_id, member_name, s6, s5, s4, s3, s2, s1, total))
            
        conn.commit()
        success = True
    except Exception as e:
        print(f"Error in process_king_note: {e}")
        success = False
    finally:
        conn.close()
        
    return success

# دالة لتحديث ملاحظة سابقة وخصم النقاط القديمة وإضافة النقاط الجديدة تلقائياً
def update_king_note(user_id, old_note_content, new_note_content):
    old_cat, old_val = extract_star_category(old_note_content)
    new_cat, new_val = extract_star_category(new_note_content)
    
    # إذا لم تكن الملاحظتان تحتويان على نجوم صالحة، لا نحتاج لتعديل النقاط
    if not old_cat and not new_cat:
        return True

    conn = sqlite3.connect(DB_KINGS_NAME)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT stars_6, stars_5, stars_4, stars_3, stars_2, stars_1, total_stars FROM kings_ranking WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        
        if row:
            s6, s5, s4, s3, s2, s1, total = row[0], row[1], row[2], row[3], row[4], row[5], row[6]
            
            # 1. طرح تأثير الملاحظة القديمة (إذا كانت موجودة)
            if old_cat:
                if old_cat == "stars_6": s6 = max(0, s6 - 1)
                elif old_cat == "stars_5": s5 = max(0, s5 - 1)
                elif old_cat == "stars_4": s4 = max(0, s4 - 1)
                elif old_cat == "stars_3": s3 = max(0, s3 - 1)
                elif old_cat == "stars_2": s2 = max(0, s2 - 1)
                elif old_cat == "stars_1": s1 = max(0, s1 - 1)
                total = max(0, total - old_val)
                
            # 2. إضافة تأثير الملاحظة الجديدة (إذا كانت موجودة)
            if new_cat:
                if new_cat == "stars_6": s6 += 1
                elif new_cat == "stars_5": s5 += 1
                elif new_cat == "stars_4": s4 += 1
                elif new_cat == "stars_3": s3 += 1
                elif new_cat == "stars_2": s2 += 1
                elif new_cat == "stars_1": s1 += 1
                total += new_val
                
            cursor.execute("""UPDATE kings_ranking 
                              SET stars_6 = ?, stars_5 = ?, stars_4 = ?, stars_3 = ?, stars_2 = ?, stars_1 = ?, total_stars = ? 
                              WHERE user_id = ?""", 
                           (s6, s5, s4, s3, s2, s1, total, user_id))
            conn.commit()
            success = True
        else:
            # إذا لم يكن موجوداً وتم التعديل، نقوم بإضافته كجديد كلياً
            success = process_king_note(user_id, "مستخدم", new_note_content)
            
    except Exception as e:
        print(f"Error in update_king_note: {e}")
        success = False
    finally:
        conn.close()
        
    return success

# دالة لجلب كل الملوك مرتبين تنازلياً حسب مجموع النجوم
def get_kings_ranking():
    conn = sqlite3.connect(DB_KINGS_NAME)
    cursor = conn.cursor()
    cursor.execute("""SELECT user_id, member_name, stars_6, stars_5, stars_4, stars_3, stars_2, stars_1, total_stars 
                      FROM kings_ranking 
                      ORDER BY total_stars DESC""")
    rows = cursor.fetchall()
    conn.close()
    return rows

# دالة لتعديل أو تصحيح سجل عضو يدوياً في حال الخطأ
def adjust_king_score(user_id, s6, s5, s4, s3, s2, s1):
    total = (s6 * 6) + (s5 * 5) + (s4 * 4) + (s3 * 3) + (s2 * 2) + (s1 * 1)
    
    conn = sqlite3.connect(DB_KINGS_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("""UPDATE kings_ranking 
                          SET stars_6 = ?, stars_5 = ?, stars_4 = ?, stars_3 = ?, stars_2 = ?, stars_1 = ?, total_stars = ? 
                          WHERE user_id = ?""", 
                       (s6, s5, s4, s3, s2, s1, total, user_id))
        conn.commit()
        success = True
    except Exception as e:
        print(f"Error in adjust_king_score: {e}")
        success = False
    finally:
        conn.close()
    return success
