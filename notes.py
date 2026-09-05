import os
import asyncio
from telethon import events, Button
from notes_manager import manage_note

user_edit_state = {}

async def send_notes_page(event, notes, page):
    page_size = 5
    total_pages = (len(notes) + page_size - 1) // page_size
    start = page * page_size
    end = start + page_size
    page_notes = notes[start:end]
    
    report = f"👑 **سجل المفكرة (صفحة {page + 1}/{total_pages}):**\n\n"
    report += "\n".join([f"{start + i + 1}. 👤 {n[0]}" for i, n in enumerate(page_notes)])
    
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

def setup_notes_system(client, ALLOWED_GROUPS, check_privilege):
    @client.on(events.NewMessage(chats=ALLOWED_GROUPS))
    async def handle_notes_system(event):
        if not await check_privilege(event, "ادمن"): return
        text, sender_id = event.raw_text, event.sender_id

        if sender_id in user_edit_state:
            state = user_edit_state[sender_id]
            if text == "إلغاء":
                del user_edit_state[sender_id]
                await event.reply("🚫 **تم إلغاء العملية.**")
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
                    await event.reply("✍️ **تم استلام الرقم.**\nالآن أرسل **الملاحظة الجديدة**:")
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
                manage_note("add", (name.strip(), note.strip(), sender_id))
                await event.reply(f"✅ **تم الحفظ:** {name.strip()}")
            except: await event.reply("❌ **خطأ في التنسيق.**")

        elif text == "عرض المفكرة":
            notes = manage_note("get_active")
            if not notes: return await event.reply("📜 **المفكرة فارغة.**")
            await send_notes_page(event, notes, 0)

        elif text.startswith("بحث ملاحظة"):
            name = text.replace("بحث ملاحظة", "").strip()
            results = manage_note("search", name)
            if not results: return await event.reply("🔍 **لا يوجد ملف.**")
            msg = f"👑 **ملف العضو: {name}**\n\n" + "\n".join(
                [f"⚜️ {i}. {r[1]} \n   ⏳ *{r[2]}*\n" for i, r in enumerate(results, 1)]
            )
            buttons = [[Button.inline("⚙️ تعديل", f"edit_{name}"), Button.inline("🗑️ حذف", f"del_{name}")], [Button.inline("❌ إغلاق", "close")]]
            await event.reply(msg, buttons=buttons)

        elif text.startswith("حذف ملاحظة"):
            name = text.replace("حذف ملاحظة", "").strip()
            res = manage_note("delete_all", name)
            await event.reply(f"🗑️ **تم مسح الملف الملكي لـ:** {name}" if res == "success" else "❌ الاسم غير موجود.")

    @client.on(events.CallbackQuery(data=lambda d: d.startswith(b"edit_") or d.startswith(b"del_") or d.startswith(b"page_")))
    async def callback_handler(event):
        data = event.data.decode()
        if data.startswith("page_"):
            page = int(data.split("_")[1])
            notes = manage_note("get_active")
            await send_notes_page(event, notes, page)
        else:
            action, name = data.split("_")
            user_edit_state[event.sender_id] = {"name": name, "action": action, "step": "wait_index"}
            await event.edit(f"👑 **{action.upper()} ملاحظة للعضو {name}**\nأرسل الآن **رقم الملاحظة**:")
                                                       
