import os; os.system('pip install Pillow')
import random
import re
import asyncio
from datetime import datetime, timedelta
from telethon import TelegramClient, events, Button, types
from telethon.tl.types import ChatBannedRights
from database import db
from telethon.tl.types import UpdateBotChatInviteRequester, UpdateNewChannelMessage, MessageService, MessageActionChatAddUser
from telethon import functions
from notes_manager import init_notes_db, manage_note
from kings_db import process_king_note, get_kings_ranking, adjust_king_score

# استدعاء المسار من القاعدة مباشرة
PROTECT_DIR = db.base_dir 

# --- بيانات الاعتماد الخاصة بالبوت ---
API_ID = 33183154
API_HASH = 'ccb195afa05973cf544600ad3c313b84'
BOT_TOKEN = '8654727197:AAFm9mBU83Q6lJro3NwUyfyM21_Ve54B4dM'
OWNER_ID = 5010882230

# --- قائمة المجموعات المسموحة المحدثة ---
ALLOWED_GROUPS = [
    -1004432647304,
    -1002052564369,
    -1004477090207,
    -1004400057155
]

# ⛔ الكلمات المحظورة (القائمة الشاملة)
BAD_WORDS = ["كلمة1", "كلمة2", "سكس", "إباحي", "زب", "كس", "طيز" ,"sex" ,"fuck" ,"dick" ,"pussy" ,"تنتاك", "إباحيه", "اباحيه", "إباحية", "اباحية", "خنيث", "مخنث", "زنوة", "عير", "فحل", "هالشرموطة", "هالشرموطه", "سكـس", "تعارف", "بزازك", "بز", "لحس", "مص", "زبر", "تمصيلي", "الحسلك", "انيك", "تنتاكي", "انيكك", "قحبة", "قحبه", "شرموطة", "شرموط", "شرموطه", "منيك", "منيوك", "تتناك", "منتاك", "منتاكة", "منتاكه", "كحب", "كحبة", "كحبه", "زبي", "زوبري", "زوبي", "عرص", "كسمك", "كوساومك", "كوس", "خول", "اير", "ايري", "سالب", "ديوث", "سحاقيه", "متناكه", "متناكة", "متناك", "سحاقية", "طيزك"] 

