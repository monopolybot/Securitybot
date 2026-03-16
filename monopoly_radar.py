import sqlite3
import asyncio
import re
import io
from telethon import events, Button, types
from PIL import Image

# --- [1] إعداد قاعدة البيانات الشاملة ---
db_radar = sqlite3.connect("radar_storage.db", check_same_thread=False)
cursor_radar = db_radar.cursor()
cursor_radar.execute('''CREATE TABLE IF NOT EXISTS radar_requests 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      uid TEXT, 
                      name TEXT, 
                      dice INTEGER, 
                      type TEXT, 
                      status TEXT DEFAULT 'open',
                      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
db_radar.commit()

active_sessions = {}

async def start_radar_system(client, ALLOWED_GROUPS):
    
    # --- [2] أمر الإعلان الرسمي ---
    @client.on(events.NewMessage(chats=ALLOWED_GROUPS, pattern='^رادار الشركاء$'))
    async def radar_info(event):
        info_msg = (
            "🎰 **ملكي: إطلاق رادار شركاء Monopoly الجديد!** 🎰\n\n"
            "يا أبطال مونوبولي، لأن وقتكم ثمين وجوائزكم لا تعوض، قمنا بتطوير نظام \"الرادار الذكي\" الأول من نوعه لإدارة فعاليات الشركاء داخل مجموعتنا.\n\n"
            "**ماذا يقدم لك الرادار؟**\n"
            "بدلاً من الضياع في آلاف الرسائل، الرادار هو \"الوسيط الملكي\" الذي يربطك بالشريك المناسب لك بضغطة زر واحدة.\n\n"
            "🛠️ **كيفية الاستخدام في 3 خطوات:**\n"
            "1️⃣ **نادي الرادار:** أرسل كلمة (رادار) في القروب.\n"
            "2️⃣ **حدد هدفك:** ستظهر لك لوحة خيارات:\n"
            "   ⚖️ **مساهمة 50/50:** للعمل المتكافئ بين الطرفين.\n"
            "   🎁 **عرض مساعدة:** إذا كنت تملك نردًا فائضًا وتريد ختم مقعد كامل لشخص آخر (كرم الملوك).\n"
            "   🆘 **طلب مساعدة:** إذا كنت تحتاج لشخص يختم لك المقعد بسبب نقص النرد.\n"
            "3️⃣ **سجل قوتك:** أرسل عدد نردك الحالي وصورة (سكرين) للتحقق.\n\n"
            "🔗 **لحظة التطابق والربط (المنشن):**\n"
            "بمجرد وجود طرفين متوافقين، سيقوم البوت بعمل منشن (Tag) علني للطرفين في القروب.\n"
            "🚀 **جربوا الرادار الآن، وبشرونا بالختم والجوائز!**\n\n"
            "👑 **تحيات الإدارة والمطور: Anas S. Alsalayta**"
        )
        msg = await event.reply(info_msg)
        try: await msg.pin()
        except: pass

    # --- [3] لوحة التحكم للإدارة ---
    @client.on(events.NewMessage(chats=ALLOWED_GROUPS, pattern='^تحكم الرادار$'))
    async def admin_radar_panel(event):
        query = """SELECT 
            (SELECT count(*) FROM radar_requests WHERE status='open' AND type='50'),
            (SELECT count(*) FROM radar_requests WHERE status='open' AND type='gift'),
            (SELECT count(*) FROM radar_requests WHERE status='open' AND type='need'),
            (SELECT count(*) FROM radar_requests WHERE status='closed')"""
        cursor_radar.execute(query)
        stats = cursor_radar.fetchone()
        admin_msg = (
            "⚙️ **غرفة عمليات الرادار الملكي**\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"⚖️ انتظار (50/50): `{stats[0]}`\n"
            f"🎁 فاعلي خير: `{stats[1]}`\n"
            f"🆘 طالبي مساعدة: `{stats[2]}`\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ إجمالي النجاح: `{stats[3]}`\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
        )
        await event.reply(admin_msg, buttons=[[Button.inline("🧹 تصفير القائمة", b"clear_radar")], [Button.inline("❌ إغلاق", b"close_radar")]])

    @client.on(events.CallbackQuery(data=b"clear_radar"))
    async def clear_db(event):
        cursor_radar.execute("DELETE FROM radar_requests WHERE status='open'")
        db_radar.commit()
        await event.answer("🛡️ تم تصفير الرادار بنجاح!", alert=True)

    # --- [4] أمر الأعضاء لفتح الرادار ---
    @client.on(events.NewMessage(chats=ALLOWED_GROUPS, pattern='^رادار$'))
    async def open_radar(event):
        uid = str(event.sender_id)
        if uid in active_sessions:
            await event.reply("⚠️ **الجلسة مشغولة!** أكمل خطواتك الحالية أولاً.")
            return
        cursor_radar.execute("SELECT id FROM radar_requests WHERE uid=? AND status='open'", (uid,))
        if cursor_radar.fetchone():
            await event.reply("⚠️ **أنت مسجل بالفعل!** انتظر المنشن الملكي.")
            return

        buttons = [[Button.inline("⚖️ 50/50", b"type_50"), Button.inline("🎁 عرض مساعدة", b"type_gift")],
                   [Button.inline("🆘 طلب مساعدة", b"type_need")], [Button.inline("❌ إغلاق", b"close_radar")]]
        await event.reply(f"🎰 **مرحباً يا {event.sender.first_name}**\nيرجى اختيار نوع المسار:", buttons=buttons)

    # --- [5] معالجة الطلب (الرقم + الصورة + البحث) ---
    @client.on(events.CallbackQuery(data=re.compile(b"type_(.*)")))
    async def process_type(event):
        p_type = event.data_match.group(1).decode()
        sender_id, sender_name = str(event.sender_id), event.sender.first_name
        active_sessions[sender_id] = True 
        type_labels = {"50": "⚖️ مساهمة 50/50", "gift": "🎁 عرض مساعدة", "need": "🆘 طلب مساعدة"}

        async with event.client.conversation(event.chat_id, timeout=120) as conv:
            try:
                # 1. طلب الرقم
                await conv.send_message(f"👤 **يا {sender_name}**، أرسل عدد نردك (Dice) أرقاماً فقط:")
                while True:
                    resp = await conv.get_response()
                    if resp.sender_id == event.sender_id:
                        if resp.text.isdigit():
                            dice_val = int(resp.text)
                            break
                        else:
                            await conv.send_message("❌ أرسل أرقاماً فقط:")

                # 2. طلب الصورة
                await conv.send_message(f"📸 **يا {sender_name}**، أرسل صورة (سكرين) لنردك الآن:")
                while True:
                    photo_msg = await conv.get_response()
                    if photo_msg.sender_id == event.sender_id:
                        if photo_msg.photo:
                            break
                        else:
                            await conv.send_message("❌ يجب إرسال صورة:")

                # 3. التوثيق
                check_msg = await conv.send_message("🔍 **جاري التوثيق والبحث عن شريك...**")
                await event.client.download_media(photo_msg.photo)
                await asyncio.sleep(1)
                await check_msg.edit("✅ **تم التوثيق!** جاري فحص المطابقات...")

                # 4. منطق البحث عن شريك
                if p_type == "50":
                    min_d, max_d = dice_val * 0.7, dice_val * 1.3
                    match_query = f"SELECT uid, name, dice FROM radar_requests WHERE type='50' AND status='open' AND uid != '{sender_id}' AND dice BETWEEN {min_d} AND {max_d} ORDER BY ABS(dice - {dice_val}) ASC LIMIT 1"
                elif p_type == "need":
                    match_query = "SELECT uid, name, dice FROM radar_requests WHERE type='gift' AND status='open' LIMIT 1"
                else: # gift
                    match_query = "SELECT uid, name, dice FROM radar_requests WHERE type='need' AND status='open' LIMIT 1"

                cursor_radar.execute(match_query)
                match = cursor_radar.fetchone()

                if match:
                    p_id, p_name, p_dice = match
                    cursor_radar.execute("UPDATE radar_requests SET status='closed' WHERE uid=?", (p_id,))
                    cursor_radar.execute("INSERT INTO radar_requests (uid, name, dice, type, status) VALUES (?,?,?,?,'closed')", (sender_id, sender_name, dice_val, p_type))
                    db_radar.commit()

                    m1, m2 = f"[{sender_name}](tg://user?id={sender_id})", f"[{p_name}](tg://user?id={p_id})"
                    final_msg = (
                        "🎊 **تطابق ملكي عادل بنجاح!** 🎊\n"
                        "━━━━━━━━━━━━━━━━━━━━\n"
                        f"🥇 الأول: {m1} (🎲 {dice_val})\n"
                        f"🥈 الثاني: {m2} (🎲 {p_dice})\n"
                        "━━━━━━━━━━━━━━━━━━━━\n"
                        f"📌 النوع: **{type_labels[p_type]}**\n"
                        "🤝 **تواصلوا الآن وبالتوفيق!**"
                    )
                    await event.client.send_message(event.chat_id, final_msg)
                else:
                    cursor_radar.execute("INSERT INTO radar_requests (uid, name, dice, type, status) VALUES (?,?,?,?,'open')", (sender_id, sender_name, dice_val, p_type))
                    db_radar.commit()
                    await conv.send_message(f"✅ تم إدراجك في الانتظار. سيتم منشنتك فور توفر شريك مناسب.")

            except Exception as e:
                print(f"Error: {e}")
            
            if sender_id in active_sessions: del active_sessions[sender_id]

    @client.on(events.CallbackQuery(data=b"close_radar"))
    async def close(event):
        uid = str(event.sender_id)
        if uid in active_sessions: del active_sessions[uid]
        await event.delete()
