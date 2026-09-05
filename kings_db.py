import sqlite3

DB_KINGS_NAME = "monopoly_kings.db"

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

# تنفيذ التهيئة عند تشغيل الملف
init_kings_db()