# تشغيل العميل (Client)
client = TelegramClient('Monopoly_Royal_Session_V100', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
init_notes_db()

# --- دالة جلب الرتبة الملكية ---
async def get_user_rank(chat_id, user_id):
    if user_id == OWNER_ID:
        return "المالك الأساسي 👑"
    try:
        from telethon.tl.functions.channels import GetParticipantRequest
        from telethon.tl.types import ChannelParticipantCreator, ChannelParticipantAdmin
        permissions = await client(GetParticipantRequest(channel=chat_id, participant=user_id))
        if isinstance(permissions.participant, ChannelParticipantCreator):
            return "منشئ المجموعة 🎖️"
        if isinstance(permissions.participant, ChannelParticipantAdmin):
            return "مشرف الإدارة 🛡️"
    except: pass
    return "عضو 👤"
    
# --- 1. دالة التصفير التلقائي الأسبوعي ---
async def weekly_auto_reset():
    while True:
        try:
            await asyncio.sleep(604800) 
            db.cursor.execute("DELETE FROM activity")
            db.conn.commit()
            for chat_id in ALLOWED_GROUPS:
                try:
                    text_reset = "🔄 **تنبيه ملكي من إدارة Monopoly**\n━━━━━━━━━━━━━━\nلقد مضى أسبوع من الحماس! تم تصفير عداد المتفاعلين الآن. ابدأوا رحلة الصعود للقمة من جديد! 🏆\n━━━━━━━━━━━━━━"
                    await client.send_message(chat_id, text_reset)
                except Exception as e_send:
                    print(f"فشل إرسال رسالة التصفير لـ {chat_id}: {e_send}")
        except Exception as e_reset:
            print(f"خطأ غير متوقع في نظام التصفير: {e_reset}")
            await asyncio.sleep(3600)

# --- 2. دالة الألقاب التفاعلية التراكمية ---
def get_user_title(count):
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
    if event.sender_id == OWNER_ID: return True
    current_gid = str(event.chat_id)
    user_rank = db.get_rank(current_gid, event.sender_id)
    ranks_order = {"عضو": 0, "مميز": 1, "ادمن": 2, "مدير": 3, "مالك": 4, "المنشئ": 5}
    return ranks_order.get(user_rank, 0) >= ranks_order.get(required_rank, 0)

# --- نظام الدرع الملكي والكشف الذكي المتقدم ---
def clean_text_refined(text):
    if not text: return ""
    # إزالة التشكيل والحروف المكررة والرموز لفحص دقيق للكلمات المحظورة
    search = ["أ", "إ", "آ", "ة", "_", "-", ".", "*", "!", "؟", "،", "\n", "ـ"]
    for s in search:
        text = text.replace(s, " ")
    text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ة", "ه")
    # إزالة الفراغات الزائدة لمعالجة الحروف المتقطعة
    text = re.sub(r'\s+', '', text)
    return text

@client.on(events.NewMessage(chats=ALLOWED_GROUPS))
async def anti_bad_words(event):
    if not event.raw_text or await check_privilege(event, "ادمن"):
        return

    gid = str(event.chat_id)
    full_text = event.raw_text
    
    from locks import is_locked 
    if is_locked(gid, "links"):
        link_pattern = r'(https?://\S+|t\.me/\S+|telegram\.me/\S+|www\.\S+|\S+\.(me|xyz|info|com|net|org|top|club|vip|online|shop|be|ly|link))'
        if re.search(link_pattern, full_text, re.IGNORECASE):
            try:
                await event.delete()
                w_count = db.add_warn(gid, event.sender_id)
                return await event.respond(f"⚠️ **مـمـنـوع نـشر الروابط!**\n━━━━━━━━━━━━━━\n👤 **العضو:** [{event.sender.first_name}](tg://user?id={event.sender_id})\n⚖️ **إنذاراتك:** `({w_count}/3)`\n━━━━━━━━━━━━━━", delete_after=15)
            except: pass

    # 2. فحص الكلمات البذيئة (تطبيق المحكمة العليا فوراً)
    cleaned_msg = clean_text_refined(full_text.lower())
    words_in_message = cleaned_msg.split()

    if any(word in words_in_message for word in BAD_WORDS):
        try:
            # الفتح الفوري للنيران (حذف + كتم + إنذار)
            await event.delete() 
            db.add_warn(gid, event.sender_id) # تسجيل الإنذار في القاعدة للأرشفة
            
            # تنفيذ الكتم الفوري (قفل الإرسال نهائياً)
            await client(functions.channels.EditBannedRequest(
                event.chat_id, event.sender_id, ChatBannedRights(until_date=None, send_messages=True)
            ))

            warn_txt = (
                f"⚠️ **تـنـبـيـه مـلـكـي حـازم (طرد من القروب)**\n━━━━━━━━━━━━━━\n"
                f"📖 **قال تعالى:**\n《 **مَّا يَلْفِظُ مِن قَوْلٍ إِلَّا لَدَيْهِ رَقِيبٌ عَتِيدٌ** 》\n━━━━━━━━━━━━━━\n"
                f"👤 **المخالف:** [{event.sender.first_name}](tg://user?id={event.sender_id})\n"
                f"🚫 **المخالفة:** تلفظ بكلمات محظورة\n"
                f"⚖️ **الإجراء:** كتم فوري + استدعاء الإدارة\n━━━━━━━━━━━━━━"
            )
            await event.respond(warn_txt)
            
            # 📢 إرسال أمر "مشرف" لتفعيل المنشن التلقائي الذي صنعته أنت
            await event.respond("مشرف") 
            
        except Exception as e:
            print(f"Error in Imperial Shield: {e}")
            

# --- 4. نظام الردود الملكية والذكية ---
@client.on(events.NewMessage(chats=ALLOWED_GROUPS))
async def reactive_replies(event):
    msg_text = event.raw_text
    user_id = event.sender_id
    group_id = str(event.chat_id)
    
    msg_count = db.get_user_messages(group_id, user_id)
    user_title = get_user_title(msg_count)
    is_admin = await check_privilege(event, "مدير")
    
    if msg_text == "بوت":
        bot_responses = [
            "👑 **لبيه!** ✨", f"👑 **نعم يا {user_title}** 🌹", "👑 **تفضل يا مديرنا الغالي** 🫡", 
            "👑 **أمرك مطاع يا بطل مونوبولي**", "👑 **معك بوت مونوبولي في الخدمة** 🛡️",
            "👑 **سمّ يا الأمير، كيف أخدمك؟**", "👑 **أبشر بعزك, أنا هنا دائماً** 🎩", "👑 **نعم يا طيب؟ أسمعك جيداً.**"
        ]
        await event.reply(random.choice(bot_responses))

    elif msg_text in ["السلام عليكم", "سلام عليكم", "سلام"]:
        if is_admin:
            await event.reply("👑 **وعليكم السلام والرحمة يا سيادة المشرف الموقر! نورت المكان بوجودك.**")
        else:
            await event.reply(f"👑 **وعليكم السلام والرحمة يا {user_title} نورتنا** 🌹")

    elif "صباح الخير" in msg_text:
        if is_admin:
            await event.reply("👑 **صباح النور والسرور يا مطورنا/مديرنا الغالي** 🌸")
        else:
            await event.reply(f"👑 **صباح الورد والجمال يا {user_title}! أتمنى لك يوماً رائعاً** ☀️")

    elif "مساء الخير" in msg_text:
        if is_admin:
            await event.reply("👑 **أجمل مساء لعيون الإدارة الموقرة** 🌙")
        else:
            await event.reply(f"👑 **مساء النور والسرور يا {user_title}** ✨ **نورت المجموعة.**")

    elif msg_text in ["هههه", "ههههه", "هههههه"]:
        await event.reply(random.choice(["👑 **جعلها دوم هالضحكة!** 😂", "👑 **ضحكتك تنور الجروب** 🌸", "👑 **يا رب دائماً مبسوط** ✨"]))
    elif msg_text == "منور":
        await event.reply(f"👑 **النور نورك يا {user_title} بنعكس عليك!** 💡")
    elif msg_text in ["شكرا", "مشكور", "يسلمو"]:
        await event.reply(f"👑 **العفو يا طيب، واجبنا خدمتك دائماً** 🌹")
    elif msg_text == "تصبح على خير":
        await event.reply(f"👑 **وأنت من أهل الخير يا {user_title}، أحلام سعيدة ونوم العوافي** 💤")

async def get_target_info(event, parts):
    target_id = None
    target_user = None
    
    if event.is_reply:
        reply = await event.get_reply_message()
        if reply and reply.sender_id:
            target_id = reply.sender_id
            try: target_user = await reply.get_sender()
            except: target_user = None
            return target_id, target_user
    
    potential_inputs = []
    if len(parts) > 1: potential_inputs.append(parts[1])
    if len(parts) > 2: potential_inputs.append(parts[2])

    for input_data in potential_inputs:
        try:
            if input_data.isdigit():
                target_id = int(input_data)
                try: target_user = await client.get_entity(target_id)
                except: target_user = None 
                break
            elif input_data.startswith("@"):
                target_user = await client.get_entity(input_data)
                target_id = target_user.id
                break
        except Exception as e:
            print(f"⚠️ تنبيه: {e}")
            continue
            
    return target_id, target_user

# --- 5. معالج الرسائل والأوامر الرئيسي ---
@client.on(events.NewMessage(chats=ALLOWED_GROUPS))
async def main_handler(event):
    message = event.raw_text
    chat_id = str(event.chat_id)
    sender_id = event.sender_id
    
    if not event.is_private:
        db.increase_messages(chat_id, sender_id)

    if message == "كشف" and event.is_reply:
        reply_msg = await event.get_reply_message()
        if reply_msg and reply_msg.sender_id:
            try:
                target_user = await client.get_entity(reply_msg.sender_id)
                t_rank = "مالك 👑" if target_user.id == OWNER_ID else db.get_rank(chat_id, target_user.id)
                t_count = db.get_user_messages(chat_id, target_user.id)
                t_title = get_user_title(t_count)
                t_time = datetime.now().strftime("%I:%M %p")
                
                kashf_text = (
                    f"📋 **| الـهـويـة الـشـخـصـيـة**\n━━━━━━━━━━━━━━\n"
                    f"👤 **الاسـم:** `{target_user.first_name}`\n"
                    f"🆔 **الـمـعـرف:** `{target_user.id}`\n"
                    f"🎖️ **الـرتبـة:** `{t_rank}`\n"
                    f"🏆 **الـلـقـب:** `{t_title}`\n"
                    f"📈 **الـمـشاركات:** `{t_count}` رسالة\n"
                    f"🕒 **الـتـوقيـت:** `{t_time}`\n"
                    f"🛡️ **الـحـالـة:** `سـجل نظيف ✅`\n━━━━━━━━━━━━━━"
                )
                await event.reply(kashf_text)
                return
            except Exception as e:
                print(f"Error in Kashf: {e}")

    if message == "رتبتي":
        my_count = db.get_user_messages(chat_id, sender_id)
        my_title = get_user_title(my_count)
        my_rank = "مالك (مطور المشروع) 👑" if sender_id == OWNER_ID else db.get_rank(chat_id, sender_id)
        info_msg = (
            f"📋 **| الـهـويـة الـشـخـصـيـة**\n━━━━━━━━━━━━━━\n"
            f"👤 **الاسـم:** `{event.sender.first_name}`\n"
            f"🆔 **الـمـعـرف:** `{sender_id}`\n"
            f"🎖️ **الـرتبـة:** `{my_rank}`\n"
            f"🏆 **الـلـقـب:** `{my_title}`\n"
            f"📈 **الـمـشاركات:** `{my_count}` رسـالة\n"
            f"🕒 **الـتـوقيـت:** `{datetime.now().strftime('%I:%M %p')}`\n"
            f"🛡️ **الـحـالـة:** `مـتفاعل مـلكي ✅`\n━━━━━━━━━━━━━━"
        )
        await event.reply(info_msg)
        return

    custom_reply = db.get_reply_data(chat_id, message)
    if custom_reply:
        rep_text, media_id = custom_reply
        try:
            if media_id and str(media_id) != "None":
                await client.send_file(event.chat_id, media_id, caption=rep_text if rep_text else "", reply_to=event.id)
                return
            elif rep_text:
                await event.reply(rep_text)
                return
        except Exception as e_media:
            if rep_text: await event.reply(rep_text)
            print(f"خطأ في الرد المبرمج: {e_media}")

    if message == "المتفاعلين":
        top_list = db.get_top_active(chat_id, limit=5)
        if not top_list:
            await event.reply("📉 **لا توجد بيانات تفاعل مسجلة حالياً.**")
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
            f"👤 **المتفاعل الملك:** `{king_name}`\n"
            f"🆔 **الآيدي:** `{king_uid}`\n"
            f"📈 **رصيد المشاركات:** `{king_msgs}` رسالة ذهبية\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🎖️ **كلمة الإدارة:**\n"
            f"\"شكراً لكونك جزءاً فعالاً في عائلة مونوبولي.\"\n\n"
            f"💡 *ملاحظة: يتم تصفير العداد تلقائياً كل أسبوع!*"
        )
        await event.reply(sharaf_text)

    if not await check_privilege(event, "ادمن"):
        return

    if message == "اضف رد":
        try:
            async with client.conversation(event.chat_id, timeout=60) as conv:
                await conv.send_message("📝 **| مـرحـباً بـك يـا عطوفة الـمـديـر**\n━━━━━━━━━━━━━━\n✨ **أرسل الآن الكلمة أو الجملة التي تود أن يستجيب لها النظام آلياً:**\n━━━━━━━━━━━━━━")
                while True:
                    response_word = await conv.get_response()
                    if response_word.sender_id == sender_id:
                        word_to_save = response_word.text
                        break
                
                await conv.send_message(f"✅ **تم استلام الكلمة:** `{word_to_save}`\n━━━━━━━━━━━━━━\n🎬 **الآن، أرسل الرد الاداري (نص، صورة، ملصق، أو متحركة):**\n━━━━━━━━━━━━━━")
                while True:
                    response_val = await conv.get_response()
                    if response_val.sender_id == sender_id:
                        media_to_save = response_val.media if response_val.media else None
                        db.set_reply(chat_id, word_to_save, response_val.text if response_val.text else "", media_to_save)
                        break
                
                await conv.send_message("👑 **| تـم تـحديث الـبروتوكول بـنجاح**\n━━━━━━━━━━━━━━\n💎 **تم حفظ الرد الجديد بنجاح.**\n🛡️ **النظام الآن في حالة تأهب للرد على الجميع.**\n━━━━━━━━━━━━━━")
        except asyncio.TimeoutError:
            await event.reply("⚠️ **| عـذراً يـا مـلك..**\nانتهى وقت الجلسة، يرجى إعادة المحاولة.")
            
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
                await conv.send_message(f"✅ **تم حذف الرد على الكلمة** `{response_word.text}` **بنجاح.**")
        except asyncio.TimeoutError:
            await event.reply("⚠️ **انتهى الوقت.**")

    if message == "مسح الردود":
        try:
            db.cursor.execute("DELETE FROM replies WHERE gid = ?", (chat_id,))
            db.conn.commit()
            await event.reply("🗑️ **تم مسح كافة الردود المبرمجة لهذه المجموعة بنجاح.**")
        except Exception as e_del:
            print(f"خطأ في مسح الردود: {e_del}")
            try:
                db.cursor.execute("DELETE FROM replies WHERE chat_id = ?", (chat_id,))
                db.conn.commit()
                await event.reply("🗑️ **تم مسح كافة الردود بنجاح (Database Fix).**")
            except:
                await event.reply("❌ **فشل مسح الردود من قاعدة البيانات.**")
                
    parts = message.split()
    if not parts: return
    
    cmd = parts[0]
    cmd_2nd = f"{parts[0]} {parts[1]}" if len(parts) >= 2 else cmd
    target_id, target_user = await get_target_info(event, parts)
    
    if target_id: 
        if target_id == OWNER_ID and sender_id != OWNER_ID:
            return

        my_rank_val = db.get_rank_value(chat_id, sender_id)
        target_rank_val = db.get_rank_value(chat_id, target_id)
        t_name = target_user.first_name if target_user else str(target_id)
        rank_map = {"ادمن": 2, "مدير": 3, "مالك": 4, "مميز": 1}

        if cmd == "رفع":
            rank_name = next((p for p in parts if p in rank_map), None)
            if rank_name:
                if sender_id != OWNER_ID and my_rank_val <= rank_map[rank_name]:
                    return await event.respond("❌ **لا تملك صلاحية لرفع هذه الرتبة.**")
                for gid in ALLOWED_GROUPS: 
                    db.set_rank(str(gid), target_id, rank_name)
                return await event.respond(f"👑 **| 👑 إرادة مـلـكـيـة سـامـيـة 👑**\n━━━━━━━━━━━━━━\n📝 **الـقـرار:** ترقية مستخدم\n👤 **المستفيد:** `{t_name}`\n🎖️ **الرتبة الجديدة:** `{rank_name}`\n━━━━━━━━━━━━━━")

        elif cmd == "تنزيل":
            if sender_id != OWNER_ID and my_rank_val <= target_rank_val:
                return await event.respond("❌ **لا يمكنك تنزيل من هو برتبتك أو أعلى منك.**")
            for gid in ALLOWED_GROUPS: 
                db.set_rank(str(gid), target_id, "عضو")
            return await event.respond(f"👑 **| 👑 قـرار إعـفـاء إداري 👑**\n━━━━━━━━━━━━━━\n📝 **القرار:** سحب الصلاحيات\n👤 **المستخدم:** `{t_name}`\n📉 **الرتبة:** `عضو`\n━━━━━━━━━━━━━━")

        async def apply_penalty(target_id, rights, action_name, is_kick=False):
            try:
                from telethon.tl.functions.channels import EditBannedRequest
                if is_kick:
                    await client(EditBannedRequest(event.chat_id, target_id, ChatBannedRights(until_date=None, view_messages=True)))
                    await client(EditBannedRequest(event.chat_id, target_id, ChatBannedRights(until_date=None, view_messages=False)))
                else:
                    await client(EditBannedRequest(event.chat_id, target_id, rights))
                
                display_name = target_user.first_name if (target_user and hasattr(target_user, 'first_name')) else f"المستخدم ({target_id})"
                
                await event.respond(
                    f"⚖️ **| ⚖️ مـحـكـمـة مـونـوبـولي الـعـلـيـا ⚖️**\n"
                    f"━━━━━━━━━━━━━━\n"
                    f"🛠️ **الإجـراء:** `{action_name}`\n"
                    f"👤 **الـمـسـتهـدف:** `{display_name}`\n"
                    f"✅ **الـحـالـة:** `تم تنفيذ الحكم`\n"
                    f"━━━━━━━━━━━━━━"
                )

                log_text = (
                    f"📜 **| تـقـريـر عـقـوبـة إداري**\n"
                    f"━━━━━━━━━━━━━━\n"
                    f"👤 **المنفذ:** [{event.sender.first_name}](tg://user?id={sender_id})\n"
                    f"🛠️ **الإجراء:** `{action_name}`\n"
                    f"👤 **المستهدف:** `{display_name}` (`{target_id}`)\n"
                    f"📍 **المصدر:** `{event.chat.title}`\n"
                    f"⏰ **التوقيت:** `{datetime.now().strftime('%I:%M %p')}`\n"
                    f"━━━━━━━━━━━━━━"
                )
                
                for log_gid in ALLOWED_GROUPS:
                    try: await client.send_message(log_gid, log_text)
                    except: pass

            except Exception as e: 
                await event.respond(f"❌ **فشل التنفيذ:** `{e}`")

        if cmd == "انذار":
            w_count = db.add_warn(chat_id, target_id)
            if w_count >= 3:
                db.reset_warns(chat_id, target_id)
                await apply_penalty(target_id, ChatBannedRights(until_date=None, send_messages=True), "كتم تلقائي (3 إنذارات)")
            else:
                await event.respond(f"⚠️ **إنذار ملكي!**\n━━━━━━━━━━━━━━\n👤 **العضو:** `{t_name}`\n⚖️ **عدد الإنذارات:** `({w_count}/3)`\n━━━━━━━━━━━━━━")
        
        elif cmd_2nd == "رفع انذار":
            db.reset_warns(chat_id, target_id)
            await event.respond(f"✅ **تم تصفير إنذارات المستخدم:** `{t_name}`")

        elif cmd == "حظر":
            await apply_penalty(target_id, ChatBannedRights(until_date=None, view_messages=True), "حظر نهائي")

        elif cmd == "طرد":
            await apply_penalty(target_id, None, "طرد من المجموعة", is_kick=True)

        elif cmd == "كتم":
            await apply_penalty(target_id, ChatBannedRights(until_date=None, send_messages=True), "كتم ملكي")

        elif cmd == "تقييد":
            await apply_penalty(target_id, ChatBannedRights(until_date=None, send_media=True, send_stickers=True, send_gifs=True, embed_links=True), "تقييد الوسائط")

        elif cmd_2nd in ["رفع القيود", "فك التقييد", "الغاء التقييد"]:
            await apply_penalty(target_id, ChatBannedRights(until_date=None, view_messages=False, send_messages=False, send_media=False, send_stickers=False, send_gifs=False, embed_links=False), "رفع كافة القيود")

        elif cmd_2nd in ["الغاء الحظر", "رفع الحظر", "فك الحظر"]:
            await apply_penalty(target_id, ChatBannedRights(until_date=None, view_messages=False), "رفع الحظر")

        elif cmd_2nd in ["الغاء الكتم", "رفع الكتم", "فك الكتم"]:
            await apply_penalty(target_id, ChatBannedRights(until_date=None, send_messages=False), "رفع الكتم")

    if event.is_reply:
        target_msg = await event.get_reply_message()
        if cmd == "تثبيت":
            await client.pin_message(event.chat_id, target_msg.id)
            await event.respond("📌 **تم تثبيت الرسالة بنجاح.**")
        elif cmd == "حذف":
            await target_msg.delete()
            try: await event.delete()
            except: pass

    if event.raw_text.startswith("اذاعة"):
        if not event.is_reply:
            return
            
        user_rank = await get_user_rank(event.chat_id, event.sender_id)
        if "عضو" in user_rank:
            return

        reply_msg = await event.get_reply_message()
        status_msg = await event.reply("🚀 **جاري البث الملكي وتثبيت الرسالة...**")
        
        broadcast_count = 0
        for gid in ALLOWED_GROUPS:
            try:
                sent_msg = await client.send_message(int(gid), reply_msg)
                try:
                    await client(functions.messages.UpdatePinnedMessageRequest(
                        peer=int(gid),
                        id=sent_msg.id,
                        silent=False
                    ))
                except Exception as e_pin:
                    print(f"فشل التثبيت في {gid}: {e_pin}")
                
                broadcast_count += 1
                await asyncio.sleep(0.5)
            except Exception as e_send:
                print(f"فشل الإرسال إلى {gid}: {e_send}")

        if broadcast_count > 0:
            await status_msg.edit(
                f"👑 **| تـم الـنـشـر والـتـثـبـيـت بـنـجـاح**\n"
                f"━━━━━━━━━━━━━━\n"
                f"📢 **عدد الممالك المستلمة:** `{broadcast_count}`\n"
                f"👤 **المنفذ:** `{user_rank}`\n"
                f"━━━━━━━━━━━━━━"
            )
        else:
            await status_msg.edit("❌ **عذراً.. فشلت عملية الإذاعة. تأكد من وجود البوت كمشرف في المجموعات.**")
        return

    if message == "امر":
        buttons_list = [
            [Button.inline("🔒 الحماية", "show_locks"), Button.inline("🎖️ الرتب", "show_ranks")],
            [Button.inline("📜 الأوامر", "show_cmds"), Button.inline("👑 الملوك", "show_kings_panel")],
            [Button.inline("❌ إغلاق", "close")]
        ]
        await event.respond("♥️ **Monopoly مونوبولي لوحة تحكم** ♥️", buttons=buttons_list)

