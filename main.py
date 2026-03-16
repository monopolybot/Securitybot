import os; os.system('pip install Pillow')
import random
import re
import asyncio
from datetime import datetime, timedelta
from telethon import TelegramClient, events, Button, types
from telethon.tl.types import ChatBannedRights  # هذا السطر الذي سيحل مشكلة الكتم والحظر
from database import db

# استدعاء المسار من القاعدة مباشرة
PROTECT_DIR = db.base_dir 

# --- بيانات الاعتماد الخاصة بالبوت ---
API_ID = 33183154
API_HASH = 'ccb195afa05973cf544600ad3c313b84'
# تأكد دائماً أن التوكن بين علامتي التنصيص بدون أي مسافات إضافية
BOT_TOKEN = '8654727197:AAGM3TkKoR_PImPmQ-rSe2lOcITpGMtTkxQ'
OWNER_ID = 5010882230
ALLOWED_GROUPS = [-1003791330278, -1003721123319, -1002052564369]

# تشغيل العميل (Client) - تم تغيير اسم الجلسة هنا لحل مشكلة السجل (Logs)
client = TelegramClient('Monopoly_Final_Fix_v21', API_ID, API_HASH, sequential_updates=True).start(bot_token=BOT_TOKEN)

# --- 1. دالة التصفير التلقائي الأسبوعي ---
async def weekly_auto_reset():
    """
    هذه الدالة تعمل في الخلفية بشكل دائم.
    تنتظر لمدة أسبوع كامل ثم تقوم بمسح بيانات التفاعل لتبدأ المسابقة من جديد.
    """
    while True:
        try:
            # الانتظار لمدة 7 أيام (بالثواني)
            await asyncio.sleep(604800) 
            
            # تنفيذ عملية الحذف من قاعدة البيانات
            db.cursor.execute("DELETE FROM activity")
            db.conn.commit()
            
            # إبلاغ المجموعات المسموحة بعملية التصفير
            for chat_id in ALLOWED_GROUPS:
                try:
                    text_reset = "🔄 **تنبيه ملكي من إدارة Monopoly**\n\nلقد مضى أسبوع من الحماس! تم تصفير عداد المتفاعلين الآن. ابدأوا رحلة الصعود للقمة من جديد! 🏆"
                    await client.send_message(chat_id, text_reset)
                except Exception as e_send:
                    print(f"فشل إرسال رسالة التصفير لـ {chat_id}: {e_send}")
        except Exception as e_reset:
            print(f"خطأ غير متوقع في نظام التصفير: {e_reset}")
            await asyncio.sleep(3600) # إعادة المحاولة بعد ساعة في حال حدوث خطأ

# --- 2. دالة الألقاب التفاعلية التراكمية ---
def get_user_title(count):
    """تحديد لقب العضو بناءً على عدد رسائله في المجموعة"""
    if count > 1000:
        return "سُلطان مونوبولي 🏆"
    elif count > 600:
        return "أسطورة التفاعل 👑"
    elif count > 300:
        return "متفاعل ذهبي 🥇"
    elif count > 150:
        return "صديق المجموعة 🤝"
    elif count > 50:
        return "متفاعل ناشئ ✨"
    else:
        return "عضو جديد 🌱"

# --- 3. دالة التحقق من الصلاحيات والرتب ---
async def check_privilege(event, required_rank):
    """التحقق الملكي: يربط الرتبة بالمجموعة الحالية"""
    if event.sender_id == OWNER_ID: return True
    current_gid = str(event.chat_id)
    # جلب الرتبة بناءً على (المجموعة واليوزر) معاً
    user_rank = db.get_rank(current_gid, event.sender_id)
    ranks_order = {"عضو": 0, "مميز": 1, "ادمن": 2, "مدير": 3, "مالك": 4, "المنشئ": 5}
    return ranks_order.get(user_rank, 0) >= ranks_order.get(required_rank, 0)
    
