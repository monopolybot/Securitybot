import os
from telethon import events, Button
from database import db

# استدعاء الكلاينت والبيانات الأساسية
try:
    from __main__ import client, OWNER_ID
except ImportError:
    OWNER_ID = 5010882230 

# --- دوال الربط السريع (لحل نقص الدوال في database.py) ---
def is_locked(gid, feature):
    db.cursor.execute("SELECT status FROM locks WHERE gid=? AND feature=?", (str(gid), feature))
    row = db.cursor.fetchone()
    return row[0] == 1 if row else False

def toggle_lock(gid, feature, status):
    db.cursor.execute("INSERT OR REPLACE INTO locks (gid, feature, status) VALUES (?, ?, ?)", (str(gid), feature, status))
    db.conn.commit()

async def check_callback_privilege(event, required_rank):
    if event.sender_id == OWNER_ID: return True
    current_gid = str(event.chat_id)
    user_rank = db.get_rank(current_gid, event.sender_id)
    ranks_order = {"عضو": 0, "مميز": 1, "ادمن": 2, "مدير": 3, "مالك": 4, "المنشئ": 5}
    return ranks_order.get(user_rank, 0) >= ranks_order.get(required_rank, 0)

@client.on(events.CallbackQuery)
async def callback_handler(event):
    data = event.data.decode('utf-8')
    gid = str(event.chat_id)
    
    # التحقق من الصلاحية
    if not await check_callback_privilege(event, "مدير"):
        return await event.answer("⚠️ عذرا هذه الصلاحيات محصورة لاصحاب الرتب الادارية فقط! 👑", alert=True)

    # --- القائمة الرئيسية ---
    if data == "show_main":
        btns = [
            [Button.inline("🛡️ نظام الحماية", "show_locks"), Button.inline("🎖️ سجل الرتب", "show_ranks")],
            [Button.inline("📜 دليل الأوامر", "show_cmds"), Button.inline("⚙️ الضبط العام", "show_settings")],
            [Button.inline("❌ إغلاق اللوحة", "close")]
        ]
        await event.edit("👑 **لوحة تحكم Monopoly الملكية** 👑\n\nاختر القسم المراد التحكم به:", buttons=btns)

    # --- نظام الأقفال ---
    elif data == "show_locks":
        def get_s(feat): return "🔒" if is_locked(gid, feat) else "🔓"
        btns = [
            [Button.inline(f"{get_s('links')} الروابط", "tg_links"), Button.inline(f"{get_s('usernames')} المعرفات", "tg_usernames")],
            [Button.inline(f"{get_s('photos')} الصور", "tg_photos"), Button.inline(f"{get_s('stickers')} الملصقات", "tg_stickers")],
            [Button.inline(f"{get_s('forward')} التوجيه", "tg_forward"), Button.inline(f"{get_s('videos')} الفيديوهات", "tg_videos")],
            [Button.inline("⬅️ رجوع", "show_main")]
        ]
        await event.edit("🔐 **إعدادات الحماية الفورية للمجموعة:**", buttons=btns)

    # --- منطق التبديل (Toggle) ---
    elif data.startswith("tg_"):
        feature = data.replace("tg_", "")
        
        if feature == "welcome":
            curr = db.get_setting(gid, "welcome_status")
            new_status = "off" if curr == "on" else "on"
            db.cursor.execute("INSERT OR REPLACE INTO settings (gid, key, value) VALUES (?, ?, ?)", (gid, "welcome_status", new_status))
            db.conn.commit()
            await event.answer(f"✨ نظام الترحيب: {'✅ تفعيل' if new_status == 'on' else '❌ تعطيل'}")
            # تحديث الواجهة فوراً
            await callback_handler(event_with_new_data(event, "show_settings"))
            
        else:
            current_l = is_locked(gid, feature)
            toggle_lock(gid, feature, 0 if current_l else 1)
            await event.answer("⚙️ تم تحديث أرشيف الحماية الملكي")
            await callback_handler(event_with_new_data(event, "show_locks"))

    # --- الأقسام الأخرى ---
    elif data == "show_ranks":
        ranks_text = "🎖️ **الهرم الإداري المعتمد في Monopoly:**\n━━━━━━━━━━━━━━\n..." # النص المختصر
        await event.edit(ranks_text, buttons=[[Button.inline("⬅️ رجوع", "show_main")]])

    elif data == "show_cmds":
        cmds_text = "📜 **دليل الأوامر الإمبراطورية:**\n━━━━━━━━━━━━━━\n..." # النص المختصر
        await event.edit(cmds_text, buttons=[[Button.inline("⬅️ رجوع", "show_main")]])

    elif data == "show_settings":
        w_status = "✅ مفعل" if db.get_setting(gid, "welcome_status") == "on" else "❌ معطل"
        await event.edit("⚙️ **الإعدادات العامة للبوت:**", buttons=[
            [Button.inline(f"نظام الترحيب: {w_status}", "tg_welcome")],
            [Button.inline("⬅️ رجوع", "show_main")]
        ])

    elif data == "close":
        await event.delete()
    # --- أزرار نظام المفكرة (المضافة حديثاً) ---
    
    # تأكيد الأرشفة وبدء مفكرة جديدة
    elif data == "confirm_archive":
        from notes_manager import manage_note
        manage_note("archive")
        await event.edit("✅ **إرادة ملكية:** تم نقل كافة الملاحظات للأرشيف بنجاح، والمفكرة الحالية الآن فارغة وجاهزة.")
        
    # عرض صفحة معينة (في حال أردنا تطوير التنقل لاحقاً)
    elif data.startswith("page_"):
        # هذه سنستخدمها إذا زاد عدد الأسماء عن 10 لتظهر أزرار "التالي"
        page = int(data.split("_")[1])
        await event.answer(f"📄 أنت الآن في الصفحة {page}", alert=False)
            # --- التنقل بين صفحات المفكرة الملكية ---
    elif data.startswith("note_page_"):
        from notes_manager import manage_note
        page_num = int(data.split("_")[-1])
        notes = manage_note("get_active")
        
        # تقسيم البيانات: كل صفحة 5 ملاحظات
        start = page_num * 5
        end = start + 5
        current_page = notes[start:end]
        
        if not current_page and page_num > 0:
            return await event.answer("⚠️ لا توجد صفحات أخرى", alert=True)
            
        report = f"👑 **المفكرة الملكية - صفحة {page_num + 1}**\n" + "—" * 15 + "\n"
        for i, n in enumerate(current_page, start + 1):
            report += f"{i}. 👤 **{n[0]}**: {n[1]}\n"
            
        # إنشاء أزرار التنقل (ديناميكي)
        nav_btns = []
        if page_num > 0:
            nav_btns.append(Button.inline("▶️ السابق", f"note_page_{page_num - 1}"))
        if len(notes) > end:
            nav_btns.append(Button.inline("التالي ◀️", f"note_page_{page_num + 1}"))
            
        # تحديث الرسالة بالأزرار الجديدة
        await event.edit(report, buttons=[nav_btns, [Button.inline("❌ إغلاق", "close")]])
    
def event_with_new_data(event, new_data):
    event.data = new_data.encode('utf-8')
    return event
