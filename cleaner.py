import asyncio
from telethon import events
from database import db
from __main__ import client, ALLOWED_GROUPS, check_privilege 

# --- [ نظام المسح والتطهير الملكي ] ---
@client.on(events.NewMessage(chats=ALLOWED_GROUPS))
async def cleaner_handler(event):
    if not event.raw_text: return
    msg = event.raw_text
    chat_id = event.chat_id

    # أمر مسح الرسائل (مثال: مسح 50)
    if msg.startswith("مسح ") or msg == "مسح":
        # التحقق من الصلاحية (أدمن فأعلى)
        if not await check_privilege(event, "ادمن"): 
            return

        try:
            parts = msg.split()
            # تحديد العدد المطلوبة مسحه (الافتراضي 10)
            num = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 10
            
            # حماية البوت: حد أدنى 1 وحد أقصى 100 لضمان استقرار الأداء
            num = max(1, min(num, 100)) 
            
            # حذف أمر المسح أولاً
            await event.delete() 
            
            # جلب الرسائل وحذفها بالجملة
            messages = await client.get_messages(chat_id, limit=num)
            if messages:
                await client.delete_messages(chat_id, messages)
                
                # رسالة تأكيد مؤقتة
                confirm = await event.respond(f"🗑️ **تم تطهير {len(messages)} رسالة من سجلات المملكة.**")
                
                # حذف رسالة التأكيد بعد 3 ثوانٍ
                await asyncio.sleep(3)
                await confirm.delete()
            
        except Exception as e:
            print(f"Cleaner Error: {e}")
            err_msg = await event.respond("❌ فشل نظام التطهير. تأكد من منحي صلاحية (حذف رسائل الآخرين).")
            await asyncio.sleep(3)
            await err_msg.delete()

    # --- ميزة تنظيف الحسابات المحذوفة (Ghost Accounts) ---
    elif msg == "تنظيف المحذوفين":
        if not await check_privilege(event, "مدير"):
            return
            
        status = await event.respond("🔍 جاري فحص الرعايا والبحث عن الحسابات المحذوفة...")
        count = 0
        try:
            async for user in client.iter_participants(chat_id):
                if user.deleted:
                    try:
                        # طرد الحساب المحذوف (Kick)
                        await client.kick_participant(chat_id, user)
                        count += 1
                    except: continue
            
            if count > 0:
                await status.edit(f"✅ تم طرد **{count}** من الحسابات المحذوفة بنجاح. المجموعة الآن أنقى!")
            else:
                await status.edit("✅ لم يتم العثور على أي حسابات محذوفة. المجموعة نظيفة تماماً!")
        except Exception as e:
            print(f"Cleaner Error (Deleted Users): {e}")
            await status.edit("❌ فشل الوصول لقائمة الأعضاء. تأكد من صلاحياتي الإدارية.")