# --- 6. نظام الترحيب والوداع الملكي ---
@client.on(events.ChatAction)
async def welcome_action(event):
    if event.chat_id not in ALLOWED_GROUPS: return
    
    ROYAL_PHOTO = "AgACAgQAAxkBAAMtaaI-Mn7PdCzJBmz-YjB23xDbnPwAAu0MaxuMGhhRKefZ-RH4mdIBAAMCAAN4AAM6BA"
    ROYAL_TEXT = (
        "👑 **شعب مونوبولي العظيم** 👑\n\n"
        "👈 **يمنع التبادل على الخاص** 👉\n\n"
        "⚡ **تجنباً لأي نصب واحتيال** ⚡\n\n"
        "🤝 **نرجوا إبلاغ أعضاء الإدارة عن أي**\n"
        "   ⛔ **شخص يقوم بتوزيع روابط** ⛔\n"
        " **جروبات أخرى عن طريق الخاص** 🤝\n\n"
        "نرجوا منكم التعاون معنا لكي نستطيع تقديم وتوفير لكم بيئة مناسبة وخالية من الجواسيس والروابط والنصابين.\n\n"
        "👑 **الجروب جروبكم ونحن بخدمتكم** 👑\n\n"
        "💥 **دمتم بخير وبحفظ الله ورعايته** 💥"
    )

    if event.user_joined or event.user_added or event.user_left or event.user_kicked:
        try:
            await client.send_file(event.chat_id, ROYAL_PHOTO, caption=ROYAL_TEXT)
            try: await event.delete()
            except: pass
        except Exception as e:
            print(f"Error in Royal Welcome: {e}")

