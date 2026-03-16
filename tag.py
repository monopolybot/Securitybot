import asyncio
from telethon import events, types
from database import db
# استيراد العناصر لضمان عدم حدوث Circular Import
from __main__ import client, ALLOWED_GROUPS, check_privilege 

# قاموس لتتبع عمليات التاغ الجارية لإمكانية إيقافها (Thread-safe)
active_tagging = {}

@client.on(events.NewMessage(chats=ALLOWED_GROUPS))
async def tag_handler(event):
    msg = event.raw_text
    chat_id = event.chat_id
    gid = str(chat_id)

    # التحقق من الصلاحية (مدير فأعلى لاستخدام المنشن الشامل)
    if not await check_privilege(event, "مدير"):
        return

    # --- 1. أمر بدء المنشن (تاغ للكل) ---
    if msg in ["تاغ", "منشن", "تاق", "كل"]:
        if active_tagging.get(gid, False):
            await event.respond("⚠️ هناك عملية **تاغ ملكية** جارية بالفعل! استخدم `ايقاف التاغ` أولاً.")
            return

        active_tagging[gid] = True
        await event.respond("📣 جاري بدء **المنشن الشامل**.. (يمكنك الإيقاف عبر: ايقاف التاغ)")

        try:
            # جلب الأعضاء (حد أقصى 500 عضو لضمان عدم استهلاك موارد الخادم)
            members = await client.get_participants(chat_id, limit=500)
            
            # تقسيم الأعضاء لضمان عدم اعتبار الرسالة سبام (5 أعضاء لكل رسالة)
            chunk_size = 5
            for i in range(0, len(members), chunk_size):
                # فحص هل تم طلب الإيقاف أثناء العملية؟
                if not active_tagging.get(gid, False):
                    break
                
                chunk = members[i:i + chunk_size]
                tag_msg = "📣 **نداء للملكة:**\n"
                for user in chunk:
                    if not user.bot:
                        tag_msg += f"▫️ [{user.first_name}](tg://user?id={user.id}) "
                
                if tag_msg != "📣 **نداء للملكة:**\n":
                    await client.send_message(chat_id, tag_msg)
                    # تأخير 2.5 ثانية (أمان أعلى لتجنب الـ Flood)
                    await asyncio.sleep(2.5)
            
            if active_tagging.get(gid):
                await event.respond("✅ تم اكتمال **المنشن الشامل** بنجاح.")
                active_tagging[gid] = False
        except Exception as e:
            print(f"Tag Error: {e}")
            active_tagging[gid] = False

    # --- 2. أمر إيقاف المنشن ---
    elif msg in ["ايقاف التاغ", "ايقاف المنشن", "وقف التاغ", "ايقاف"]:
        if active_tagging.get(gid, False):
            active_tagging[gid] = False
            await event.respond("🛑 تم **إيقاف** العملية بنجاح.")
        else:
            await event.respond("❌ لا توجد عملية نشطة حالياً.")

    # --- 3. أمر منشن المدراء ---
    elif msg in ["تاغ للمدراء", "منشن للمدراء", "ادمنيه"]:
        await event.respond("📢 استدعاء طاقم الإدارة الموقر...")
        admins = await client.get_participants(chat_id, filter=types.ChannelParticipantsAdmins())
        
        admin_tags = "👮‍♂️ **نداء عاجل للإدارة:**\n\n"
        for admin in admins:
            if not admin.bot:
                admin_tags += f"▫️ [{admin.first_name}](tg://user?id={admin.id})\n"
        
        await client.send_message(chat_id, admin_tags)
