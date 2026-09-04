import os
import json
import random
import re
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ===== CẤU HÌNH =====
TOKEN = "8925038640:AAETKnoevX7Tv7P_vadQgGRwANRrKL4mSm0"
ADMIN_ID = 7054270031

GROUP_LINKS = [
    "https://t.me/grhackios",
    "https://t.me/hackiosfreechat"
]

GROUP_IDS = [-1003706807731, -1004273662926]

ACCOUNTS_FILE = "accounts.json"
USER_DATA_FILE = "user_data.json"
ADMIN_FILE = "admins.json"
GIFTCODES_FILE = "giftcodes.json"
CONFIG_FILE = "config.json"

# ===== LOAD DATA =====
def load_json(filename, default=None):
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default if default is not None else {}

def save_json(filename, data):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

accounts = load_json(ACCOUNTS_FILE, {"free": []})
user_data = load_json(USER_DATA_FILE, {})
admins = load_json(ADMIN_FILE, {"list": [ADMIN_ID]})
giftcodes = load_json(GIFTCODES_FILE, {})
config = load_json(CONFIG_FILE, {"group_ids": GROUP_IDS})

# ===== ĐẢM BẢO ADMIN =====
if ADMIN_ID not in admins.get("list", []):
    admins["list"].append(ADMIN_ID)
    save_json(ADMIN_FILE, admins)

# ===== HÀM KIỂM TRA =====
def is_admin(user_id):
    return user_id in admins.get("list", [])

async def is_member_any_group(user_id, context):
    group_ids = config.get("group_ids", GROUP_IDS)
    for group_id in group_ids:
        try:
            member = await context.bot.get_chat_member(group_id, user_id)
            if member.status in ["member", "administrator", "creator"]:
                return True
        except:
            continue
    return False

def get_ref_link(user_id):
    return f"https://t.me/@Updetfilebot?start=ref_{user_id}"

# ===== MENU =====
def get_main_menu(user_id):
    keyboard = [
        [InlineKeyboardButton("🎲 Lấy Acc Free", callback_data="get_acc")],
        [InlineKeyboardButton("📅 Điểm danh", callback_data="daily")],
        [InlineKeyboardButton("🎁 Nhập Giftcode", callback_data="giftcode")],
        [InlineKeyboardButton("📊 Thống kê của tôi", callback_data="my_stats")],
        [InlineKeyboardButton("📦 Tồn kho", callback_data="stock")],
        [InlineKeyboardButton("👥 Giới thiệu bạn bè", callback_data="referral")]
    ]
    if is_admin(user_id):
        keyboard.append([InlineKeyboardButton("👑 Admin Panel", callback_data="admin_panel")])
    return InlineKeyboardMarkup(keyboard)