async def hourly_royal_broadcast():
    TARGET_GROUP = -1002052564369
    BROADCAST_TEXT = (
        "♥️ **شعب مونوبولي العظيم** ♥️\n\n"
        "👈 **يمنع التبادل على الخاص** 👉\n\n"
        "⚡ **تجنباً لأي نصب واحتيال** ⚡\n\n"
        "🤝 **نرجوا إبلاغ أعضاء الإدارة عن أي**\n\n"
        "   ⛔ **شخص يقوم بتوزيع روابط** ⛔\n\n"
        " **قروبات أخرى عن طريق الخاص** 🤝\n\n"
        "نرجوا منكم التعاون معنا لكي نستطيع تقديم وتوفير لكم بيئة مناسبة وخالية من الجواسيس والروابط والنصابين \n\n"
        "👑 **الجروب جروبكم ونحن بخدمتكم** 👑\n\n"
        "💥 **دمتم بخير وبحفظ الله ورعايته** 💥"
    )
    
    while True:
        try:
            await client.send_message(TARGET_GROUP, BROADCAST_TEXT)
            await asyncio.sleep(3600)
        except Exception as e:
            print(f"⚠️ خطأ في الإذاعة الدورية: {e}")
            await asyncio.sleep(60)

import locks
import ranks
import callbacks
import monopoly_radar