# --- 4. نظام الردود الملكية والذكية (الردود التلقائية) ---
@client.on(events.NewMessage(chats=ALLOWED_GROUPS))
async def reactive_replies(event):
    msg_text = event.raw_text
    user_id = event.sender_id
    group_id = str(event.chat_id)
    
    # جلب معلومات العضو للتفاعل الشخصي
    msg_count = db.get_user_messages(group_id, user_id)
    user_title = get_user_title(msg_count)
    is_admin = await check_privilege(event, "مدير")
    # الرد الملكي عند ذكر اسم أنس أو الرد عليه
    anas_names = ["انس", "أنس", "انس السلايطة", "المطور"]
    is_reply_to_anas = False
    if event.is_reply:
        rep_msg = await event.get_reply_message()
        if rep_msg.sender_id == OWNER_ID:
            is_reply_to_anas = True

    if any(name in msg_text for name in anas_names) or is_reply_to_anas:
        anas_responses = [
            "يا مرحبا ترحيبة البدو بالسيل.. ترحيبةٍ من جوف قلبٍ صدوُقِ. ☕️🐎",
            "الخيل والليل والبيداء تعرفنا.. والحق أبلج والباطل لجاجه. ⚔️🛡️",
            "استعن بالله ولا تعجز، فمن اعتمد على الله كفاه، ومن اعتز بغير الله ذل. ✨💎",
            "من اعتاد على القمة، لم يرضَ بغير السحاب موطناً.. نورت عرشك. 🦅👑",
            "ما كل من يركب على الخيل خيال.. ولا كل خيلٍ تعجبك هي أصيلة. 🐎📜",
            "كن كالنخيل عن الأحقاد مرتفعاً.. يُرمى بصخرٍ فيلقي أطيب الثمر. 🌴💎",
            "إذا هبّت رياحك فاغتنمها، فإن لكل خافقة سكون.. أهلاً بصانع الفرص. ⚙️🌬️",
            "يا ليتني من قـومٍ لا يجهلون.. مقام الكبار إذا حضروا وأقبلوا. 🎩⚔️",
            "تجري الرياح كما تجري سفينتنا.. نحن الرياح ونحن البحر والسفن. 🌊🚢",
            "لا يغير الله ما بقوم حتى يغيروا ما بأنفسهم.. طبت وطاب ممشاك . ✨📖"
        ]
        await event.reply(f"👑 **| تـرحـيـب مـلـكـي**\n━━━━━━━━━━━━━━\n✨ {random.choice(anas_responses)}\n━━━━━━━━━━━━━━")
        return

    # ردود كلمة (بوت) المتنوعة
    if msg_text == "بوت":
        bot_responses = [
            "لبيه! ✨", 
            f"نعم يا {user_title} 🌹", 
            "تفضل يا مديرنا الغالي 🫡", 
            "أمرك مطاع يا بطل مونوبولي", 
            "معك بوت مونوبولي في الخدمة 🛡️",
            "سمّ يا الأمير، كيف أخدمك؟",
            "أبشر بعزك, أنا هنا دائماً 🎩",
            "نعم يا طيب؟ أسمعك جيداً."
        ]
        await event.reply(random.choice(bot_responses))

    # الرد على السلام
    elif msg_text in ["السلام عليكم", "سلام عليكم", "سلام"]:
        if is_admin:
            await event.reply("👑 وعليكم السلام والرحمة يا سيادة المشرف الموقر! نورت المكان بوجودك.")
        else:
            await event.reply(f"وعليكم السلام والرحمة يا {user_title} نورتنا 🌹")

    # الرد على تحية الصباح
    elif "صباح الخير" in msg_text:
        if is_admin:
            await event.reply("صباح النور والسرور يا مطورنا/مديرنا الغالي 🌸")
        else:
            await event.reply(f"صباح الورد والجمال يا {user_title}! أتمنى لك يوماً رائعاً ☀️")

    # الرد على تحية المساء
    elif "مساء الخير" in msg_text:
        if is_admin:
            await event.reply("أجمل مساء لعيون الإدارة الموقرة 🌙")
        else:
            await event.reply(f"مساء النور والسرور يا {user_title} ✨ نورت المجموعة.")

    # --- الردود التلقائية الجديدة التي طلبتها ---
    elif msg_text in ["هههه", "ههههه", "هههههه"]:
        await event.reply(random.choice(["جعلها دوم هالضحكة! 😂", "ضحكتك تنور الجروب 🌸", "يا رب دائماً مبسوط ✨"]))
    elif msg_text == "منور":
        await event.reply(f"النور نورك يا {user_title} بنعكس عليك! 💡")
    elif msg_text in ["شكرا", "مشكور", "يسلمو"]:
        await event.reply(f"العفو يا طيب، واجبنا خدمتك دائماً 🌹")
    elif msg_text == "تصبح على خير":
        await event.reply(f"وأنت من أهل الخير يا {user_title}، أحلام سعيدة ونوم العوافي 💤")


        