def get_compact_menu():
    keyboard = [
        [InlineKeyboardButton("🎲 Lấy Acc Free", callback_data="get_acc")],
        [InlineKeyboardButton("🔙 Quay lại menu", callback_data="back_to_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ====================================
# 📌 LỆNH /start (SỬA PHẦN REF)
# ====================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = user_data.get(str(user_id), {})
    
    # Lưu ref_id vào context để xử lý sau
    if context.args and context.args[0].startswith("ref_"):
        ref_id = context.args[0].replace("ref_", "")
        if ref_id != str(user_id) and ref_id.isdigit():
            context.user_data["ref_id"] = ref_id
            await update.message.reply_text(
                f"🎉 **Bạn đã được giới thiệu bởi user ID `{ref_id}`!**\n\n"
                f"📌 Sau khi tham gia group và xác nhận thành công, **cả 2 sẽ được +5 lượt**.",
                parse_mode="Markdown"
            )
    
    if str(user_id) not in user_data:
        user_data[str(user_id)] = {"joined": False, "daily_date": None, "total_claimed": 0, "lifts": 0}
        save_json(USER_DATA_FILE, user_data)
        user = user_data[str(user_id)]
    
    if not user.get("joined", False):
        links = "\n".join([f"• {link}" for link in GROUP_LINKS])
        keyboard = [[InlineKeyboardButton("✅ Xác nhận đã tham gia", callback_data="verify_join")]]
        await update.message.reply_text(
            f"👋 **Chào mừng!**\n🔗 Tham gia group:\n{links}\n✅ Bấm xác nhận.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    await show_main_menu(update, context, user_id)

# ====================================
# 📌 XÁC NHẬN THAM GIA (SỬA PHẦN CỘNG LƯỢT)
# ====================================
async def verify_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    
    if await is_member_any_group(int(user_id), context):
        # Cộng 5 lượt cho user hiện tại
        user_data[user_id]["joined"] = True
        user_data[user_id]["lifts"] = user_data[user_id].get("lifts", 0) + 5
        save_json(USER_DATA_FILE, user_data)
        
        # Cộng 5 lượt cho người giới thiệu (nếu có)
        ref_id = context.user_data.get("ref_id")
        if ref_id and ref_id != user_id:
            ref_user = user_data.get(ref_id, {})
            ref_user["lifts"] = ref_user.get("lifts", 0) + 5
            user_data[ref_id] = ref_user
            save_json(USER_DATA_FILE, user_data)
            
            # Thông báo cho người giới thiệu
            try:
                await context.bot.send_message(
                    chat_id=int(ref_id),
                    text=f"🎉 **Bạn đã giới thiệu thành công 1 người bạn!**\n"
                         f"👤 Người được giới thiệu: `{query.from_user.first_name}`\n"
                         f"🎯 Bạn được +5 lượt!",
                    parse_mode="Markdown"
                )
            except:
                pass
            
            # Thông báo cho người được giới thiệu
            await query.edit_message_text(
                f"✅ **Xác nhận thành công!**\n\n"
                f"🎁 Bạn được +5 lượt.\n"
                f"🎉 Người giới thiệu cũng được +5 lượt.\n\n"
                f"👇 Bấm vào menu:",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🎮 Vào menu chính", callback_data="back_to_menu")]])
            )
            return
        
        # Nếu không có ref
        await query.edit_message_text(
            "✅ **Xác nhận thành công!**\n🎁 +5 lượt.\n👇 Bấm vào menu:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🎮 Vào menu chính", callback_data="back_to_menu")]])
        )
    else:
        links = "\n".join([f"• {link}" for link in GROUP_LINKS])
        await query.edit_message_text(
            f"❌ **Chưa tham gia!**\n🔗 Vui lòng join:\n{links}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Xác nhận đã tham gia", callback_data="verify_join")]])
        )

# ====================================
# 📌 HIỂN THỊ MENU CHÍNH
# ====================================
async def show_main_menu(update, context, user_id):
    user = user_data.get(str(user_id), {})
    last_acc = context.user_data.get("last_acc_msg", "")
    
    msg = f"🎮 **BOT LẤY ACC FREE**\n\n"
    msg += f"👋 Xin chào {update.effective_user.first_name} ❤️!\n"
    msg += f"📦 Tồn kho: `{len(accounts.get('free', []))}` acc\n"
    msg += f"🎯 Lượt lấy acc: `{user.get('lifts', 0)}`\n"
    msg += f"📨 Acc đã lấy: `{user.get('total_claimed', 0)}`\n"
    
    if last_acc:
        msg = last_acc + "\n\n" + msg
    
    await update.message.reply_text(
        msg,
        parse_mode="Markdown",
        reply_markup=get_main_menu(user_id)
    )

# ====================================
# 📌 GIỚI THIỆU BẠN BÈ
# ====================================
async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    ref_link = get_ref_link(user_id)
    
    await query.edit_message_text(
        f"👥 **GIỚI THIỆU BẠN BÈ**\n\n"
        f"🔗 Link của bạn:\n`{ref_link}`\n\n"
        f"📌 Khi bạn bè qua link, tham gia 2 group và xác nhận:\n"
        f"✅ **Cả 2 đều được +5 lượt!**\n\n"
        f"📋 Copy link và gửi cho bạn bè.",
        parse_mode="Markdown"
    )

