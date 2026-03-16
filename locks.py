import re
import io
from telethon import events
from database import db

# استدعاء الوظائف من الملف الرئيسي (تأكد أن الملف اسمه main.py أو app.py)
try:
    from __main__ import client, ALLOWED_GROUPS, check_privilege 
except ImportError:
    # حماية في حال التشغيل التجريبي
    client = None

# خريطة الميزات (عربي - إنجليزي)
FEATURES = {
    "الروابط": "links",
    "الصور": "photos",
    "الملصقات": "stickers",
    "المتحركة": "gifs",
    "التوجيه": "forward",
    "المعرفات": "usernames",
    "الفيديوهات": "videos",
    "البصمات": "voice",
    "الملفات": "files",
    "الجهات": "contacts",
    "الترحيب": "welcome_status"
}

# --- دوال الربط مع القاعدة (لحل النقص في database.py) ---
def is_locked(gid, feature):
    db.cursor.execute("SELECT status FROM locks WHERE gid=? AND feature=?", (str(gid), feature))
    row = db.cursor.fetchone()
    return row[0] == 1 if row else False

def toggle_lock(gid, feature, status):
    db.cursor.execute("INSERT OR REPLACE INTO locks (gid, feature, status) VALUES (?, ?, ?)", (str(gid), feature, status))
    db.conn.commit()

# --- 1. معالج الحماية التلقائي ---
@client.on(events.NewMessage(chats=ALLOWED_GROUPS))
async def auto_protection_handler(event):
    if not event.chat_id: return
    # استثناء الإدارة والمميزين
    if await check_privilege(event, "مميز"):
        return

    gid = str(event.chat_id)
    msg = event.raw_text or "" 

    try:
        # أ. فحص الروابط والمعرفات
        if is_locked(gid, "links"):
            if re.search(r'(https?://\S+|t\.me/\S+|www\.\S+|\S+\.(me|xyz|info))', msg):
                return await event.delete()

        if is_locked(gid, "usernames"):
            if re.search(r'@\S+', msg):
                return await event.delete()

        # ب. فحص الوسائط
        if event.photo and is_locked(gid, "photos"):
            return await event.delete()

        # ج. فحص باقي الأقفال
        checks = {
            "stickers": event.sticker,
            "gifs": event.gif,
            "forward": event.fwd_from,
            "videos": (event.video or event.video_note),
            "voice": event.voice,
            "contacts": event.contact,
            "files": event.document
        }
        
        for key, condition in checks.items():
            if condition and is_locked(gid, key):
                return await event.delete()

    except Exception as e:
        print(f"⚠️ خطأ في نظام الحماية: {e}")

# --- 2. أوامر التحكم اليدوي ---
@client.on(events.NewMessage(chats=ALLOWED_GROUPS))
async def locks_control_handler(event):
    msg = event.raw_text
    gid = str(event.chat_id)

    if not await check_privilege(event, "مدير"):
        return

    for ar_name, en_key in FEATURES.items():
        if msg == f"قفل {ar_name}":
            if en_key == "welcome_status":
                db.cursor.execute("INSERT OR REPLACE INTO settings (gid, key, value) VALUES (?, ?, ?)", (gid, en_key, "off"))
                db.conn.commit()
            else:
                toggle_lock(gid, en_key, 1)
            return await event.respond(f"🔒 تم قفل **{ar_name}** بنجاح.")
        
        elif msg == f"فتح {ar_name}":
            if en_key == "welcome_status":
                db.cursor.execute("INSERT OR REPLACE INTO settings (gid, key, value) VALUES (?, ?, ?)", (gid, en_key, "on"))
                db.conn.commit()
            else:
                toggle_lock(gid, en_key, 0)
            return await event.respond(f"🔓 تم فتح **{ar_name}** بنجاح.")

    # --- 3. أوامر السيطرة الجماعية ---
    if msg == "قفل الدردشة":
        try:
            await client.edit_permissions(event.chat_id, send_messages=False)
            await event.respond("🚫 **تم إغلاق الدردشة.**")
        except: await event.respond("❌ لا أملك صلاحيات كافية.")
            
    elif msg == "فتح الدردشة":
        try:
            await client.edit_permissions(event.chat_id, send_messages=True, send_media=True)
            await event.respond("✅ **تم فتح الدردشة.**")
        except: await event.respond("❌ فشل الفتح.")

    elif msg == "قفل الوسائط":
        for m in ["photos", "videos", "stickers", "gifs", "voice", "files"]:
            toggle_lock(gid, m, 1)
        await event.respond("🔒 **تم قفل كافة الوسائط.**")
        
    elif msg == "فتح الوسائط":
        for m in ["photos", "videos", "stickers", "gifs", "voice", "files"]:
            toggle_lock(gid, m, 0)
        await event.respond("🔓 **تم فتح كافة الوسائط.**")
