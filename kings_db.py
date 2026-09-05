import sqlite3
import re

DB_KINGS_NAME = "monopoly_kings.db"

# دالة لتهيئة قاعدة البيانات وجدول الملوك
def init_kings_db():
    conn = sqlite3.connect(DB_KINGS_NAME)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS kings_ranking 
                      (uid TEXT PRIMARY KEY, 
                       name TEXT, 
                       s6 INTEGER DEFAULT 0,
                       s5 INTEGER DEFAULT 0,
                       s4 INTEGER DEFAULT 0,
                       s3 INTEGER DEFAULT 0,
                       s2 INTEGER DEFAULT 0,
                       s1 INTEGER DEFAULT 0,
                       total INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

# تنفيذ التهيئة فور استدعاء الملف
init_kings_db()

# دالة مساعدة لاستخراج فئة النجوم وقيمتها من نص الملاحظة
def extract_star_category(note_content):
    content = note_content.lower()
    
    if any(w in content for w in ["6 نجوم", "ستة نجوم", "ست نجوم", "6ن"]):
        return "s6", 6
    elif any(w in content for w in ["5 نجوم", "خمس نجوم", "خمسه نجوم", "5ن"]):
        return "s5", 5
    elif any(w in content for w in ["4 نجوم", "أربعة نجوم", "اربعة نجوم", "4ن"]):
        return "s4", 4
    elif any(w in content for w in ["3 نجوم", "ثلاثة نجوم", "ثلاث نجوم", "3n", "3ن"]):
        return "s3", 3
    elif any(w in content for w in ["نجمتين", "نجمتان", "2 نجوم", "2ن"]):
        return "s2", 2
    elif any(w in content for w in ["نجمة", "نجمه", "1 نجوم", "1ن"]):
        return "s1", 1
        
    return None, 0

# دالة التحليل الذكي للنص وتحديث السجلات تراكمياً (تعتمد اسم العضو المستهدف من النص)
def process_king_note(admin_id, admin_name, text):
    """
    يعالج نص الملاحظة لاستخراج اسم الملك المستهدف والفئة والنقاط وتحديث قاعدة البيانات.
    الشكل المتوقع: تسجيل ملاحظة [اسم_الملك] : [نص الملاحظة]
    """
    # البحث عن الاسم الواقع بين كلمة "ملاحظة" والنقطتين الرأسيتين ":"
    match_name = re.search(r'ملاحظة\s+(.*?)\s*:', text)
    if not match_name:
        return False, "⚠️ صيغة الملاحظة غير صحيحة. استخدم: تسجيل ملاحظة [اسم العضو] : [التفاصيل]"
    
    target_name = match_name.group(1).strip()
    
    # استخراج فئة النجوم والنقاط باستخدام الدالة المساعدة
    star_category, points_to_add = extract_star_category(text)
        
    if not star_category:
        return False, "⚠️ لم يتم تحديد فئة النجوم بدقة في الملاحظة (مثال: 5 نجوم أو خمس نجوم)."

    from database import db
    
    # التحقق هل العضو موجود مسبقاً في جدول ملوك المجموعة بواسطة اسمه
    db.cursor.execute("SELECT uid, s6, s5, s4, s3, s2, s1, total FROM kings_ranking WHERE name = ?", (target_name,))
    row = db.cursor.fetchone()
    
    if row:
        uid = row[0]
        s6, s5, s4, s3, s2, s1, total = row[1], row[2], row[3], row[4], row[5], row[6], row[7]
        
        # تحديث العداد والفئة المحددة
        if star_category == "s6": s6 += 1
        elif star_category == "s5": s5 += 1
        elif star_category == "s4": s4 += 1
        elif star_category == "s3": s3 += 1
        elif star_category == "s2": s2 += 1
        elif star_category == "s1": s1 += 1
        
        total += points_to_add
        
        db.cursor.execute("""
            UPDATE kings_ranking 
            SET s6 = ?, s5 = ?, s4 = ?, s3 = ?, s2 = ?, s1 = ?, total = ?
            WHERE name = ?
        """, (s6, s5, s4, s3, s2, s1, total, target_name))
    else:
        # إنشاء سجل جديد للملك المستهدف
        s6 = 1 if star_category == "s6" else 0
        s5 = 1 if star_category == "s5" else 0
        s4 = 1 if star_category == "s4" else 0
        s3 = 1 if star_category == "s3" else 0
        s2 = 1 if star_category == "s2" else 0
        s1 = 1 if star_category == "s1" else 0
        total = points_to_add
        
        uid = f"king_{abs(hash(target_name))}"
        
        db.cursor.execute("""
            INSERT INTO kings_ranking (uid, name, s6, s5, s4, s3, s2, s1, total)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (uid, target_name, s6, s5, s4, s3, s2, s1, total))
        
    db.conn.commit()
    return True, f"👑 **تم تسجيل الملاحظة بنجاح!**\n👤 **الملك المستفيد:** `{target_name}`\n⭐ **الفئة:** `{star_category.upper()}` (+{points_to_add} نقاط)"


# دالة لتحديث ملاحظة سابقة وخصم النقاط القديمة وإضافة النقاط الجديدة تلقائياً
def update_king_note(old_note_content, new_note_content):
    match_old = re.search(r'ملاحظة\s+(.*?)\s*:', old_note_content)
    match_new = re.search(r'ملاحظة\s+(.*?)\s*:', new_note_content)
    
    if not match_new:
        return False
        
    target_name = match_new.group(1).strip()
    old_cat, old_val = extract_star_category(old_note_content)
    new_cat, new_val = extract_star_category(new_note_content)
    
    if not old_cat and not new_cat:
        return True

    conn = sqlite3.connect(DB_KINGS_NAME)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT s6, s5, s4, s3, s2, s1, total FROM kings_ranking WHERE name = ?", (target_name,))
        row = cursor.fetchone()
        
        if row:
            s6, s5, s4, s3, s2, s1, total = row[0], row[1], row[2], row[3], row[4], row[5], row[6]
            
            # 1. طرح تأثير الملاحظة القديمة
            if old_cat and (not match_old or match_old.group(1).strip() == target_name):
                if old_cat == "s6": s6 = max(0, s6 - 1)
                elif old_cat == "s5": s5 = max(0, s5 - 1)
                elif old_cat == "s4": s4 = max(0, s4 - 1)
                elif old_cat == "s3": s3 = max(0, s3 - 1)
                elif old_cat == "s2": s2 = max(0, s2 - 1)
                elif old_cat == "s1": s1 = max(0, s1 - 1)
                total = max(0, total - old_val)
                
            # 2. إضافة تأثير الملاحظة الجديدة
            if new_cat:
                if new_cat == "s6": s6 += 1
                elif new_cat == "s5": s5 += 1
                elif new_cat == "s4": s4 += 1
                elif new_cat == "s3": s3 += 1
                elif new_cat == "s2": s2 += 1
                elif new_cat == "s1": s1 += 1
                total += new_val
                
            cursor.execute("""UPDATE kings_ranking 
                              SET s6 = ?, s5 = ?, s4 = ?, s3 = ?, s2 = ?, s1 = ?, total = ? 
                              WHERE name = ?""", 
                           (s6, s5, s4, s3, s2, s1, total, target_name))
            conn.commit()
            success = True
        else:
            success, _ = process_king_note(0, "System", new_note_content)
            
    except Exception as e:
        print(f"Error in update_king_note: {e}")
        success = False
    finally:
        conn.close()
        
    return success

# دالة لجلب كل الملوك مرتبين تنازلياً حسب مجموع النقاط
def get_kings_ranking():
    conn = sqlite3.connect(DB_KINGS_NAME)
    cursor = conn.cursor()
    cursor.execute("""SELECT uid, name, s6, s5, s4, s3, s2, s1, total 
                      FROM kings_ranking 
                      ORDER BY total DESC""")
    rows = cursor.fetchall()
    conn.close()
    return rows

# دالة لتعديل أو تصحيح سجل عضو يدوياً
def adjust_king_score(target_name, s6, s5, s4, s3, s2, s1):
    total = (s6 * 6) + (s5 * 5) + (s4 * 4) + (s3 * 3) + (s2 * 2) + (s1 * 1)
    
    conn = sqlite3.connect(DB_KINGS_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("""UPDATE kings_ranking 
                          SET s6 = ?, s5 = ?, s4 = ?, s3 = ?, s2 = ?, s1 = ?, total = ? 
                          WHERE name = ?""", 
                       (s6, s5, s4, s3, s2, s1, total, target_name))
        conn.commit()
        success = True
    except Exception as e:
        print(f"Error in adjust_king_score: {e}")
        success = False
    finally:
        conn.close()
    return success