async def get_target_info(event, parts):
    target_id = None
    target_user = None
    if event.is_reply:
        reply = await event.get_reply_message()
        target_id = reply.sender_id
        target_user = await reply.get_sender()
        return target_id, target_user
    
    # البحث عن اليوزر في الكلمة الثانية أو الثالثة (لدعم أوامر الفراغ)
    potential_inputs = []
    if len(parts) > 1: potential_inputs.append(parts[1])
    if len(parts) > 2: potential_inputs.append(parts[2])

    for input_data in potential_inputs:
        try:
            if input_data.isdigit():
                target_id = int(input_data)
                target_user = await client.get_entity(target_id)
                break
            elif input_data.startswith("@"):
                target_user = await client.get_entity(input_data)
                target_id = target_user.id
                break
        except Exception as e:
            continue
    return target_id, target_user

async def check_user_radar(user_id, current_name, current_username):
    user_id = str(user_id)
    old_data = db.get_user_from_radar(user_id)
    if old_data:
        old_name, old_username = old_data
        msg = None
        if str(current_name) != str(old_name):
            msg = f"🚨 **| رادار كـشـف الـهـويـة (تغيير اسم)**\n━━━━━━━━━━━━━━\n👤 **المستخدم:** [{current_name}](tg://user?id={user_id})\n🆔 **الآيدي:** `{user_id}`\n\n📜 **القديم:** {old_name}\n✨ **الجديد:** {current_name}\n━━━━━━━━━━━━━━"
        elif str(current_username) != str(old_username):
            msg = f"🚨 **| رادار كـشـف الـهـويـة (تغيير معرف)**\n━━━━━━━━━━━━━━\n👤 **المستخدم:** {current_name}\n🆔 **الآيدي:** `{user_id}`\n\n🔗 **القديم:** {old_username}\n✨ **الجديد:** {current_username}\n━━━━━━━━━━━━━━"
        if msg:
            for gid in ALLOWED_GROUPS:
                try: await client.send_message(int(gid), msg)
                except: continue
    db.sync_user_to_radar(user_id, current_name, current_username)
    