client.loop.create_task(weekly_auto_reset())
client.loop.create_task(hourly_royal_broadcast())

user_edit_state = {}

async def send_notes_page(event, notes, page):
    page_size = 5
    total_pages = (len(notes) + page_size - 1) // page_size
    start = page * page_size
    end = start + page_size
    page_notes = notes[start:end]
    
    report = f"👑 **سجل المفكرة (صفحة {page + 1}/{total_pages}):**\n━━━━━━━━━━━━━━\n"
    report += "\n".join([f"⚜️ {start + i + 1}. 👤 `{n[0]}`" for i, n in enumerate(page_notes)])
    report += "\n━━━━━━━━━━━━━━"
    
    buttons = []
    nav_buttons = []
    if page > 0: nav_buttons.append(Button.inline("⏪ رجوع", f"page_{page-1}"))
    if page < total_pages - 1: nav_buttons.append(Button.inline("التالي ⏩", f"page_{page+1}"))
    
    if nav_buttons: buttons.append(nav_buttons)
    buttons.append([Button.inline("❌ إغلاق", "close")])
    
    if isinstance(event, events.CallbackQuery.Event):
        await event.edit(report, buttons=buttons)
    else:
        await event.reply(report, buttons=buttons)








@client.on(events.NewMessage(chats=ALLOWED_GROUPS))
async def handle_notes_system(event):
    if not await check_privilege(event, "ادمن"): return
    text, sender_id = event.raw_text, event.sender_id

    if sender_id in user_edit_state:
        state = user_edit_state[sender_id]
        if text == "إلغاء":
            del user_edit_state[sender_id]
            await event.reply("🚫 **تم إلغاء العملية بنجاح.**")
            return

        if state["step"] == "wait_index":
            if not text.isdigit():
                await event.reply("❌ **خطأ:** يرجى إرسال **رقم الملاحظة** فقط.")
                return
            if state["action"] == "del":
                res = manage_note("delete_by_index", (state["name"], text))
                del user_edit_state[sender_id]
                await event.reply("✅ **تم الحذف بنجاح.**" if res == "success" else "❌ **خطأ:** رقم الملاحظة غير صحيح.")
            else:
                user_edit_state[sender_id].update({"index": text, "step": "wait_note"})
                await event.reply("✍️ **تم استلام الرقم.**\n━━━━━━━━━━━━━━\n**الآن أرسل الملاحظة الجديدة:**\n━━━━━━━━━━━━━━")
            return
        elif state["step"] == "wait_note":
            res = manage_note("edit_by_index", (state["name"], state["index"], text))
            del user_edit_state[sender_id]
            await event.reply("✅ **تم التعديل بنجاح.**" if res == "success" else "❌ **خطأ في التعديل.**")
            return

    if text.startswith("تسجيل ملاحظة"):
        try:
            content_part = text.replace("تسجيل ملاحظة", "").strip()
            name, note = content_part.split(":")
            clean_name = name.strip()
            clean_note = note.strip()
            
            manage_note("add", (clean_name, clean_note, sender_id))
            process_king_note(sender_id, clean_name, clean_note)
            
            await event.reply(f"👑 **| تـم الـحـفـظ بـنـجـاح**\n━━━━━━━━━━━━━━\n👤 **العضو/الاسم:** `{clean_name}`\n📌 **تمت الإضافة للمفكرة وقائمة ملوك المجموعة**\n━━━━━━━━━━━━━━")
        except: 
            await event.reply("❌ **خطأ في التنسيق.**\n━━━━━━━━━━━━━━\n(الصيغة الصحيحة: `تسجيل ملاحظة الاسم : النص`)\n━━━━━━━━━━━━━━")

    elif text == "عرض المفكرة":
        notes = manage_note("get_active")
        if not notes: return await event.reply("📜 **المفكرة فارغة حالياً.**")
        await send_notes_page(event, notes, 0)
        
    elif text in ["ملوك", "قائمة الملوك"]:
        rows = get_kings_ranking()
        if not rows:
            await event.reply("📉 **لا توجد سجلات ملكية للنجوم حالياً.**")
            return
        
        kings_text = "👑 **| قـائمة مـلـوك مونوبولي (سجل النجوم)**\n━━━━━━━━━━━━━━━━━━\n"
        for idx, row in enumerate(rows, start=1):
            name = row[1]
            s6, s5, s4, s3, s2, s1 = row[2], row[3], row[4], row[5], row[6], row[7]
            total = row[8]
            
            medal = "🥇" if idx == 1 else ("🥈" if idx == 2 else ("🥉" if idx == 3 else f"`#{idx}`"))
            kings_text += f"{medal} **{name}**\n"
            kings_text += f"   ✨ مجموع النجوم: `{total}` (⭐6:{s6} | ⭐5:{s5} | ⭐4:{s4} | ⭐3:{s3} | ⭐2:{s2} | ⭐1:{s1})\n"
            kings_text += "----------------------------------\n"
            
        kings_text += "━━━━━━━━━━━━━━━━━━\n💡 **استمروا في جمع النجوم للتربع على القمة!**"
        await event.reply(kings_text)
        return





    elif text.startswith("بحث ملاحظة"):
        name = text.replace("بحث ملاحظة", "").strip()
        results = manage_note("search", name)
        if not results: return await event.reply("🔍 **لا يوجد ملف مسجل بهذا الاسم.**")
        msg = f"👑 **ملف العضو: {name}**\n━━━━━━━━━━━━━━\n" + "\n".join(
            [f"⚜️ {i}. `{r[1]}` \n   ⏳ *{r[2]}*\n" for i, r in enumerate(results, 1)]
        ) + "━━━━━━━━━━━━━━"
        buttons = [[Button.inline("⚙️ تعديل", f"edit_{name}"), Button.inline("🗑️ حذف", f"del_{name}")], [Button.inline("❌ إغلاق", "close")]]
        await event.reply(msg, buttons=buttons)

    elif text.startswith("حذف ملاحظة"):
        name = text.replace("حذف ملاحظة", "").strip()
        res = manage_note("delete_all", name)
        await event.reply(f"🗑️ **تم مسح الملف الملكي لـ:** `{name}`" if res == "success" else "❌ **الاسم غير موجود في السجلات.**")

