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

# دالة التحليل الذكي للنص وتحديث السجلات تراكمياً
def process_king_note(user_id, member_name, note_content):
    # تحويل النص إلى أحرف صغيرة لتسهيل المطابقة
    content = note_content.lower()
    
    # تحديد الفئة المستهدفة بناءً على الكلمات المفتاحية أو الأرقام
    star_category = None
    star_value = 0
    
    if any(w in content for w in ["6 نجوم", "ستة نجوم", "ست نجوم", "6ن"]):
        star_category = "stars_6"
        star_value = 6
    elif any(w in content for w in ["5 نجوم", "خمس نجوم", "خمسه نجوم", "5ن"]):
        star_category = "stars_5"
        star_value = 5
    elif any(w in content for w in ["4 نجوم", "أربعة نجوم", "اربعة نجوم", "4ن"]):
        star_category = "stars_4"
        star_value = 4
    elif any(w in content for w in ["3 نجوم", "ثلاثة نجوم", "ثلاث نجوم", "3ن"]):
        star_category = "stars_3"
        star_value = 3
    elif any(w in content for w in ["نجمتين", "نجمتان", "2 نجوم", "2ن"]):
        star_category = "stars_2"
        star_value = 2
    elif any(w in content for w in ["نجمة", "نجمه", "1 نجوم", "1ن"]):
        star_category = "stars_1"
        star_value = 1
        
    # إذا لم يتم التعرف على أي فئة نجوم، نتوقف
    if not star_category:
        return False
        
    conn = sqlite3.connect(DB_KINGS_NAME)
    cursor = conn.cursor()
    
    try:
        # التأكد مما إذا كان العضو مسجلاً مسبقاً في قائمة الملوك
        cursor.execute("SELECT user_id, stars_6, stars_5, stars_4, stars_3, stars_2, stars_1, total_stars FROM kings_ranking WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        
        if row:
            # العضو موجود: نقوم بتحديث القيم تراكمياً
            s6, s5, s4, s3, s2, s1, total = row[1], row[2], row[3], row[4], row[5], row[6], row[7]
            
            if star_category == "stars_6": s6 += 1
            elif star_category == "stars_5": s5 += 1
            elif star_category == "stars_4": s4 += 1
            elif star_category == "stars_3": s3 += 1
            elif star_category == "stars_2": s2 += 1
            elif star_category == "stars_1": s1 += 1
            
            # تحديث الإجمالي التراكمي للنجوم
            total += star_value
            
            cursor.execute("""UPDATE kings_ranking 
                              SET member_name = ?, stars_6 = ?, stars_5 = ?, stars_4 = ?, stars_3 = ?, stars_2 = ?, stars_1 = ?, total_stars = ? 
                              WHERE user_id = ?""", 
                           (member_name, s6, s5, s4, s3, s2, s1, total, user_id))
        else:
            # العضو غير موجود: نضيف سجل جديد لأول مرة
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