# --- 5. معالج الرسائل والأوامر الرئيسي ---
@client.on(events.NewMessage(chats=ALLOWED_GROUPS))
async def main_handler(event):
    message = event.raw_text
    chat_id = str(event.chat_id)
    sender_id = event.sender_id
    user = await event.get_sender()
    fn = f"{user.first_name} {user.last_name or ''}".strip()
    un = f"@{user.username}" if user.username else "لا يوجد"
    await check_user_radar(sender_id, fn, un)

    # 1. تسجيل التفاعل التراكمي
    if not event.is_private:
        db.increase_messages(chat_id, sender_id)

    # 2. نظام الردود المبرمجة (أضف رد) - الإصلاح الشامل للميديا
    custom_reply = db.get_reply_data(chat_id, message)
    if custom_reply:
        rep_text, media_id = custom_reply
        try:
            # التحقق مما إذا كان الرد يحتوي على ميديا (صورة أو ملصق)
            if media_id and str(media_id) != "None":
                # إرسال الميديا كـ File لضمان ظهور الصورة فوراً
                await client.send_file(event.chat_id, media_id, caption=rep_text if rep_text else "", reply_to=event.id)
                return
            elif rep_text:
                await event.reply(rep_text)
                return
        except Exception as e_media:
            if rep_text: await event.reply(rep_text)
            print(f"خطأ في إرسال الميديا المبرمجة: {e_media}")

    # 3. أمر "رتبتي" - لعرض تفاصيل العضو
    if message == "رتبتي":
        my_count = db.get_user_messages(chat_id, sender_id)
        my_title = get_user_title(my_count)
        # التعرف التلقائي على المالك الأساسي (أنس)
        my_rank = "مالك (مطور المشروع) 👑" if sender_id == OWNER_ID else db.get_rank(chat_id, sender_id)
        info_msg = (
            f"📋 **| الـهـويـة الـشـخـصـيـة**\n━━━━━━━━━━━━━━\n👤 **الاسـم:** {event.sender.first_name}\n🆔 **الـمـعـرف:** `{sender_id}`\n🎖️ **الـرتبـة:** {my_rank}\n🏆 **الـلـقـب:** {my_title}\n📈 **الـمـشاركات:** {my_count} رسـالة\n🕒 **الـتـوقيـت:** {datetime.now().strftime('%I:%M %p')}\n🛡️ **الـحـالـة:** مـتفاعل مـلكي ✅\n━━━━━━━━━━━━━━"
        )
        await event.reply(info_msg)
        return

    # 4. نظام "المتفاعلين" - لوحة الشرف الملكية
    if message == "المتفاعلين":
        top_list = db.get_top_active(chat_id, limit=5)
        if not top_list:
            await event.reply("📉 لا توجد بيانات تفاعل مسجلة حالياً.")
            return

        king_uid, king_msgs = top_list[0]
        try:
            king_entity = await client.get_entity(int(king_uid))
            king_name = king_entity.first_name
        except:
            king_name = "مستخدم غير معروف"

        sharaf_text = (
            f"🏆 **سُلطان التفاعل في Monopoly** 🏆\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"✨ **تهانينا لـ 'فارس الكلمة' لهذا الأسبوع!** ✨\n\n"
            f"👤 **المتفاعل الملك:** {king_name}\n"
            f"🆔 **الآيدي:** `{king_uid}`\n"
            f"📈 **رصيد المشاركات:** `{king_msgs}` رسالة ذهبية\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🎖️ **كلمة الإدارة:**\n"
            f"\"شكراً لكونك جزءاً فعالاً في عائلة مونوبولي.\"\n\n"
            f"💡 *ملاحظة: يتم تصفير العداد تلقائياً كل أسبوع!*"
        )
        await event.reply(sharaf_text)

    # 5. نظام "كشف" الإمبراطوري - يدعم الرد والآيدي والمعرف والأعضاء المغادرين
    if message.startswith("كشف"):
        parts = message.split()
        target_id = None
        target_user = None
        
        # الحالة 1: الكشف عبر الرد (Reply)
        if event.is_reply:
            reply_msg = await event.get_reply_message()
            target_id = reply_msg.sender_id
        # الحالة 2: الكشف عبر الآيدي أو المعرف (كشف 12345 أو كشف @anas)
        elif len(parts) > 1:
            input_data = parts[1]
            try:
                if input_data.isdigit():
                    target_id = int(input_data)
                elif input_data.startswith("@"):
                    target_user = await client.get_entity(input_data)
                    target_id = target_user.id
            except: pass
        
        if target_id:
            try:
                # محاولة جلب البيانات اللحظية من سيرفرات تليجرام
                if not target_user:
                    target_user = await client.get_entity(target_id)
                
                current_name = f"{target_user.first_name} {target_user.last_name or ''}".strip()
                current_un = f"@{target_user.username}" if target_user.username else "لا يوجد"
                
                # جلب البيانات القديمة من الرادار للمقارنة
                radar_data = db.get_user_from_radar(str(target_id))
                old_info_text = ""
                if radar_data:
                    old_name, old_un = radar_data
                    if old_name != current_name:
                        old_info_text += f"\n📜 **الاسـم الـقديم:** {old_name}"
                    if old_un != current_un:
                        old_info_text += f"\n🔗 **الـمعرف الـقديم:** {old_un}"
                
                # جلب الرتبة والمشاركات
                t_rank = "مالك 👑" if target_id == OWNER_ID else db.get_rank(chat_id, target_id)
                t_count = db.get_user_messages(chat_id, target_id)
                t_title = get_user_title(t_count)

                kashf_text = (
                    f"📋 **| كـشـف الـهـويـة الإمـبـراطـوري**\n━━━━━━━━━━━━━━\n"
                    f"👤 **الاسـم الـحالي:** {current_name}"
                    f"{old_info_text}\n"
                    f"🆔 **الآيدي:** `{target_id}`\n"
                    f"🔗 **الـمـعرف الحالي:** {current_un}\n"
                    f"🎖️ **الـرتبـة:** {t_rank}\n"
                    f"🏆 **الـلـقـب:** {t_title}\n"
                    f"📈 **الـمـشاركات:** {t_count} رسالة\n"
                    f"🕒 **الـتـوقيـت:** {datetime.now().strftime('%I:%M %p')}\n"
                    f"🛡️ **الـحـالـة:** مـراقب بـالرادار ✅\n━━━━━━━━━━━━━━"
                )
                await event.reply(kashf_text)
            except Exception as e:
                await event.reply("❌ **فشل الكشف:** لم أتمكن من العثور على هذا المستخدم في قاعدة بيانات تليجرام.")
        return

    # تحقق من صلاحيات الإدارة للأوامر القادمة
    if not await check_privilege(event, "ادمن"):
        return

    # 6. نظام "أضف رد" المطور (تم إصلاح منع تداخل الردود عبر التحقق من المشرف)
    if message == "اضف رد":
        try:
            async with client.conversation(event.chat_id, timeout=60) as conv:
                await conv.send_message("📝 **| مـرحـباً بـك يـا عطوفة الـمـديـر**\n━━━━━━━━━━━━━━\n✨ أرسل الآن **الكلمة أو الجملة** التي تود\nأن يستجيب لها النظام آلياً:\n━━━━━━━━━━━━━━")
                
                # نستخدم حلقة للتأكد من أن الرد من نفس المشرف الذي بدأ الأمر
                while True:
                    response_word = await conv.get_response()
                    if response_word.sender_id == sender_id:
                        word_to_save = response_word.text
                        break
                
                await conv.send_message(f"✅ **تم استلام الكلمة:** `{word_to_save}`\n━━━━━━━━━━━━━━\n🎬 الآن، أرسل **الرد الاداري** الذي تريده\n**(نص، صورة، ملصق، أو حتى متحركة):**\n━━━━━━━━━━━━━━")
                
                while True:
                    response_val = await conv.get_response()
                    if response_val.sender_id == sender_id:
                        media_to_save = response_val.media if response_val.media else None
                        db.set_reply(chat_id, word_to_save, response_val.text if response_val.text else "", media_to_save)
                        break
                
                await conv.send_message("👑 **| تـم تـحديث الـبروتوكول بـنجاح**\n━━━━━━━━━━━━━━\n💎 **تم حفظ الرد الجديد بنجاح.**\n🛡️ النظام الآن في حالة تأهب للرد على الجميع.\n━━━━━━━━━━━━━━")
        except asyncio.TimeoutError:
            await event.reply("⚠️ **| عـذراً يـا مـلك..**\nانتهى وقت الجلسة، يرجى إعادة المحاولة.")
            
    # --- أمر حذف رد الجديد (إصلاح مشكلة chat_id) ---
    if message == "حذف رد":
        try:
            async with client.conversation(event.chat_id, timeout=60) as conv:
                await conv.send_message("🗑️ **أهلاً بك يا مدير!**\nأرسل الآن **الكلمة** التي تريد حذف ردها المبرمج:")
                while True:
                    response_word = await conv.get_response()
                    if response_word.sender_id == sender_id:
                        try:
                            db.cursor.execute("DELETE FROM replies WHERE chat_id = ? AND word = ?", (chat_id, response_word.text))
                            db.conn.commit()
                        except:
                            db.cursor.execute("DELETE FROM replies WHERE gid = ? AND word = ?", (chat_id, response_word.text))
                            db.conn.commit()
                        break
                await conv.send_message(f"✅ تم حذف الرد على الكلمة '{response_word.text}' بنجاح.")
        except asyncio.TimeoutError:
            await event.reply("⚠️ انتهى الوقت.")

    # --- ميزة مسح الردود دفعة واحدة ---
    if message == "مسح الردود":
        try:
            # تم تصحيح الاستعلام ليمسح بناءً على رقم المجموعة فقط دون متغيرات خارجية
            db.cursor.execute("DELETE FROM replies WHERE gid = ?", (chat_id,))
            db.conn.commit()
            await event.reply("🗑️ **تم مسح كافة الردود المبرمجة لهذه المجموعة بنجاح.**")
        except Exception as e_del:
            print(f"خطأ في مسح الردود: {e_del}")
            # محاولة أخرى في حال كان اسم العمود في قاعدتك هو chat_id
            try:
                db.cursor.execute("DELETE FROM replies WHERE chat_id = ?", (chat_id,))
                db.conn.commit()
                await event.reply("🗑️ **تم مسح كافة الردود بنجاح (Database Fix).**")
            except:
                await event.reply("❌ فشل مسح الردود من قاعدة البيانات.")
                
    # --- [7] نظام التحكم الإمبراطوري (عقوبات + رتب) ---
    parts = message.split()
    if not parts: return
    
    cmd = parts[0]
    # دمج أول كلمتين للتعرف على أوامر الفراغ (مثل: الغاء الكتم)
    cmd_2nd = f"{parts[0]} {parts[1]}" if len(parts) >= 2 else cmd
    target_id, target_user = await get_target_info(event, parts)
    if target_id: 
        if target_id == OWNER_ID and sender_id != OWNER_ID:
            
            return 
        # بقية الأوامر تتبع شرط وجود target_id لكن خارج شرط الحصانة الملكية
        my_rank_val = db.get_rank_value(chat_id, sender_id)
        target_rank_val = db.get_rank_value(chat_id, target_id)
        t_name = target_user.first_name if target_user else str(target_id)
        rank_map = {"ادمن": 2, "مدير": 3, "مالك": 4, "مميز": 1}

        if cmd == "رفع":
            rank_name = next((p for p in parts if p in rank_map), None)
            if rank_name:
                if sender_id != OWNER_ID and my_rank_val <= rank_map[rank_name]:
                    return await event.respond("❌ لا تملك صلاحية لرفع هذه الرتبة.")
                for gid in ALLOWED_GROUPS: 
                    db.set_rank(str(gid), target_id, rank_name)
                return await event.respond(f"👑 **| 👑 إرادة مـلـكـيـة سـامـيـة 👑**\n━━━━━━━━━━━━━━\n📝 **الـقـرار:** تـرقيـة مـسـتـخـدم\n👤 **الـمـسـتـفيد:** {t_name}\n🎖️ **الـرتبـة الـجـديـدة:** {rank_name}\n━━━━━━━━━━━━━━")

        elif cmd == "تنزيل":
            if sender_id != OWNER_ID and my_rank_val <= target_rank_val:
                return await event.respond("❌ لا يمكنك تنزيل من هو برتبتك أو أعلى منك.")
            for gid in ALLOWED_GROUPS: 
                db.set_rank(str(gid), target_id, "عضو")
            return await event.respond(f"👑 **| 👑 قـرار إعـفـاء إداري 👑**\n━━━━━━━━━━━━━━\n📝 **الـقـرار:** سـحب الـصـلاحـيات\n👤 **الـمـسـتـخدم:** {t_name}\n📉 **الـرتبـة:** عـضـو\n━━━━━━━━━━━━━━")

        async def apply_penalty(rights, action_name):
            try:
                from telethon.tl.functions.channels import EditBannedRequest
                await client(EditBannedRequest(event.chat_id, target_id, rights))
                await event.respond(f"⚖️ **| ⚖️ مـحـكـمـة مـونـوبـولي الـعـلـيـا ⚖️**\n━━━━━━━━━━━━━━\n🛠️ **الإجـراء:** {action_name}\n👤 **الـمـسـتهـدف:** {t_name}\n✅ **الـحـالـة:** تـم تـنفيـذ الـحـكم\n━━━━━━━━━━━━━━")
            except Exception as e: 
                await event.respond(f"❌ فشل التنفيذ: {e}")


        # أوامر الإنذار
        if cmd == "انذار":
            w_count = db.add_warn(chat_id, target_id)
            if w_count >= 3:
                db.reset_warns(chat_id, target_id)
                await apply_penalty(ChatBannedRights(until_date=None, send_messages=True), "كتم تلقائي (بسبب بلوغ 3 إنذارات)")
            else:
                await event.respond(f"⚠️ **إنذار ملكي!**\nالعضو: {t_name}\nعدد إنذاراته الآن: {w_count}/3\n*عند الثالث سيتم كتمه تلقائياً.*")
        
        elif cmd_2nd == "رفع انذار":
            db.reset_warns(chat_id, target_id)
            await event.respond(f"✅ تم تصفير إنذارات {t_name}. فليكن هذا درساً له!")

        # أوامر العقوبات (بدون أندرسكور)
        if cmd == "حظر":
            await apply_penalty(ChatBannedRights(until_date=None, view_messages=True), "حظر")
        elif cmd == "كتم":
            await apply_penalty(ChatBannedRights(until_date=None, send_messages=True), "كتم")
        elif cmd == "تقييد":
            await apply_penalty(ChatBannedRights(until_date=None, send_media=True, send_stickers=True, send_gifs=True), "تقييد")
        elif cmd_2nd in ["الغاء الحظر", "رفع الحظر", "فك الحظر"]:
            await apply_penalty(ChatBannedRights(until_date=None, view_messages=False), "رفع الحظر عن")
        elif cmd_2nd in ["الغاء الكتم", "رفع الكتم", "فك الكتم"]:
            await apply_penalty(ChatBannedRights(until_date=None, send_messages=False), "رفع الكتم عن")
        elif cmd_2nd in ["الغاء القيود", "رفع القيود", "فك القيود"]:
            await apply_penalty(ChatBannedRights(until_date=None, send_media=False, send_stickers=False, send_gifs=False), "رفع القيود عن")


    # --- أوامر التفاعل المباشر (تثبيت/حذف) ---
    if event.is_reply:
        target_msg = await event.get_reply_message()
        if cmd == "تثبيت":
            await client.pin_message(event.chat_id, target_msg.id)
            await event.respond("📌 تم تثبيت الرسالة.")
        elif cmd == "حذف":
            await target_msg.delete()
            try: await event.delete()
            except: pass
    # --- [نظام الإذاعة الملكي الشامل] ---
    if message == "اذاعة" and event.is_reply:
        if not await check_privilege(event, "مدير"):
            return
            
        reply_msg = await event.get_reply_message()
        broadcast_count = 0
        status_msg = await event.reply("🚀 **جاري بدء الإذاعة الملكية لجميع المجموعات...**")
        
        for gid in ALLOWED_GROUPS:
            try:
                await client.send_message(int(gid), reply_msg)
                broadcast_count += 1
                await asyncio.sleep(0.5) 
            except Exception as e:
                print(f"فشل الإرسال للمجموعة {gid}: {e}")

        await status_msg.edit(f"✅ **تمت الإذاعة بنجاح!**\n━━━━━━━━━━━━━━\n📢 **المجموعات المستلمة:** {broadcast_count}\n🛡️ **المنفذ:** ༺۝༒♛ 🅰🅽🅰🆂 ♛༒۝༻\n━━━━━━━━━━━━━━")
        return # لإنهاء المعالجة هنا
        
    # 8. فتح لوحة الأوامر
    if message == "امر":
        buttons_list = [
            [Button.inline("🔒 الحماية", "show_locks"), Button.inline("🎖️ الرتب", "show_ranks")],
            [Button.inline("📜 الأوامر", "show_cmds"), Button.inline("❌ إغلاق", "close")]
        ]
        await event.respond("♥️ Monopoly مونوبولي لوحة تحكم ♥️", buttons=buttons_list)