# ====================================
# 📌 LẤY ACC
# ====================================
async def get_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    user = user_data.get(user_id, {})
    
    if user.get("lifts", 0) <= 0:
        await query.edit_message_text(
            "❌ **Hết lượt!**\n📅 Điểm danh mỗi ngày +2 lượt.\n🎁 Nhập giftcode để nhận thêm.",
            parse_mode="Markdown"
        )
        return
    
    acc_list = accounts.get("free", [])
    if not acc_list:
        await query.edit_message_text("❌ **Đã hết acc!**\n⏳ Quay lại sau.", parse_mode="Markdown")
        return
    
    acc = random.choice(acc_list)
    acc_list.remove(acc)
    accounts["free"] = acc_list
    save_json(ACCOUNTS_FILE, accounts)
    
    user["lifts"] -= 1
    user["total_claimed"] = user.get("total_claimed", 0) + 1
    save_json(USER_DATA_FILE, user_data)
    
    msg = "✅ **Lấy acc thành công!**\n\n"
    msg += f"📱 **TK:** `{acc['user']}`\n🔑 **MK:** `{acc['pass']}`\n"
    if acc.get('name') and acc['name'] != 'N/A': msg += f"👤 **Tên:** {acc['name']}\n"
    if acc.get('rank') and acc['rank'] != 'N/A': msg += f"🏅 **Rank:** {acc['rank']}\n"
    if acc.get('skin') and acc['skin'] != '0': msg += f"🎨 **Skin:** {acc['skin']}\n"
    
    skin_list = [
        ("✨ SS", "ss"), ("💎 SSS", "sss"), ("🎌 Anime", "anime"),
        ("🔮 SSM", "ssm"), ("🎊 SUKIEN", "sukien"), ("🎮 SC", "sc"), ("📦 Other", "other")
    ]
    for label, key in skin_list:
        val = acc.get(key, '0')
        if val and val != '0':
            msg += f"\n**{label}:** {val}"
        else:
            msg += f"\n**{label}:** `0`"
    
    if acc.get('status') and acc['status'] != 'N/A':
        msg += f"\n\n📌 **Tình trạng:** {acc['status']}"
    
    msg += f"\n\n🎯 Lượt còn: `{user['lifts']}`\n📦 Tồn kho: `{len(accounts['free'])}` acc\n📨 Đã lấy: `{user['total_claimed']}` acc"
    
    context.user_data["last_acc_msg"] = msg
    
    await query.edit_message_text(
        msg,
        parse_mode="Markdown",
        reply_markup=get_compact_menu()
    )

# ====================================
# 📌 ĐIỂM DANH
# ====================================
async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    user = user_data.get(user_id, {})
    today = datetime.now().date().isoformat()
    
    if user.get("daily_date") == today:
        await query.edit_message_text(
            "📅 **Bạn đã điểm danh hôm nay rồi!**\n⏳ Quay lại vào ngày mai.",
            parse_mode="Markdown"
        )
        return
    
    user["lifts"] = user.get("lifts", 0) + 2
    user["daily_date"] = today
    save_json(USER_DATA_FILE, user_data)
    
    await query.edit_message_text(
        f"✅ **Điểm danh thành công!**\n🎯 +2 lượt\n📊 Tổng lượt: `{user['lifts']}`",
        parse_mode="Markdown"
    )

# ====================================
# 📌 GIFTCODE
# ====================================
async def create_giftcode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Bạn không có quyền.")
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("⚠️ `/addcode <mã> <số_lượt>`\nVD: `/addcode OKDJSAJ 5`", parse_mode="Markdown")
        return
    code, reward = args[0].upper(), int(args[1])
    giftcodes[code] = reward
    save_json(GIFTCODES_FILE, giftcodes)
    
    for uid in user_data.keys():
        try:
            await context.bot.send_message(
                chat_id=int(uid),
                text=f"🎁 **GIFTCODE MỚI!**\n\n"
                     f"🔑 Mã: `{code}`\n"
                     f"🎯 Giá trị: `{reward}` lượt\n\n"
                     f"📌 Nhập `/code {code}` để nhận ngay!",
                parse_mode="Markdown"
            )
        except:
            pass
    
    await update.message.reply_text(
        f"✅ **Đã tạo giftcode:** `{code}` ({reward} lượt)\n📢 Đã thông báo đến {len(user_data)} user.",
        parse_mode="Markdown"
    )

