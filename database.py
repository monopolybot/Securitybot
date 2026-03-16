import sqlite3
import pickle
import os

class BotDB:
    def __init__(self):
        # إعداد مسار التخزين (Northflank)
        self.base_dir = "/app/data"
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir, exist_ok=True)

        self.db_path = os.path.join(self.base_dir, "monopoly_royal.db")
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.conn.cursor() 
        self.create_tables()

    def create_tables(self):
        # إنشاء كافة الجداول المطلوبة دفعة واحدة
        self.cursor.execute('CREATE TABLE IF NOT EXISTS ranks (gid TEXT, uid TEXT, rank TEXT, PRIMARY KEY(gid, uid))')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS locks (gid TEXT, feature TEXT, status INTEGER DEFAULT 0, PRIMARY KEY(gid, feature))')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS replies (gid TEXT, word TEXT, reply TEXT, media_id BLOB DEFAULT NULL, PRIMARY KEY(gid, word))')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS settings (gid TEXT, key TEXT, value TEXT, PRIMARY KEY(gid, key))')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS activity (gid TEXT, uid TEXT, count INTEGER DEFAULT 0, PRIMARY KEY(gid, uid))')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS warns (gid TEXT, uid TEXT, count INTEGER DEFAULT 0, PRIMARY KEY(gid, uid))')
        
        # جدول الرادار الملكي
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS users_radar (
            uid TEXT PRIMARY KEY, 
            full_name TEXT, 
            username TEXT
        )''')
        self.conn.commit()

    # --- 1. إدارة الرتب ---
    def get_rank(self, gid, uid):
        self.cursor.execute("SELECT rank FROM ranks WHERE gid=? AND uid=?", (str(gid), str(uid)))
        row = self.cursor.fetchone()
        return row[0] if row else "عضو"

    def set_rank(self, gid, uid, rank_name):
        self.cursor.execute("INSERT OR REPLACE INTO ranks (gid, uid, rank) VALUES (?, ?, ?)", (str(gid), str(uid), rank_name))
        self.conn.commit()

    def get_rank_value(self, gid, uid):
        rank = self.get_rank(gid, uid)
        ranks_order = {"عضو": 0, "مميز": 1, "ادمن": 2, "مدير": 3, "مالك": 4, "المنشئ": 5}
        return ranks_order.get(rank, 0)

    # --- 2. إدارة التفاعل (التصفير الأسبوعي) ---
    def increase_messages(self, gid, uid):
        self.cursor.execute("INSERT OR IGNORE INTO activity (gid, uid, count) VALUES (?, ?, 0)", (str(gid), str(uid)))
        self.cursor.execute("UPDATE activity SET count = count + 1 WHERE gid=? AND uid=?", (str(gid), str(uid)))
        self.conn.commit()

    def get_user_messages(self, gid, uid):
        self.cursor.execute("SELECT count FROM activity WHERE gid=? AND uid=?", (str(gid), str(uid)))
        row = self.cursor.fetchone()
        return row[0] if row else 0

    def get_top_active(self, gid, limit=5):
        self.cursor.execute("SELECT uid, count FROM activity WHERE gid=? ORDER BY count DESC LIMIT ?", (str(gid), limit))
        return self.cursor.fetchall()

    # --- 3. إدارة الردود المبرمجة ---
    def set_reply(self, gid, word, reply_text, media_id=None):
        m_id = pickle.dumps(media_id) if media_id else None
        self.cursor.execute("INSERT OR REPLACE INTO replies (gid, word, reply, media_id) VALUES (?, ?, ?, ?)", (str(gid), word, reply_text, m_id))
        self.conn.commit()

    def get_reply_data(self, gid, word):
        self.cursor.execute("SELECT reply, media_id FROM replies WHERE gid=? AND word=?", (str(gid), word))
        row = self.cursor.fetchone()
        if row:
            rep_text = row[0]
            try:
                media = pickle.loads(row[1]) if row[1] else None
            except: media = None
            return rep_text, media
        return None

    # --- 4. إدارة الإنذارات والعقوبات ---
    def add_warn(self, gid, uid):
        self.cursor.execute("INSERT OR IGNORE INTO warns (gid, uid, count) VALUES (?, ?, 0)", (str(gid), str(uid)))
        self.cursor.execute("UPDATE warns SET count = count + 1 WHERE gid=? AND uid=?", (str(gid), str(uid)))
        self.conn.commit()
        return self.get_warns(gid, uid)

    def reset_warns(self, gid, uid):
        self.cursor.execute("DELETE FROM warns WHERE gid=? AND uid=?", (str(gid), str(uid)))
        self.conn.commit()

    def get_warns(self, gid, uid):
        self.cursor.execute("SELECT count FROM warns WHERE gid=? AND uid=?", (str(gid), str(uid)))
        row = self.cursor.fetchone()
        return row[0] if row else 0

    # --- 5. إدارة الأقفال (Locks) ---
    def set_lock(self, gid, feature, status):
        """status: 1 للفتح، 0 للقفل"""
        self.cursor.execute("INSERT OR REPLACE INTO locks (gid, feature, status) VALUES (?, ?, ?)", (str(gid), feature, status))
        self.conn.commit()

    def is_locked(self, gid, feature):
        self.cursor.execute("SELECT status FROM locks WHERE gid=? AND feature=?", (str(gid), feature))
        row = self.cursor.fetchone()
        return row[0] == 1 if row else False

    # --- 6. الإعدادات العامة (الترحيب) ---
    def set_setting(self, gid, key, value):
        self.cursor.execute("INSERT OR REPLACE INTO settings (gid, key, value) VALUES (?, ?, ?)", (str(gid), key, value))
        self.conn.commit()

    def get_setting(self, gid, key):
        self.cursor.execute("SELECT value FROM settings WHERE gid=? AND key=?", (str(gid), key))
        row = self.cursor.fetchone()
        return row[0] if row else "off"

        # --- 7. نظام الرادار الملكي (النسخة المحصنة) ---
    def sync_user_to_radar(self, uid, full_name, username):
        """تخزين البيانات مع التأكد من تحويل الآيدي لنص لضمان دقة المقارنة"""
        self.cursor.execute("INSERT OR REPLACE INTO users_radar (uid, full_name, username) VALUES (?, ?, ?)", 
                            (str(uid), str(full_name), str(username)))
        self.conn.commit()

    def get_user_from_radar(self, uid):
        """جلب البيانات مع تحويل الآيدي لضمان المطابقة"""
        self.cursor.execute("SELECT full_name, username FROM users_radar WHERE uid=?", (str(uid),))
        return self.cursor.fetchone()
    
db = BotDB()
