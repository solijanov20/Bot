import os
import sqlite3
import json
from flask import Flask, request
import telebot
from telebot import types

TOKEN = '8781754588:AAE54MW3W7xuy8Tx9bvP3JTgkrK59VuBPv4'
ADMIN_ID = 1256682649
CHANNEL_ID = -1002118852337  # Majburiy obuna kanali ID raqami

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Bazani yaratish
def init_db():
    conn = sqlite3.connect('movies.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movies (
            code TEXT PRIMARY KEY,
            files TEXT,
            views INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS channels (
            channel_id TEXT PRIMARY KEY,
            channel_name TEXT
        )
    ''')
    cursor.execute('REPLACE INTO channels (channel_id, channel_name) VALUES (?, ?)', (str(CHANNEL_ID), "Uznetfilm Asosiy Kanal"))
    conn.commit()
    conn.close()

init_db()

upload_sessions = {}

# Majburiy obunani tekshirish funksiyasi
def check_subscription(user_id):
    conn = sqlite3.connect('movies.db')
    cursor = conn.cursor()
    cursor.execute('SELECT channel_id FROM channels')
    channels = cursor.fetchall()
    conn.close()

    for ch in channels:
        ch_id = ch[0]
        try:
            chat_target = int(ch_id) if ch_id.startswith('-') or ch_id.isdigit() else ch_id
            member = bot.get_chat_member(chat_target, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except Exception:
            return False
    return True

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return '!', 200

@app.route('/')
def index():
    return 'HELLO, WORLD!'

# Admin panelni chiqarish
def show_admin_panel(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("📥 Kino Yuklash"),
        types.KeyboardButton("📢 Kanallar"),
        types.KeyboardButton("🤖 Bot holati"),
        types.KeyboardButton("📊 Statistika"),
        types.KeyboardButton("👥 Adminlar")
    )
    bot.send_message(chat_id, "Solijanov_ Admin paneli:", reply_markup=markup)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    
    conn = sqlite3.connect('movies.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

    if user_id == ADMIN_ID:
        show_admin_panel(message.chat.id)
    else:
        if not check_subscription(user_id):
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("📢 Kanalga obuna bo'lish", url="https://t.me/c/2118852337/1"))
            markup.add(types.InlineKeyboardButton("🔄 Tekshirish", callback_data="check_sub"))
            bot.send_message(
                message.chat.id, 
                "⚠️ Botdan foydalanish uchun oldin majburiy kanalimizga obuna bo'ling!", 
                reply_markup=markup
            )
            return

        text = (
            "Assalomu aleykum!\n\n"
            "Uznetfilm jamoasi sizga eng yangi va saralangan kinolarni taqdim etadi.\n\n"
            "Kinoni yoki serialni ko'rish uchun uning kodini yuboring:"
        )
        bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['panel'])
def cmd_panel(message):
    if message.from_user.id == ADMIN_ID:
        show_admin_panel(message.chat.id)

@bot.message_handler(func=lambda message: message.from_user.id == ADMIN_ID)
def handle_admin_actions(message):
    user_id = message.from_user.id
    text = message.text

    if text == "📥 Kino Yuklash":
        upload_sessions[user_id] = {'step': 'waiting_code', 'files': []}
        bot.send_message(message.chat.id, "Kinoning kodini kiriting:", reply_markup=types.ReplyKeyboardRemove())
        return

    elif text == "📢 Kanallar":
        conn = sqlite3.connect('movies.db')
        cursor = conn.cursor()
        cursor.execute('SELECT channel_id, channel_name FROM channels')
        channels = cursor.fetchall()
        conn.close()
        
        resp = "📢 Majburiy kanallar ro'yxati:\n\n"
        for idx, ch in enumerate(channels, 1):
            resp += f"{idx}. ID: {ch[0]} | Nomi: {ch[1]}\n"
        
        bot.send_message(message.chat.id, resp)
        return

    elif text == "🤖 Bot holati":
        bot.send_message(message.chat.id, "🤖 Bot holati: **Yaxshi 🟢 (Server barqaror ishlamoqda)**", parse_mode="Markdown")
        return

    elif text == "📊 Statistika":
        conn = sqlite3.connect('movies.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT files FROM movies')
        rows = cursor.fetchall()
        serial_count = 0
        movie_count = 0
        
        for r in rows:
            files_list = json.loads(r[0])
            if len(files_list) > 1:
                serial_count += 1
            else:
                movie_count += 1
                
        cursor.execute('SELECT SUM(views) FROM movies')
        v_sum = cursor.fetchone()[0]
        total_views = v_sum if v_sum else 0
            
        conn.close()

        stat_text = (
            "📊 Bot statistikasi:\n\n"
            f"👥 Botga kirgan jami odamlar: {total_users} ta\n"
            f"🎬 Bazadagi kinolar: {movie_count} ta\n"
            f"📺 Bazadagi seriallar: {serial_count} ta\n"
            f"👁 Jami ko'rilgan kinolar/qismlar: {total_views} marta"
        )
        bot.send_message(message.chat.id, stat_text)
        return

    elif text == "👥 Adminlar":
        bot.send_message(message.chat.id, f"👥 Adminlar ro'yxati:\n\n1. Asosiy Admin (ID: `{ADMIN_ID}`)", parse_mode="Markdown")
        return

    if user_id in upload_sessions:
        session = upload_sessions[user_id]
        step = session.get('step')

        if step == 'waiting_code':
            code = text.strip()
            session['code'] = code
            session['step'] = 'waiting_files'
            bot.send_message(message.chat.id, f"Kod qabul qilindi: `{code}`\nEndi video(lar)ni tashlang. Serial bo'lsa bitta-bitdan ketma-ket tashlang. Hammasini tugatgach **`/tugadi`** deb yozing.", parse_mode="Markdown")
            return

        elif step == 'waiting_files':
            if text.strip() == '/tugadi':
                code = session['code']
                files = session['files']
                if not files:
                    bot.send_message(message.chat.id, "Siz hali bitta ham video yubormadingiz! Iltimos, video yuboring yoki /tugadi yozing.")
                    return

                conn = sqlite3.connect('movies.db')
                cursor = conn.cursor()
                cursor.execute('REPLACE INTO movies (code, files, views) VALUES (?, ?, 0)', (code, json.dumps(files)))
                conn.commit()
                conn.close()

                del upload_sessions[user_id]
                show_admin_panel(message.chat.id)
                bot.send_message(message.chat.id, f"Muvaffaqiyatli saqlandi! ✅\nKino kodi: `{code}`\nJami videolar: {len(files)} ta", parse_mode="Markdown")
            else:
                if message.video or message.document:
                    file_id = message.video.file_id if message.video else message.document.file_id
                    session['files'].append(file_id)
                    bot.send_message(message.chat.id, f"Video qabul qilindi ({len(session['files'])} ta). Yana tashlashingiz mumkin yoki tugatish uchun **`/tugadi`** deb yozing.", parse_mode="Markdown")
                else:
                    bot.send_message(message.chat.id, "Iltimos, video yuboring yoki tugatish uchun **`/tugadi`** deb yozing.", parse_mode="Markdown")
            return

    show_admin_panel(message.chat.id)

@bot.message_handler(func=lambda message: True)
def handle_user_request(message):
    user_id = message.from_user.id
    
    conn = sqlite3.connect('movies.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
    conn.commit()

    if not check_subscription(user_id):
        conn.close()
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Kanalga obuna bo'lish", url="https://t.me/c/2118852337/1"))
        markup.add(types.InlineKeyboardButton("🔄 Tekshirish", callback_data="check_sub"))
        
        bot.send_message(
            message.chat.id, 
            "⚠️ Botdan foydalanish uchun oldin majburiy kanalimizga obuna bo'ling!", 
            reply_markup=markup
        )
        return

    code = message.text.strip()
    cursor.execute('SELECT files, views FROM movies WHERE code = ?', (code,))
    row = cursor.fetchone()

    if row:
        files = json.loads(row[0])
        new_views = row[1] + 1
        
        cursor.execute('UPDATE movies SET views = ? WHERE code = ?', (new_views, code))
        conn.commit()
        conn.close()

        bot.send_message(message.chat.id, f"Mana, `{code}`-kodli kino yoki serial:", parse_mode="Markdown")
        for f_id in files:
            bot.send_video(message.chat.id, f_id)
        
        bot.send_message(message.chat.id, "Instagram sahifamizga obuna bo'ling ❤😎")
    else:
        conn.close()
        bot.send_message(message.chat.id, "Uzur kino kodi Xato🥲")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == "check_sub":
        if check_subscription(call.from_user.id):
            bot.answer_callback_query(call.id, "Rahmat, obuna tasdiqlandi!")
            text = (
                "Assalomu aleykum!\n\n"
                "Uznetfilm jamoasi sizga eng yangi va saralangan kinolarni taqdim etadi.\n\n"
                "Kinoni yoki serialni ko'rish uchun uning kodini yuboring:"
            )
            bot.send_message(call.message.chat.id, text)
        else:
            bot.answer_callback_query(call.id, "Siz hali kanalga obuna bo'lmadingiz!", show_alert=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