async def handle_giftcode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user = user_data.get(user_id, {})
    code = update.message.text.replace('/code', '').strip().upper()
    
    if code in giftcodes:
        reward = giftcodes[code]
        user["lifts"] = user.get("lifts", 0) + reward
        save_json(USER_DATA_FILE, user_data)
        del giftcodes[code]
        save_json(GIFTCODES_FILE, giftcodes)
        await update.message.reply_text(
            f"✅ **Nhập code thành công!**\n🎯 +{reward} lượt\n📊 Tổng: `{user['lifts']}`",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ **Mã không hợp lệ!**", parse_mode="Markdown")

# ====================================
# 📌 CÁC HÀM KHÁC
# ====================================
async def my_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    user = user_data.get(user_id, {})
    await query.edit_message_text(
        f"📊 **THỐNG KÊ CỦA BẠN**\n\n"
        f"👤 Tên: {query.from_user.first_name}\n🆔 ID: `{user_id}`\n"
        f"🎯 Lượt còn: `{user.get('lifts', 0)}`\n"
        f"📨 Acc đã lấy: `{user.get('total_claimed', 0)}`\n"
        f"📅 Điểm danh: `{user.get('daily_date', 'Chưa')}`",
        parse_mode="Markdown"
    )

async def stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    acc_list = accounts.get("free", [])
    total = len(acc_list)
    rank_count = {}
    for acc in acc_list:
        r = acc.get('rank', 'N/A')
        rank_count[r] = rank_count.get(r, 0) + 1
    stats = "\n".join([f"  - {r}: `{c}`" for r, c in list(rank_count.items())[:5]])
    if len(rank_count) > 5:
        stats += f"\n  - ... và {len(rank_count)-5} rank khác"
    await query.edit_message_text(
        f"📦 **TỒN KHO**\n\n🎲 Tổng: `{total}` acc\n📊 Phân bố rank:\n{stats if stats else '  - Chưa có dữ liệu'}",
        parse_mode="Markdown"
    )

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        await query.answer("⛔ Không có quyền.")
        return
    await query.answer()
    await query.edit_message_text(
        f"📊 **THỐNG KÊ TOÀN BỘ**\n\n"
        f"👥 Người dùng: `{len(user_data)}`\n"
        f"📦 Tồn kho: `{len(accounts.get('free', []))}` acc\n"
        f"📨 Acc đã lấy: `{sum(u.get('total_claimed', 0) for u in user_data.values())}`\n"
        f"🎁 Giftcode còn: `{len(giftcodes)}`",
        parse_mode="Markdown"
    )

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    user = user_data.get(user_id, {})
    last_acc = context.user_data.get("last_acc_msg", "")
    
    msg = f"🎮 **BOT LẤY ACC FREE**\n\n"
    msg += f"👋 Xin chào {query.from_user.first_name} ❤️!\n"
    msg += f"📦 Tồn kho: `{len(accounts.get('free', []))}` acc\n"
    msg += f"🎯 Lượt lấy acc: `{user.get('lifts', 0)}`\n"
    msg += f"📨 Acc đã lấy: `{user.get('total_claimed', 0)}`\n"
    
    if last_acc:
        msg = last_acc + "\n\n" + msg
    
    await query.edit_message_text(
        msg,
        parse_mode="Markdown",
        reply_markup=get_main_menu(int(user_id))
    )

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        await query.answer("⛔ Không có quyền.")
        return
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("📤 Upload file acc", callback_data="admin_upload")],
        [InlineKeyboardButton("🎁 Tạo giftcode", callback_data="admin_giftcode")],
        [InlineKeyboardButton("📊 Thống kê toàn bộ", callback_data="admin_stats")],
        [InlineKeyboardButton("🔙 Quay lại", callback_data="back_to_menu")]
    ]
    await query.edit_message_text(
        "👑 **ADMIN PANEL**\n📌 Chọn chức năng:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ====================================
# 📌 BUTTON HANDLER
# ====================================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    if data == "verify_join":
        await verify_join(update, context)
    elif data == "get_acc":
        await get_account(update, context)
    elif data == "daily":
        await daily(update, context)
    elif data == "giftcode":
        await query.edit_message_text("🎁 Nhập `/code <mã>`", parse_mode="Markdown")
    elif data == "my_stats":
        await my_stats(update, context)
    elif data == "stock":
        await stock(update, context)
    elif data == "referral":
        await referral(update, context)
    elif data == "admin_panel":
        await admin_panel(update, context)
    elif data == "back_to_menu":
        await back_to_menu(update, context)
    elif data == "admin_upload":
        await query.edit_message_text("📤 Gửi file `.txt` vào chat riêng.", parse_mode="Markdown")
    elif data == "admin_giftcode":
        await query.edit_message_text("🎁 Cú pháp: `/addcode <mã> <số_lượt>`", parse_mode="Markdown")
    elif data == "admin_stats":
        await admin_stats(update, context)

# ====================================
# 📌 PARSE ACC & UPLOAD
# ====================================
def parse_accounts_from_text(text):
    added = []
    for line in text.strip().split('\n'):
        line = line.strip()
        if not line or 'FINAL = ' not in line:
            continue
        try:
            data = {}
            line = line.split("FINAL = ")[1]
            for field in line.split(" | "):
                if ": " in field:
                    k, v = field.split(": ", 1)
                    data[k.strip()] = v.strip()
            user_pass = data.get("FINAL") or data.get("tk_mk") or ""
            if ':' in user_pass:
                u, p = user_pass.split(':', 1)
            elif '|' in user_pass:
                u, p = user_pass.split('|', 1)
            else:
                continue
            def clean(v): return v if v and v != 'No Skin' else '0'
            added.append({
                "user": u.strip(), "pass": p.strip(),
                "name": data.get('Name', 'N/A'), "rank": data.get('Rank', 'N/A'),
                "skin": data.get('Skin', '0'), "uid": data.get('UID', 'N/A'),
                "ss": clean(data.get('SS', '0')), "sss": clean(data.get('SSS', '0')),
                "anime": clean(data.get('Anime', '0')), "ssm": clean(data.get('SSM', '0')),
                "sukien": clean(data.get('SUKIEN', '0')), "sc": clean(data.get('SC', '0')),
                "other": clean(data.get('Other', '0')), "status": data.get('Tình Trạng', 'N/A')
            })
        except:
            continue
    return added

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Chỉ admin mới có quyền!")
        return
    doc = update.message.document
    if not doc.file_name.endswith('.txt'):
        await update.message.reply_text("⚠️ Gửi file `.txt`!")
        return
    file = await doc.get_file()
    path = f"temp_{doc.file_name}"
    await file.download_to_drive(path)
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    os.remove(path)
    parsed = parse_accounts_from_text(content)
    if not parsed:
        await update.message.reply_text("❌ Không tìm thấy acc!")
        return
    accounts.setdefault("free", []).extend(parsed)
    save_json(ACCOUNTS_FILE, accounts)
    await update.message.reply_text(
        f"✅ **Đã thêm {len(parsed)} acc**\n📦 Tồn kho: `{len(accounts['free'])}` acc",
        parse_mode="Markdown"
    )

# ====================================
# 📌 MAIN
# ====================================
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("code", handle_giftcode))
    app.add_handler(CommandHandler("addcode", create_giftcode))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    print("🤖 Bot đang chạy...")
    print(f"📦 Tồn kho: {len(accounts.get('free', []))} acc")
    print(f"👑 Admin: {admins.get('list', [])}")
    app.run_polling()

if __name__ == "__main__":
    main()
