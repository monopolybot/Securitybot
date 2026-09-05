import os
import sqlite3
from telethon import events, Button
from database import db
from kings_db import get_kings_ranking, DB_KINGS_NAME

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

# --- 👑 دالة عرض قائمة ملوك المجموعة الملكية (مع أسماء عريضة، تيجان، ونقاط، وزر Play) ---
async def send_kings_page(event, page=0):
    kings = get_kings_ranking()
    
    if not kings:
        text = "👑 **قائمة ملوك المجموعة:**\n━━━━━━━━━━━━━━━━━━\n\n⚜️ لا توجد سجلات ملوك متاحة حالياً.\n\n━━━━━━━━━━━━━━━━━━"
        buttons = [[Button.inline("❌ إغلاق", "close")]]
        if isinstance(event, events.CallbackQuery.Event):
            await event.edit(text, buttons=buttons)
        else:
            await event.reply(text, buttons=buttons)
        return

    page_size = 5
    total_pages = (len(kings) + page_size - 1) // page_size
    page = max(0, min(page, total_pages - 1))
    
    start = page * page_size
    end = start + page_size
    page_kings = kings[start:end]
    
    report = f"👑 **قائمة ملوك المجموعة (صفحة {page + 1}/{total_pages}):**\n━━━━━━━━━━━━━━━━━━\n\n"
    
    buttons = []
    for i, k in enumerate(page_kings, start=1):
        row_id, name, s6, s5, s4, s3, s2, s1, total = k[0], k[1], k[2], k[3], k[4], k[5], k[6], k[7], k[8]
        rank_num = start + i
        
        # 👑 اسم الملك بالخط العريض مع التاج وعدد النقاط، وفصل خط عريض بين الأسماء
        report += f"⚜️ **{rank_num}. 👑 {name}** — 💎 النقاط: `{total}`\n"
        report += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
        # زر الـ Play بجانب اسم الملك لعرض تفاصيله الكاملة
        buttons.append([Button.inline(f"▶️ عرض تفاصيل الملك: {name}", f"king_det_{row_id}")])
        
    # أزرار التنقل بين الصفحات
    nav_buttons = []
    if page > 0: 
        nav_buttons.append(Button.inline("⏪ رجوع", f"kpage_{page-1}"))
    if page < total_pages - 1: 
        nav_buttons.append(Button.inline("التالي ⏩", f"kpage_{page+1}"))
    
    if nav_buttons: 
        buttons.append(nav_buttons)
    buttons.append([Button.inline("❌ إغلاق", "close")])
    
    if isinstance(event, events.CallbackQuery.Event):
        await event.edit(report, buttons=buttons)
    else:
        await event.reply(report, buttons=buttons)


# --- 👑 دالة عرض تفاصيل الملك الفردية عند الضغط على زر Play ---
async def send_king_detail_view(event, row_id):
    conn = sqlite3.connect(DB_KINGS_NAME)
    cursor = conn.cursor()
    cursor.execute("""SELECT rowid, member_name, stars_6, stars_5, stars_4, stars_3, stars_2, stars_1, total_stars 
                      FROM kings_ranking WHERE rowid = ?""", (row_id,))
    king = cursor.fetchone()
    conn.close()
    
    if not king:
        await event.answer("⚠️ عذراً، لم يتم العثور على بيانات هذا الملك.", alert=True)
        return

    _, name, s6, s5, s4, s3, s2, s1, total = king
    total_cards_count = s6 + s5 + s4 + s3 + s2 + s1
    
    detail_text = (
        f"👑 **سجل تفاصيل الملك الملكي**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 **الاسم : {name}**\n"
        f"⭐ **كرت ست نجوم : {s6}**\n"
        f"⭐ **كرت خمس نجوم : {s5}**\n"
        f"⭐ **كرت اربعة نجوم : {s4}**\n"
        f"⭐ **كرت ثلاثة نجوم : {s3}**\n"
        f"⭐ **كرت نجمتين : {s2}**\n"
        f"⭐ **كرت نجمة : {s1}**\n\n"
        f"💎 **مجموع النقاط : {total}**\n"
        f"📦 **مجموع الكروت : {total_cards_count}**\n"
        f"━━━━━━━━━━━━━━━━━━"
    )
    
    buttons = [
        [Button.inline("🔙 العودة لقائمة الملوك", "kpage_0")],
        [Button.inline("❌ إغلاق", "close")]
    ]
    
    await event.edit(detail_text, buttons=buttons)


