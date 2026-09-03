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

GROUP_IDS = [-1003706807731, -1004273662926]  # 👈 ID group của mày

DATA_DIR = "data"
ACCOUNTS_FILE = os.path.join(DATA_DIR, "accounts.json")
USER_DATA_FILE = os.path.join(DATA_DIR, "user_data.json")
ADMIN_FILE = os.path.join(DATA_DIR, "admins.json")
GIFTCODES_FILE = os.path.join(DATA_DIR, "giftcodes.json")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")

# Tạo thư mục data nếu chưa tồn tại
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

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
config = load_json(CONFIG_FILE, {"group_ids": GROUP_IDS})  # Lưu group IDs vào config

# ===== HÀM KIỂM TRA ADMIN =====
def is_admin(user_id):
    return user_id in admins.get("list", [])

# ===== HÀM KIỂM TRA THAM GIA GROUP =====
async def is_member_any_group(user_id, context):
    group_ids = config.get("group_ids", GROUP_IDS)
    if not group_ids:
        return False
    for group_id in group_ids:
        try:
            member = await context.bot.get_chat_member(group_id, user_id)
            if member.status in ["member", "administrator", "creator"]:
                return True
        except Exception as e:
            print(f"Lỗi kiểm tra group {group_id}: {e}")
            continue
    return False

# ===== HÀM TẠO MENU =====
def get_main_menu(user_id):
    keyboard = [
        [InlineKeyboardButton("🎲 Lấy Acc Free", callback_data="get_acc")],
        [InlineKeyboardButton("📅 Điểm danh", callback_data="daily")],
        [InlineKeyboardButton("🎁 Nhập Giftcode", callback_data="giftcode")],
        [InlineKeyboardButton("📊 Thống kê của tôi", callback_data="my_stats")],
        [InlineKeyboardButton("📦 Tồn kho", callback_data="stock")]
    ]
    if is_admin(user_id):
        keyboard.append([InlineKeyboardButton("👑 Admin Panel", callback_data="admin_panel")])
    
    return InlineKeyboardMarkup(keyboard)