@client.on(events.CallbackQuery(data=lambda d: d.startswith(b"edit_") or d.startswith(b"del_") or d.startswith(b"page_") or d.startswith(b"kpage_")))
async def callback_handler(event):
    data = event.data.decode()
    if data.startswith("page_"):
        page = int(data.split("_")[1])
        notes = manage_note("get_active")
        await send_notes_page(event, notes, page)
    elif data.startswith("kpage_"):
        page = int(data.split("_")[1])
        kings = get_kings_ranking()
        await send_kings_page(event, kings, page)
    elif data == "show_kings_panel":
        kings = get_kings_ranking()
        if not kings:
            await event.answer("قائمة الملوك فارغة حالياً!", alert=True)
            return
        await send_kings_page(event, 0)

    else:
        action, name = data.split("_")
        user_edit_state[event.sender_id] = {"name": name, "action": action, "step": "wait_index"}
        await event.edit(f"👑 **{action.upper()} ملاحظة للعضو {name}**\n━━━━━━━━━━━━━━\n**أرسل الآن رقم الملاحظة:**\n━━━━━━━━━━━━━━")

@client.on(events.NewMessage(func=lambda e: e.is_private))
async def private_chat_handler(event):
    if event.sender and event.sender.bot:
        return
        
    sender_name = event.sender.first_name if event.sender else "صديقي"
    
    private_response = (
        f"👑 **أهلاً بك يا {sender_name} في بوت قروب مونوبولي!** 👑\n\n"
        f"━━━━━━━━━━━━━━\n"
        f"🤖 **أنا بوت إدارة إمبراطورية مونوبولي في الخدمة.**\n"
        f"📌 يرجى العلم أن الأوامر التفاعلية (مثل التاغ، الكشف، والردود) تعمل حصرياً داخل **المجموعات المسموحة** للإمبراطورية.\n\n"
        f"💬 **للتواصل مع المطور:** `@A_N505`\n\n"
        f"༺۝༒♛ 🅰🅽🅰🆂 ♛༒۝༻\n"
        f"━━━━━━━━━━━━━━"
    )
    
    await event.reply(private_response)

from tag import setup_tag_handler
setup_tag_handler(client, ALLOWED_GROUPS, check_privilege, OWNER_ID)
    
print("--- [Monopoly System Online - V7.0 Royal Edition] ---")
print("--- [Status: Complete with Advanced Shield] ---")
client.loop.create_task(monopoly_radar.start_radar_system(client, ALLOWED_GROUPS))

client.run_until_disconnected()
