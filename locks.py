import re
import io
from telethon import events
from database import db

# استدعاء الوظائف من الملف الرئيسي
try:
    from __main__ import client, ALLOWED_GROUPS, check_privilege, OWNER_ID
except ImportError:
    client = None

# خريطة الميزات الكاملة (11 ميزة)
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

# --- دوال الربط مع القاعدة ---
def is_locked(gid, feature):
    try:
        db.cursor.execute("SELECT status FROM locks WHERE gid=? AND feature=?", (str(gid), feature))
        row = db.cursor.fetchone()
        return row[0] == 1 if row else False
    except:
        return False

def toggle_lock(gid, feature, status):
    db.cursor.execute("INSERT OR REPLACE INTO locks (gid, feature, status) VALUES (?, ?, ?)", (str(gid), feature, status))
    db.conn.commit()

# --- 1. معالج الحماية التلقائي الشامل ---
@client.on(events.NewMessage(chats=ALLOWED_GROUPS))
async def auto_protection_handler(event):
    if not event.chat_id or not event.sender_id: return
    
    # استثناء الإدارة والمميزين (المطور والمشرفين لا ينطبق عليهم الحذف)
    if await check_privilege(event, "مميز"):
        return

    gid = str(event.chat_id)
    
    # جلب النص الكامل (الرسالة + وصف الميديا) لضمان فحص الروابط المخفية
    text_content = event.raw_text or ""
    caption_content = event.raw_text or ""
    
    full_text = text_content + caption_content

    try:
        # أ. فحص الروابط المطوّر (تمت إضافة be و ly و link لليوتيوب والاختصارات)
        if is_locked(gid, "links"):
            link_pattern = r'(https?://\S+|t\.me/\S+|telegram\.me/\S+|www\.\S+|\S+\.(me|xyz|info|com|net|org|top|club|vip|online|shop|be|ly|link))'
            if re.search(link_pattern, full_text, re.IGNORECASE):
                await event.delete()
                w_count = db.add_warn(gid, event.sender_id)
                return await event.respond(f"⚠️ **مـمـنـوع نـشر الروابط!**\n👤 العضو: [{event.sender.first_name}](tg://user?id={event.sender_id})\n⚖️ إنذاراتك: ({w_count}/3)", delete_after=30)

        # ب. فحص المعرفات (@username)
        if is_locked(gid, "usernames"):
            if re.search(r'@\S+', full_text):
                return await event.delete()

        # ج. فحص باقي الأقفال (كاملة كما في ملفك الأصلي)
        checks = {
            "photos": event.photo,
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

# --- 2. أوامر التحكم اليدوي (قفل / فتح) ---
@client.on(events.NewMessage(chats=ALLOWED_GROUPS))
async def locks_control_handler(event):
    msg = event.raw_text
    gid = str(event.chat_id)

    # التحقق من أن المرسل مدير أو أعلى
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

    # --- 3. أوامر السيطرة الجماعية (كاملة) ---
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
