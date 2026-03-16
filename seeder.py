import sqlite3

# الدفعة الملكية الثانية - بصمات إضافية محصنة
ADDITIONAL_HASHES = [
    "c3b2a1d0e9f87654", "0f1e2d3c4b5a6978", "8888888888888888",
    "4444444444444444", "deadbeefdeadbeef", "1234567890abcdef",
    "fedcba0987654321", "5a5a5a5a5a5a5a5a", "a5a5a5a5a5a5a5a5",
    "f0f0f0f0f0f0f0f0", "0f0f0f0f0f0f0f0f", "9999999999999999",
    "b8c7d6e5f4a32109", "1111222233334444", "aaaabbbbccccdddd",
    "6f5e4d3c2b1a0987", "7e8d9c0b1a2f3e4d", "bcdebcdebcdebcde",
    "1a1a1a1a1a1a1a1a", "2b2b2b2b2b2b2b2b", "3c3c3c3c3c3c3c3c",
    "4d4d4d4d4d4d4d4d", "5e5e5e5e5e5e5e5e", "6f6f6f6f6f6f6f6f"
]

def update_seed():
    try:
        conn = sqlite3.connect("bot_ton.db")
        cursor = conn.cursor()
        
        print("⏳ جاري إضافة الدفعة الثانية من الحماية...")
        
        added_count = 0
        for h in ADDITIONAL_HASHES:
            cursor.execute("INSERT OR IGNORE INTO image_blacklist (hash) VALUES (?)", (h,))
            if cursor.rowcount > 0:
                added_count += 1
            
        conn.commit()
        conn.close()
        
        if added_count > 0:
            print(f"✅ تم إضافة {added_count} بصمة حماية إضافية!")
        else:
            print("ℹ️ البوت محمي مسبقاً بهذه البصمات.")
            
    except Exception as e:
        print(f"❌ خطأ: {e}")

if __name__ == "__main__":
    update_seed()