# --- 6. نظام الترحيب والعمليات التلقائية ---
@client.on(events.ChatAction)
async def welcome_action(event):
    if event.user_joined or event.user_added:
        current_gid = str(event.chat_id)
        new_user = await event.get_user()
        
        # ترحيب خاص بالمطور أنس
        if new_user and new_user.id == OWNER_ID:
            await event.respond("👑 نورت المجموعة بطلتك يا مطورنا أنس! تحياتي.")
        elif new_user and db.get_setting(current_gid, "welcome_status") == "on":
            await event.respond(f"✨ نورت المجموعة يا {new_user.first_name}! ننتظر تفاعلك 🌹")

# --- استدعاء الموديولات المساعدة ---
import ranks, locks, tag, callbacks, monopoly_radar

# تشغيل المهمة الأسبوعية في الخلفية
client.loop.create_task(weekly_auto_reset())

# بدء التشغيل النهائي
print("--- [Monopoly System Online - V7.0 Royal Edition] ---")
print("--- [Status: Complete | Fixed Media & Delete Issues] ---")
client.loop.create_task(monopoly_radar.start_radar_system(client, ALLOWED_GROUPS))


# =========================================================
# --- [نظام رادار مونوبولي المطور: الإصدار 8.0 النهائي] ---
# =========================================================

