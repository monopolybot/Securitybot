import asyncio
from telethon import events, types
from database import db

# ملاحظة: يتم ربط الـ client لاحقاً أو استيراده بأمان دون دورة دائرية
# سنقوم بتصدير الدالة وتفعيلها عبر main مباشرة أو تعريفها كالتالي:

def setup_tag_handler(client, ALLOWED_GROUPS, check_privilege, OWNER_ID):
    active_tagging = {}

    @client.on(events.NewMessage(chats=ALLOWED_GROUPS))
    async def tag_handler(event):
        msg = event.raw_text
        chat_id = event.chat_id
        gid = str(chat_id)

        # التحقق من الصلاحية (مدير فأعلى لاستخدام المنشن الشامل)
        if not await check_privilege(event, "ادمن"):
            return

        # --- 1. أمر بدء المنشن (تاغ للكل بالترتيب الملكي) ---
        if msg in ["تاغ", "منشن", "تاق", "كل"]:
            if active_tagging.get(gid, False):
                await event.respond("⚠️ هناك عملية **تاغ ملكية** جارية بالفعل! استخدم `ايقاف التاغ` أولاً.")
                return

            active_tagging[gid] = True
            await event.respond("📣 جاري بدء **المنشن الشامل الملكي**.. (يمكنك الإيقاف عبر: ايقاف التاغ)")

            try:
                # 1. جلب المالك الأساسي وتجهيزه ليكون أول من يتم عمل منشن له ومنفصل
                owner_entity = None
                try:
                    owner_entity = await client.get_entity(OWNER_ID)
                except:
                    pass

                # 2. جلب المشرفين في المجموعة
                admins = await client.get_participants(chat_id, filter=types.ChannelParticipantsAdmins())
                
                # 3. جلب كافة أعضاء المجموعة (حد أقصى 500)
                all_members = await client.get_participants(chat_id, limit=500)
                
                # تصفية وفصل القوائم بدقة
                admin_ids = {a.id for a in admins}
                regular_members = [u for u in all_members if u.id != OWNER_ID and u.id not in admin_ids and not u.bot]
                admin_list = [a for a in admins if a.id != OWNER_ID and not a.bot]

                # --- الخطوة الأولى: منشن المالك منفصلاً لوحده في البداية ---
                if owner_entity and active_tagging.get(gid, False):
                    owner_msg = f"👑 **سلطان الإمبراطورية (المالك):**\n▫️ [{owner_entity.first_name}](tg://user?id={owner_entity.id})"
                    await client.send_message(chat_id, owner_msg)
                    await asyncio.sleep(2.0)

                # --- الخطوة الثانية: منشن المشرفين جماعةً ---
                if admin_list and active_tagging.get(gid, False):
                    admin_msg = "🛡️ **طاقم الإدارة الموقر:**\n"
                    for admin in admin_list:
                        admin_msg += f"▫️ [{admin.first_name}](tg://user?id={admin.id}) "
                    await client.send_message(chat_id, admin_msg)
                    await asyncio.sleep(2.0)

                # --- الخطوة الثالثة: منشن الأعضاء مقسمين لدفعات لتجنب السبام ---
                chunk_size = 5
                for i in range(0, len(regular_members), chunk_size):
                    if not active_tagging.get(gid, False):
                        break
                    
                    chunk = regular_members[i:i + chunk_size]
                    tag_msg = "📣 **نداء لشعب مونوبولي:**\n"
                    for user in chunk:
                        tag_msg += f"▫️ [{user.first_name}](tg://user?id={user.id}) "
                    
                    if tag_msg != "📣 **نداء لشعب مونوبولي:**\n":
                        await client.send_message(chat_id, tag_msg)
                        # تأخير 2.5 ثانية (أمان أعلى لتجنب الـ Flood)
                        await asyncio.sleep(2.5)
                
                if active_tagging.get(gid):
                    await event.respond("✅ تم اكتمال **المنشن الشامل الملكي** بنجاح.")
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