@client.on(events.CallbackQuery)
async def callback_handler(event):
    data = event.data.decode('utf-8')
    gid = str(event.chat_id)
    
    # 👑 معالجة أزرار التنقل الخاصة بقائمة الملوك
    if data.startswith("kpage_"):
        try:
            page_num = int(data.split("_")[1])
            await send_kings_page(event, page=page_num)
            await event.answer()
        except Exception as e:
            print(f"Error in kings pagination: {e}")
            await event.answer("حدث خطأ أثناء التنقل بين الصفحات.", alert=True)
        return

    # 👑 معالجة زر تفاصيل الملك (Play)
    if data.startswith("king_det_"):
        try:
            row_id = int(data.split("_")[2])
            await send_king_detail_view(event, row_id)
            await event.answer()
        except Exception as e:
            print(f"Error in king detail view: {e}")
            await event.answer("حدث خطأ أثناء عرض تفاصيل الملك.", alert=True)
        return

    # زر الإغلاق العام
    if data == "close":
        try:
            await event.delete()
        except:
            await event.edit("تم إغلاق اللوحة الملكية.")
        return

    # التحقق من الصلاحية لباقي أزرار الإدارة
    if not await check_callback_privilege(event, "ادمن"):
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
            await callback_handler(event_with_new_data(event, "show_settings"))
            
        else:
            current_l = is_locked(gid, feature)
            toggle_lock(gid, feature, 0 if current_l else 1)
            await event.answer("⚙️ تم تحديث أرشيف الحماية الملكي")
            await callback_handler(event_with_new_data(event, "show_locks"))

    # --- الأقسام الأخرى ---
    elif data == "show_ranks":
        ranks_text = "🎖️ **الهرم الإداري المعتمد في Monopoly:**\n━━━━━━━━━━━━━━\n..." 
        await event.edit(ranks_text, buttons=[[Button.inline("⬅️ رجوع", "show_main")]])

    elif data == "show_cmds":
        cmds_text = "📜 **دليل الأوامر الإمبراطورية:**\n━━━━━━━━━━━━━━\n..." 
        await event.edit(cmds_text, buttons=[[Button.inline("⬅️ رجوع", "show_main")]])

    elif data == "show_settings":
        w_status = "✅ مفعل" if db.get_setting(gid, "welcome_status") == "on" else "❌ معطل"
        await event.edit("⚙️ **الإعدادات العامة للبوت:**", buttons=[
            [Button.inline(f"نظام الترحيب: {w_status}", "tg_welcome")],
            [Button.inline("⬅️ رجوع", "show_main")]
        ])

    # --- تأكيد الأرشفة وبدء مفكرة جديدة ---
    elif data == "confirm_archive":
        from notes_manager import manage_note
        manage_note("archive")
        await event.edit("✅ **إرادة ملكية:** تم نقل كافة الملاحظات للأرشيف بنجاح، والمفكرة الحالية الآن فارغة وجاهزة.")
        
    # --- التنقل بين صفحات المفكرة الملكية ---
    elif data.startswith("note_page_"):
        from notes_manager import manage_note
        page_num = int(data.split("_")[-1])
        notes = manage_note("get_active")
        
        start = page_num * 5
        end = start + 5
        current_page = notes[start:end]
        
        if not current_page and page_num > 0:
            return await event.answer("⚠️ لا توجد صفحات أخرى", alert=True)
            
        report = f"👑 **المفكرة الملكية - صفحة {page_num + 1}**\n" + "—" * 15 + "\n"
        for i, n in enumerate(current_page, start + 1):
            report += f"{i}. 👤 **{n[0]}**: {n[1]}\n"
            
        nav_btns = []
        if page_num > 0:
            nav_btns.append(Button.inline("▶️ السابق", f"note_page_{page_num - 1}"))
        if len(notes) > end:
            nav_btns.append(Button.inline("التالي ◀️", f"note_page_{page_num + 1}"))
            
        await event.edit(report, buttons=[nav_btns, [Button.inline("❌ إغلاق", "close")]])
    
def event_with_new_data(event, new_data):
    event.data = new_data.encode('utf-8')
    return event