@client.on(events.Raw(types.UpdateUser))
async def identity_tracker_radar(event):
    """صيد التغييرات التي تحدث في البروفايل مباشرة"""
    try:
        user_id = event.user_id
        user_full = await client.get_entity(user_id)
        fn = f"{user_full.first_name} {user_full.last_name or ''}".strip()
        un = f"@{user_full.username}" if user_full.username else "لا يوجد"
        # استدعاء المحرك الذي وضعناه في الأعلى للمقارنة
        await check_user_radar(user_id, fn, un)
    except: pass

async def identity_full_sync():
    """الجرد الموزع: يمنع التعليق تماماً عبر توزيع الجهد لضمان سلاسة الرد القصوى"""
    try: await client.send_message(OWNER_ID, "🚀 **الرادار الإمبراطوري يعمل بنمط 'التوزيع السلس'.. وداعاً للتعليق!**")
    except: pass
    
    while True:
        print("⏳ تبدأ الآن دورية الرادار السلسة (10 آلاف عضو)...", flush=True)
        for gid in ALLOWED_GROUPS:
            try:
                async for user in client.iter_participants(gid):
                    if user.bot: continue
                    
                    fn = f"{user.first_name} {user.last_name or ''}".strip()
                    un = f"@{user.username}" if user.username else "لا يوجد"
                    
                    # فحص الرادار ومقارنة الأسماء
                    await check_user_radar(user.id, fn, un)
                    
                    # --- السر في فك التعليق ---
                    # التوقف لمدة 0.1 ثانية بعد كل عضو يمنح البوت فرصة لمعالجة الرسائل الواردة فوراً
                    await asyncio.sleep(0.1) 
                        
            except Exception as e:
                print(f"⚠️ تنبيه: تعثر الرادار في مجموعة {gid}: {e}")
                continue
        
        print("✅ انتهت الجولة الشاملة بنجاح. الدورية القادمة بعد 15 دقيقة.", flush=True)
        # الاستراحة بين الدوريات (15 دقيقة) لراحة المعالج والحساب
        await asyncio.sleep(900)

# --- أوامر التشغيل النهائية لضمان عدم التكرار ---
client.loop.create_task(identity_full_sync())
print("--- [Monopoly System Online - V8.8 Ultra-Smooth Mode] ---", flush=True)
client.run_until_disconnected()
