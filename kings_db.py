import sqlite3
import re

DB_KINGS_NAME = "monopoly_kings.db"

def init_kings_db():
    conn = sqlite3.connect(DB_KINGS_NAME)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS kings_ranking 
                      (member_name TEXT PRIMARY KEY, 
                       stars_6 INTEGER DEFAULT 0,
                       stars_5 INTEGER DEFAULT 0,
                       stars_4 INTEGER DEFAULT 0,
                       stars_3 INTEGER DEFAULT 0,
                       stars_2 INTEGER DEFAULT 0,
                       stars_1 INTEGER DEFAULT 0,
                       total_stars INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

init_kings_db()

def extract_star_category(note_content):
    if not note_content:
        return None, 0
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

def process_king_note(admin_id, member_name, note_content):
    cat, val = extract_star_category(note_content)
    if not cat or not member_name:
        return False
        
    clean_name = member_name.strip()
    conn = sqlite3.connect(DB_KINGS_NAME)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT stars_6, stars_5, stars_4, stars_3, stars_2, stars_1, total_stars FROM kings_ranking WHERE member_name = ?", (clean_name,))
        row = cursor.fetchone()
        
        if row:
            s6, s5, s4, s3, s2, s1, total = row[0], row[1], row[2], row[3], row[4], row[5], row[6]
            if cat == "stars_6": s6 += 1
            elif cat == "stars_5": s5 += 1
            elif cat == "stars_4": s4 += 1
            elif cat == "stars_3": s3 += 1
            elif cat == "stars_2": s2 += 1
            elif cat == "stars_1": s1 += 1
            total += val
            
            cursor.execute("""UPDATE kings_ranking 
                              SET stars_6 = ?, stars_5 = ?, stars_4 = ?, stars_3 = ?, stars_2 = ?, stars_1 = ?, total_stars = ? 
                              WHERE member_name = ?""", 
                           (s6, s5, s4, s3, s2, s1, total, clean_name))
        else:
            s6 = 1 if cat == "stars_6" else 0
            s5 = 1 if cat == "stars_5" else 0
            s4 = 1 if cat == "stars_4" else 0
            s3 = 1 if cat == "stars_3" else 0
            s2 = 1 if cat == "stars_2" else 0
            s1 = 1 if cat == "stars_1" else 0
            total = val
            
            cursor.execute("""INSERT INTO kings_ranking (member_name, stars_6, stars_5, stars_4, stars_3, stars_2, stars_1, total_stars) 
                              VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", 
                           (clean_name, s6, s5, s4, s3, s2, s1, total))
        conn.commit()
        success = True
    except Exception as e:
        print(f"Error in process_king_note: {e}")
        success = False
    finally:
        conn.close()
    return success

def update_king_note(member_name, old_note_content, new_note_content):
    if not member_name:
        return False
    clean_name = member_name.strip()
    old_cat, old_val = extract_star_category(old_note_content)
    new_cat, new_val = extract_star_category(new_note_content)
    
    if not old_cat and not new_cat:
        return True

    conn = sqlite3.connect(DB_KINGS_NAME)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT stars_6, stars_5, stars_4, stars_3, stars_2, stars_1, total_stars FROM kings_ranking WHERE member_name = ?", (clean_name,))
        row = cursor.fetchone()
        
        if row:
            s6, s5, s4, s3, s2, s1, total = row[0], row[1], row[2], row[3], row[4], row[5], row[6]
            
            if old_cat:
                if old_cat == "stars_6": s6 = max(0, s6 - 1)
                elif old_cat == "stars_5": s5 = max(0, s5 - 1)
                elif old_cat == "stars_4": s4 = max(0, s4 - 1)
                elif old_cat == "stars_3": s3 = max(0, s3 - 1)
                elif old_cat == "stars_2": s2 = max(0, s2 - 1)
                elif old_cat == "stars_1": s1 = max(0, s1 - 1)
                total = max(0, total - old_val)
                
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
                              WHERE member_name = ?""", 
                           (s6, s5, s4, s3, s2, s1, total, clean_name))
            conn.commit()
            success = True
        else:
            # إذا لم يكن موجوداً وتم التعديل، نقوم بإنشاء سجل جديد له مباشرة
            conn.close()
            return process_king_note(0, clean_name, new_note_content)
            
    except Exception as e:
        print(f"Error in update_king_note: {e}")
        success = False
    finally:
        try:
            conn.close()
        except:
            pass
        
    return success

def get_kings_ranking():
    conn = sqlite3.connect(DB_KINGS_NAME)
    cursor = conn.cursor()
    cursor.execute("""SELECT rowid, member_name, stars_6, stars_5, stars_4, stars_3, stars_2, stars_1, total_stars 
                      FROM kings_ranking 
                      ORDER BY total_stars DESC""")
    rows = cursor.fetchall()
    conn.close()
    return rows

def adjust_king_score(member_name, s6, s5, s4, s3, s2, s1):
    clean_name = member_name.strip()
    total = (s6 * 6) + (s5 * 5) + (s4 * 4) + (s3 * 3) + (s2 * 2) + (s1 * 1)
    
    conn = sqlite3.connect(DB_KINGS_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("""UPDATE kings_ranking 
                          SET stars_6 = ?, stars_5 = ?, stars_4 = ?, stars_3 = ?, stars_2 = ?, stars_1 = ?, total_stars = ? 
                          WHERE member_name = ?""", 
                       (s6, s5, s4, s3, s2, s1, total, clean_name))
        conn.commit()
        success = True
    except Exception as e:
        print(f"Error in adjust_king_score: {e}")
        success = False
    finally:
        conn.close()
    return success