# ====================================
# 📌 LỆNH /start
# ====================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = user_data.get(str(user_id), {})
    
    if str(user_id) not in user_data:
        user_data[str(user_id)] = {
            "joined": False,
            "daily_date": None,
            "total_claimed": 0,
            "lifts": 0
        }
        save_json(USER_DATA_FILE, user_data)
        user = user_data[str(user_id)]
    
    # Nếu chưa xác nhận join group -> yêu cầu join
    if not user.get("joined", False):
        keyboard = [[InlineKeyboardButton("✅ Xác nhận đã tham gia", callback_data="verify_join")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        links_text = "\n".join([f"• {link}" for link in GROUP_LINKS])
        
        await update.message.reply_text(
            f"👋 **Chào mừng bạn đến với BOT LẤY ACC FREE!**\n\n"
            f"🔗 Vui lòng tham gia **một trong các group** sau:\n{links_text}\n\n"
            f"✅ Sau khi tham gia, bấm nút **'Xác nhận đã tham gia'** để tiếp tục.",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        return
    
    # Đã xác nhận -> hiển thị menu chính
    await show_main_menu(update, context, user_id)

async def show_main_menu(update, context, user_id):
    user = user_data.get(str(user_id), {})
    lifts = user.get("lifts", 0)
    total_claimed = user.get("total_claimed", 0)
    total_accs = len(accounts.get("free", []))
    
    last_acc = context.user_data.get("last_acc_msg", "")
    
    msg = f"🎮 **BOT LẤY ACC FREE**\n\n"
    msg += f"👋 Xin chào {update.effective_user.first_name}!\n"
    msg += f"📦 Tồn kho: `{total_accs}` acc\n"
    msg += f"🎯 Lượt lấy acc: `{lifts}`\n"
    msg += f"📨 Acc đã lấy: `{total_claimed}`\n\n"
    msg += f"👇 Chọn chức năng bên dưới:"
    
    if last_acc:
        msg = last_acc + "\n\n" + msg
    
    await update.message.reply_text(
        msg,
        parse_mode="Markdown",
        reply_markup=get_main_menu(user_id)
    )

# ====================================
# 📌 XÁC NHẬN THAM GIA
# ====================================
async def verify_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    
    # Kiểm tra user đã join group chưa
    is_member = await is_member_any_group(int(user_id), context)
    
    if is_member:
        user_data[user_id]["joined"] = True
        user_data[user_id]["lifts"] = user_data[user_id].get("lifts", 0) + 5
        save_json(USER_DATA_FILE, user_data)
        
        await query.edit_message_text(
            "✅ **Xác nhận thành công!**\n\n"
            "🎁 Bạn đã được tặng `5` lượt lấy acc!\n"
            "📅 Hãy điểm danh mỗi ngày để nhận thêm lượt.\n\n"
            "👇 Bấm nút dưới đây để vào menu:",
            parse_mode="Markdown"
        )
        
        keyboard = [[InlineKeyboardButton("🎮 Vào menu chính", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_reply_markup(reply_markup=reply_markup)
        
    else:
        links_text = "\n".join([f"• {link}" for link in GROUP_LINKS])
        await query.edit_message_text(
            f"❌ **Bạn chưa tham gia bất kỳ group nào!**\n\n"
            f"🔗 Vui lòng tham gia **một trong các group** sau:\n{links_text}\n\n"
            f"✅ Sau đó bấm lại nút xác nhận.",
            parse_mode="Markdown"
        )
        
        keyboard = [[InlineKeyboardButton("✅ Xác nhận đã tham gia", callback_data="verify_join")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_reply_markup(reply_markup=reply_markup)

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
            "❌ **Bạn đã hết lượt lấy acc!**\n\n"
            "📅 Điểm danh mỗi ngày để nhận `2` lượt.\n"
            "🎁 Hoặc nhập giftcode để nhận thêm lượt.",
            parse_mode="Markdown"
        )
        return
    
    acc_list = accounts.get("free", [])
    if not acc_list:
        await query.edit_message_text(
            "❌ **Đã hết acc!**\n⏳ Vui lòng quay lại sau.",
            parse_mode="Markdown"
        )
        return
    
    acc = random.choice(acc_list)
    acc_list.remove(acc)
    accounts["free"] = acc_list
    save_json(ACCOUNTS_FILE, accounts)
    
    user["lifts"] -= 1
    user["total_claimed"] = user.get("total_claimed", 0) + 1
    save_json(USER_DATA_FILE, user_data)
    
    msg = "✅ **Lấy acc thành công!**\n\n"
    msg += f"📱 **Tài khoản:** `{acc['user']}`\n"
    msg += f"🔑 **Mật khẩu:** `{acc['pass']}`\n"
    if acc.get('name') and acc['name'] != 'N/A':
        msg += f"👤 **Tên:** {acc['name']}\n"
    if acc.get('uid') and acc['uid'] != 'N/A':
        msg += f"🆔 **UID:** {acc['uid']}\n"
    if acc.get('rank') and acc['rank'] != 'N/A':
        msg += f"🏅 **Rank:** {acc['rank']}\n"
    if acc.get('skin') and acc['skin'] != '0':
        msg += f"🎨 **Skin:** {acc['skin']}\n"
    
    skin_types = [
        ("✨ Skin SS", acc.get('ss', '0')),
        ("💎 Skin SSS", acc.get('sss', '0')),
        ("🎌 Skin Anime", acc.get('anime', '0')),
        ("🔮 Skin SSM", acc.get('ssm', '0')),
        ("🎊 Skin SUKIEN", acc.get('sukien', '0')),
        ("🎮 Skin SC", acc.get('sc', '0')),
        ("📦 Other", acc.get('other', '0'))
    ]
    
    for label, value in skin_types:
        if value and value != '0':
            msg += f"\n{label}: {value}"
        else:
            msg += f"\n{label}: `0`"
    
    if acc.get('status') and acc['status'] != 'N/A':
        msg += f"\n\n📌 **Tình trạng:** {acc['status']}"
    
    msg += f"\n\n🎯 Lượt còn lại: `{user['lifts']}`\n"
    msg += f"📦 Tồn kho còn: `{len(accounts['free'])}` acc\n"
    msg += f"📨 Tổng acc đã lấy: `{user['total_claimed']}` acc"
    
    context.user_data["last_acc_msg"] = msg
    
    keyboard = [[InlineKeyboardButton("🔙 Quay lại menu", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        msg,
        parse_mode="Markdown",
        reply_markup=reply_markup
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
            "📅 **Bạn đã điểm danh hôm nay rồi!**\n"
            "⏳ Quay lại vào ngày mai nhé.",
            parse_mode="Markdown"
        )
        return
    
    user["lifts"] = user.get("lifts", 0) + 2
    user["daily_date"] = today
    save_json(USER_DATA_FILE, user_data)
    
    await query.edit_message_text(
        f"✅ **Điểm danh thành công!**\n\n"
        f"🎯 Nhận được `2` lượt lấy acc\n"
        f"📊 Tổng lượt hiện có: `{user['lifts']}`\n\n"
        f"📅 Quay lại vào ngày mai để nhận tiếp.",
        parse_mode="Markdown"
    )

# ====================================
# 📌 GIFTCODE
# ====================================
async def giftcode_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "🎁 **NHẬP GIFTCODE**\n\n"
        "📝 Nhập mã giftcode vào khung chat.\n"
        "Ví dụ: `/code ABC123`\n\n"
        "💡 Mỗi code có giá trị lượt khác nhau.",
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
            f"✅ **Nhập giftcode thành công!**\n\n"
            f"🎯 Nhận được `{reward}` lượt lấy acc\n"
            f"📊 Tổng lượt hiện có: `{user['lifts']}`",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "❌ **Mã giftcode không hợp lệ!**\n"
            "Vui lòng kiểm tra lại hoặc liên hệ admin.",
            parse_mode="Markdown"
        )

# ====================================
# 📌 ADMIN TẠO GIFTCODE
# ====================================
async def create_giftcode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Bạn không có quyền này.")
        return
    
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "⚠️ **Cú pháp:** `/addcode <mã_code> <số_lượt>`\n\n"
            "📌 **Ví dụ:**\n"
            "/addcode OKDJSAJ 5\n"
            "/addcode VIP123 10",
            parse_mode="Markdown"
        )
        return
    
    code = args[0].upper()
    try:
        reward = int(args[1])
    except ValueError:
        await update.message.reply_text("⚠️ Số lượt phải là số nguyên!")
        return
    
    giftcodes[code] = reward
    save_json(GIFTCODES_FILE, giftcodes)
    
    await update.message.reply_text(
        f"✅ **Đã tạo giftcode:**\n"
        f"🔑 Mã: `{code}`\n"
        f"🎯 Số lượt: `{reward}`\n\n"
        f"📌 Người dùng nhập `/code {code}` để nhận.",
        parse_mode="Markdown"
    )

# ====================================
# 📌 THỐNG KÊ CÁ NHÂN
# ====================================
async def my_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    user = user_data.get(user_id, {})
    
    lifts = user.get("lifts", 0)
    total_claimed = user.get("total_claimed", 0)
    daily_date = user.get("daily_date", "Chưa điểm danh")
    
    await query.edit_message_text(
        f"📊 **THỐNG KÊ CỦA BẠN**\n\n"
        f"👤 Tên: {query.from_user.first_name}\n"
        f"🆔 ID: `{user_id}`\n"
        f"🎯 Lượt còn lại: `{lifts}`\n"
        f"📨 Tổng acc đã lấy: `{total_claimed}`\n"
        f"📅 Điểm danh gần nhất: `{daily_date}`",
        parse_mode="Markdown"
    )

# ====================================
# 📌 TỒN KHO
# ====================================
async def stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    acc_list = accounts.get("free", [])
    total_accs = len(acc_list)
    
    rank_count = {}
    for acc in acc_list:
        rank = acc.get('rank', 'N/A')
        rank_count[rank] = rank_count.get(rank, 0) + 1
    
    rank_stats = "\n".join([f"  - {rank}: `{count}`" for rank, count in list(rank_count.items())[:5]])
    if len(rank_count) > 5:
        rank_stats += f"\n  - ... và {len(rank_count) - 5} rank khác"
    
    await query.edit_message_text(
        f"📦 **TỒN KHO HIỆN TẠI**\n\n"
        f"🎲 Tổng acc: `{total_accs}`\n\n"
        f"📊 **Phân bố rank:**\n{rank_stats if rank_stats else '  - Chưa có dữ liệu'}",
        parse_mode="Markdown"
    )

# ====================================
# 📌 ADMIN PANEL
# ====================================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        await query.answer("⛔ Bạn không có quyền.")
        return
    
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📤 Upload file acc", callback_data="admin_upload")],
        [InlineKeyboardButton("🎁 Tạo giftcode", callback_data="admin_giftcode")],
        [InlineKeyboardButton("📊 Thống kê toàn bộ", callback_data="admin_stats")],
        [InlineKeyboardButton("🔙 Quay lại", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "👑 **ADMIN PANEL**\n\n"
        "📌 Chọn chức năng quản lý:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

# ====================================
# 📌 QUAY LẠI MENU
# ====================================
async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    user = user_data.get(user_id, {})
    lifts = user.get("lifts", 0)
    total_claimed = user.get("total_claimed", 0)
    total_accs = len(accounts.get("free", []))
    
    last_acc = context.user_data.get("last_acc_msg", "")
    
    msg = f"🎮 **BOT LẤY ACC FREE**\n\n"
    msg += f"👋 Xin chào {query.from_user.first_name}!\n"
    msg += f"📦 Tồn kho: `{total_accs}` acc\n"
    msg += f"🎯 Lượt lấy acc: `{lifts}`\n"
    msg += f"📨 Acc đã lấy: `{total_claimed}`\n\n"
    msg += f"👇 Chọn chức năng bên dưới:"
    
    if last_acc:
        msg = last_acc + "\n\n" + msg
    
    await query.edit_message_text(
        msg,
        parse_mode="Markdown",
        reply_markup=get_main_menu(int(user_id))
    )

# ====================================
# 📌 HÀM XỬ LÝ BUTTON
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
        await giftcode_menu(update, context)
    elif data == "my_stats":
        await my_stats(update, context)
    elif data == "stock":
        await stock(update, context)
    elif data == "admin_panel":
        await admin_panel(update, context)
    elif data == "back_to_menu":
        await back_to_menu(update, context)
    elif data == "admin_upload":
        await query.edit_message_text(
            "📤 **Upload file acc:**\n\n"
            "📌 Gửi file `.txt` chứa danh sách acc vào chat riêng với bot.\n"
            "📂 Định dạng: `FINAL = user:pass | Name: ... | Rank: ...`",
            parse_mode="Markdown"
        )
    elif data == "admin_giftcode":
        await query.edit_message_text(
            "🎁 **Tạo giftcode:**\n\n"
            "📌 Cú pháp: `/addcode <mã> <số_lượt>`\n"
            "Ví dụ: `/addcode OKDJSAJ 5`\n\n"
            "💡 Mỗi code có giá trị lượt lấy acc.",
            parse_mode="Markdown"
        )
    elif data == "admin_stats":
        await admin_stats(update, context)

# ====================================
# 📌 THỐNG KÊ ADMIN
# ====================================
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        await query.answer("⛔ Bạn không có quyền.")
        return
    
    await query.answer()
    
    total_users = len(user_data)
    total_accs = len(accounts.get("free", []))
    total_claimed = sum(u.get("total_claimed", 0) for u in user_data.values())
    total_giftcodes = len(giftcodes)
    
    await query.edit_message_text(
        f"📊 **THỐNG KÊ TOÀN BỘ**\n\n"
        f"👥 Người dùng: `{total_users}`\n"
        f"📦 Tồn kho: `{total_accs}` acc\n"
        f"📨 Acc đã lấy: `{total_claimed}`\n"
        f"🎁 Giftcode còn: `{total_giftcodes}`",
        parse_mode="Markdown"
    )

# ====================================
# 📌 PARSE ACC
# ====================================
def parse_accounts_from_text(text):
    accounts_added = []
    lines = text.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line or 'FINAL = ' not in line:
            continue
        try:
            data = {}
            line = line.split("FINAL = ")[1]
            fields = line.split(" | ")
            for field in fields:
                field = field.strip()
                if ": " in field:
                    key, value = field.split(": ", 1)
                    data[key.strip()] = value.strip()
            
            if "FINAL" in data:
                user_pass = data["FINAL"]
            elif fields:
                first = fields[0]
                if ":" in first:
                    user_pass = first.strip()
                else:
                    continue
            else:
                continue
            
            if ':' in user_pass:
                username, password = user_pass.split(':', 1)
            elif '|' in user_pass:
                username, password = user_pass.split('|', 1)
            else:
                continue
            
            def clean_skin(value):
                if not value or value == 'No Skin':
                    return '0'
                return value
            
            acc = {
                "user": username.strip(),
                "pass": password.strip(),
                "name": data.get('Name', 'N/A'),
                "rank": data.get('Rank', 'N/A'),
                "skin": data.get('Skin', '0'),
                "uid": data.get('UID', 'N/A'),
                "ss": clean_skin(data.get('SS', '0')),
                "sss": clean_skin(data.get('SSS', '0')),
                "anime": clean_skin(data.get('Anime', '0')),
                "ssm": clean_skin(data.get('SSM', '0')),
                "sukien": clean_skin(data.get('SUKIEN', '0')),
                "sc": clean_skin(data.get('SC', '0')),
                "other": clean_skin(data.get('Other', '0')),
                "status": data.get('Tình Trạng', 'N/A')
            }
            accounts_added.append(acc)
        except Exception as e:
            print(f"Lỗi parse: {line[:50]}... - {e}")
            continue
    
    return accounts_added

# ====================================
# 📌 UPLOAD FILE
# ====================================
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Chỉ admin mới có quyền!")
        return
    
    document = update.message.document
    if not document.file_name.endswith('.txt'):
        await update.message.reply_text("⚠️ Vui lòng gửi file `.txt`!")
        return
    
    file = await document.get_file()
    file_path = f"temp_{document.file_name}"
    await file.download_to_drive(file_path)
    
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    os.remove(file_path)
    
    parsed = parse_accounts_from_text(content)
    if not parsed:
        await update.message.reply_text("❌ Không tìm thấy acc nào trong file!")
        return
    
    accounts.setdefault("free", []).extend(parsed)
    save_json(ACCOUNTS_FILE, accounts)
    
    await update.message.reply_text(
        f"✅ **Đã thêm {len(parsed)} acc từ file `{document.file_name}`**\n"
        f"📦 Tồn kho hiện tại: `{len(accounts['free'])}` acc",
        parse_mode="Markdown"
    )

# ====================================
# 📌 HÀM CHÍNH
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
    print(f"📌 Group IDs: {GROUP_IDS}")
    print("✅ Đã thêm Group ID của mày!")
    app.run_polling()

if __name__ == "__main__":
    main()
