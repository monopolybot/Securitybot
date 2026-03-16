import io
from telethon import events
from database import db

# استيراد الـ hasher لحساب بصمة الصورة
try: 
    from hasher import get_image_hash
except: 
    get_image_hash = None

# استدعاء الأساسيات من الملف الرئيسي (تأكد من اسم ملف التشغيل)
try:
    from __main__ import client, ALLOWED_GROUPS, check_privilege 
except ImportError:
    client = None

@client.on(events.NewMessage(chats=ALLOWED_GROUPS))
async def ranks_manager_system(event):
    if not event.raw_text: return
    msg = event.raw_text
    gid = str(event.chat_id)

    # التحقق من الصلاحية (أدمن فأعلى مسموح له حظر الصور)
    if not await check_privilege(event, "ادمن"):
        return

    # --- 🛡️ ميزة حظر بصمة الصورة (Image Fingerprinting) ---
    if msg == "حظر صورة" and event.is_reply:
        reply_msg = await event.get_reply_message()
        
        if reply_msg and reply_msg.photo:
            if not get_image_hash:
                return await event.respond("❌ نظام التشفير (hasher.py) غير موجود أو معطل.")
                
            status_msg = await event.respond("🔍 جارِ فحص بصمة الصورة وحظرها ملكياً...")
            
            try:
                # 1. تحميل الصورة في الذاكرة (RAM) لسرعة المعالجة
                photo_bytes = await reply_msg.download_media(file=io.BytesIO())
                # 2. توليد البصمة (الهاش الفريد)
                img_hash = get_image_hash(photo_bytes)
                
                if img_hash:
                    # 3. إضافتها لجدول القائمة السوداء
                    db.cursor.execute("INSERT OR IGNORE INTO image_blacklist (hash) VALUES (?)", (img_hash,))
                    db.conn.commit()
                    
                    # 4. تنفيذ الحذف الفوري للصورة والرد
                    await reply_msg.delete()
                    await status_msg.edit("🚫 **تم حظر بصمة الصورة بنجاح!**\nلن يُسمح بتداولها في الممالك بعد الآن.")
                else:
                    await status_msg.edit("❌ لم نتمكن من استخراج بصمة رقمية لهذه الصورة.")
                
            except Exception as e:
                print(f"Error in Image Hash System: {e}")
                await status_msg.edit("❌ فشل النظام في معالجة البصمة الملكية.")
        else:
            await event.respond("⚠️ يا ملك، يجب أن ترد على (صورة) لكي أستطيع سحب بصمتها.")
