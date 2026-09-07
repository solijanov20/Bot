import os
import sqlite3
import requests
from flask import Flask, request

# TOKEN va boshqa ma'lumotlaringiz to'g'rilandi:
TOKEN = "8781754588:AAE54MW3W7xuy8Tx9bvP3JTgkrK59VuBPv4"
ADMIN_ID = 1256682649
MOVIE_CHANNEL_ID = "-1002118852337"

URL = f"https://api.telegram.org/bot{TOKEN}/"

app = Flask(__name__)

def get_db():
    conn = sqlite3.connect("movies.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS movies (
            code INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id TEXT,
            trailer_file_id TEXT,
            caption TEXT,
            views INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS series (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code INTEGER,
            episode INTEGER,
            file_id TEXT,
            trailer_file_id TEXT,
            caption TEXT,
            views INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT,
            channel_url TEXT,
            name TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY
        )
    """)
    conn.commit()
    conn.close()

init_db()

admin_state = {}

def send_message(chat_id, text, reply_markup=None):
    try:
        data = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
        if reply_markup:
            data["reply_markup"] = reply_markup
        requests.post(URL + "sendMessage", json=data, timeout=5)
    except Exception as e:
        print("Xato send_message:", e)

def send_video(chat_id, file_id, caption, reply_markup=None):
    try:
        data = {"chat_id": chat_id, "video": file_id, "caption": caption, "parse_mode": "Markdown"}
        if reply_markup:
            data["reply_markup"] = reply_markup
        return requests.post(URL + "sendVideo", json=data, timeout=10).json()
    except Exception as e:
        print("Xato send_video:", e)
        return None

def check_sub(user_id, channel_id):
    try:
        res = requests.post(URL + "getChatMember", json={"chat_id": channel_id, "user_id": user_id}, timeout=3).json()
        if res.get("ok"):
            status = res["result"]["status"]
            return status in ["creator", "administrator", "member"]
    except Exception as e:
        print("Xato check_sub:", e)
    return False

def get_admin_keyboard():
    return {
        "keyboard": [
            [{"text": "📢 Kanallar"}, {"text": "📥 Kino Yuklash"}],
            [{"text": "✉ Xabarnoma"}, {"text": "📊 Statistika"}],
            [{"text": "🤖 Bot holati"}, {"text": "👥 Adminlar"}],
            [{"text": "◀️ Orqaga"}]
        ],
        "resize_keyboard": True
    }

def get_media_type_keyboard():
    return {
        "keyboard": [
            [{"text": "🎬 Kino"}, {"text": "📺 Serial"}],
            [{"text": "◀️ Orqaga"}]
        ],
        "resize_keyboard": True
    }

def get_instagram_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "📸 Instagram sahifamizga obuna bo'lish", "url": "https://www.instagram.com/uznetfilm?stkn=MzBqamVuYXQzOWsw"}]
        ]
    }

def add_user(user_id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        print("Xato add_user:", e)

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()
    if not update:
        return "OK", 200

    if "callback_query" in update:
        query = update["callback_query"]
        user_id = query["from"]["id"]
        chat_id = query["message"]["chat"]["id"]
        data = query.get("data")

        if data == "check_sub":
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT channel_id FROM channels")
            channels = cursor.fetchall()
            conn.close()

            unsubbed = False
            for ch in channels:
                if not check_sub(user_id, ch["channel_id"]):
                    unsubbed = True
                    break

            if unsubbed:
                requests.post(URL + "answerCallbackQuery", json={"callback_query_id": query["id"], "text": "iltimos obuna boling ❤💬", "show_alert": True})
            else:
                requests.post(URL + "answerCallbackQuery", json={"callback_query_id": query["id"], "text": "rahmat 🥰", "show_alert": True})
                send_message(chat_id, "rahmat 🥰\n\nEndi kino yoki serial kodini qaytadan yuboring:")
        
        elif data.startswith("ep_"):
            _, code_str, ep_str = data.split("_")
            code, episode = int(code_str), int(ep_str)

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT file_id, caption FROM series WHERE code = ? AND episode = ?", (code, episode))
            ser = cursor.fetchone()
            if ser:
                cursor.execute("UPDATE series SET views = views + 1 WHERE code = ? AND episode = ?", (code, episode))
                conn.commit()
            conn.close()

            if ser:
                requests.post(URL + "answerCallbackQuery", json={"callback_query_id": query["id"], "text": f"{episode}-qism yuklanmoqda..."})
                video_caption = f"📺 {ser['caption']} — {episode}-qism\n\nrahmat 🥰"
                send_video(chat_id, ser["file_id"], video_caption, reply_markup=get_instagram_keyboard())
            else:
                requests.post(URL + "answerCallbackQuery", json={"callback_query_id": query["id"], "text": "Kechirasiz, bu qism topilmadi."})
        return "OK", 200

    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        user_id = msg["from"]["id"]

        add_user(user_id)

        if "text" in msg:
            text = msg["text"].strip()

            if text.lower() == "/start":
                start_text = (
                    "Assalomu aleykum!\n\n"
                    "Uznetfilm jamoasi sizga eng yangi va saralangan kinolarni taqdim etadi.\n\n"
                    "Kinoni yoki serialni ko'rish uchun uning kodini yuboring:"
                )
                send_message(chat_id, start_text)
                return "OK", 200

            if text.lower() == "/panel" and user_id == ADMIN_ID:
                send_message(chat_id, "⚙️ *Admin boshqaruv paneli:*", reply_markup=get_admin_keyboard())
                return "OK", 200

            if text.lower().startswith("/triller") and user_id == ADMIN_ID:
                parts = text.split(maxsplit=1)
                if len(parts) == 2 and parts[1].isdigit():
                    tr_code = int(parts[1])
                    conn = get_db()
                    cursor = conn.cursor()
                    
                    cursor.execute("SELECT trailer_file_id, caption FROM movies WHERE code = ?", (tr_code,))
                    m_data = cursor.fetchone()
                    
                    if m_data:
                        ch_caption = f"🎬 *{m_data['caption']}*\n\n🔢 *Kino kodi:* `{tr_code}`\n📥 Ko'rish uchun botga kodingizni yuboring!\n🤖 *Botimiz:* @Uznetfilm_bot"
                        send_video(MOVIE_CHANNEL_ID, m_data["trailer_file_id"], ch_caption)
                        send_message(chat_id, f"✅ `{tr_code}`-kodli kino treyleri kanalga yuborildi!")
                    else:
                        cursor.execute("SELECT trailer_file_id, caption FROM series WHERE code = ? ORDER BY episode ASC LIMIT 1", (tr_code,))
                        s_data = cursor.fetchone()
                        if s_data:
                            ch_caption = f"📺 *{s_data['caption']}*\n\n🔢 *Serial kodi:* `{tr_code}`\n📥 Ko'rish uchun botga kodingizni yuboring!\n🤖 *Botimiz:* @Uznetfilm_bot"
                            send_video(MOVIE_CHANNEL_ID, s_data["trailer_file_id"], ch_caption)
                            send_message(chat_id, f"✅ `{tr_code}`-kodli serial treyleri kanalga yuborildi!")
                        else:
                            send_message(chat_id, "❌ Bunday kodli kino yoki serial topilmadi!")
                    conn.close()
                else:
                    send_message(chat_id, "❌ *Xato format!* To'g'ri ishlatish:\n`/triller kod` (masalan: `/triller 5`)")
                return "OK", 200

            if user_id == ADMIN_ID:
                if text == "📢 Kanallar":
                    conn = get_db()
                    cursor = conn.cursor()
                    cursor.execute("SELECT channel_id, name, channel_url FROM channels")
                    channels = cursor.fetchall()
                    conn.close()

                    ch_text = "📢 *Majburiy kanallar ro'yxati:*\n\n"
                    if channels:
                        for ch in channels:
                            ch_text += f"🔹 {ch['name']} (`{ch['channel_id']}`)\n"
                    else:
                        ch_text += "Hozircha kanallar qo'shilmagan.\n"

                    ch_text += "\n*Yangi kanal qo'shish uchun quyidagi formatda yuboring:*\n`@kanal_username https://t.me/kanal_linki Kanal Nomi`"
                    admin_state[user_id] = "waiting_for_channel"
                    send_message(chat_id, ch_text)
                    return "OK", 200

                if admin_state.get(user_id) == "waiting_for_channel":
                    parts = text.split(" ", 2)
                    if len(parts) == 3:
                        ch_id, ch_url, ch_name = parts[0], parts[1], parts[2]
                        conn = get_db()
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO channels (channel_id, channel_url, name) VALUES (?, ?, ?)", (ch_id, ch_url, ch_name))
                        conn.commit()
                        conn.close()
                        send_message(chat_id, f"✅ *Kanal qo'shildi:* {ch_name}", reply_markup=get_admin_keyboard())
                    else:
                        send_message(chat_id, "❌ *Xato format!* Qaytadan yuboring.")
                    admin_state.pop(user_id, None)
                    return "OK", 200

                if text == "📥 Kino Yuklash" or text.lower() == "/kino":
                    admin_state[user_id] = "waiting_for_trailer"
                    send_message(chat_id, "🎬 Avval ushbu kino yoki serialning **treylerini** (videofaylini) yuboring:")
                    return "OK", 200

                if text == "🎬 Kino" and admin_state.get(user_id) and isinstance(admin_state[user_id], dict) and admin_state[user_id].get("state") == "waiting_for_type":
                    admin_state[user_id]["type"] = "movie"
                    admin_state[user_id]["state"] = "waiting_for_full_movie"
                    send_message(chat_id, "📥 Endi to'liq **kino faylini** (videoni) yuboring:")
                    return "OK", 200

                if text == "📺 Serial" and admin_state.get(user_id) and isinstance(admin_state[user_id], dict) and admin_state[user_id].get("state") == "waiting_for_type":
                    admin_state[user_id]["type"] = "series"
                    admin_state[user_id]["state"] = "waiting_for_series_code"
                    send_message(chat_id, "🔢 Ushbu serial uchun **kod (raqam)** yuboring (masalan: 55):")
                    return "OK", 200

                if isinstance(admin_state.get(user_id), dict) and admin_state[user_id].get("state") == "waiting_for_series_code":
                    if text.isdigit():
                        admin_state[user_id]["series_code"] = int(text)
                        admin_state[user_id]["state"] = "waiting_for_episode"
                        send_message(chat_id, "🔢 Ushbu video serialning **nechanchi qismi (seriyasi)** ekanligini raqamda yuboring (masalan: 1):")
                    else:
                        send_message(chat_id, "❌ Faqat raqam kiriting!")
                    return "OK", 200

                if isinstance(admin_state.get(user_id), dict) and admin_state[user_id].get("state") == "waiting_for_episode":
                    if text.isdigit():
                        admin_state[user_id]["episode"] = int(text)
                        admin_state[user_id]["state"] = "waiting_for_full_series"
                        send_message(chat_id, "📥 Endi ushbu qismning to'liq **video faylini** yuboring:")
                    else:
                        send_message(chat_id, "❌ Faqat raqam kiriting!")
                    return "OK", 200

                if isinstance(admin_state.get(user_id), dict) and admin_state[user_id].get("state") == "waiting_for_series_caption":
                    trailer_file_id = admin_state[user_id]["trailer_file_id"]
                    file_id = admin_state[user_id]["full_file_id"]
                    s_code = admin_state[user_id]["series_code"]
                    episode = admin_state[user_id]["episode"]
                    caption = text

                    conn = get_db()
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO series (code, episode, file_id, trailer_file_id, caption) VALUES (?, ?, ?, ?, ?)", (s_code, episode, file_id, trailer_file_id, caption))
                    conn.commit()
                    conn.close()

                    send_message(chat_id, f"✅ *Serial qismi bazaga saqlandi!*\n\n🔢 Kod: `{s_code}` | Qism: `{episode}`\n📢 Kanalga chiqarish uchun: `/triller {s_code}` deb yuboring.", reply_markup=get_admin_keyboard())
                    admin_state.pop(user_id, None)
                    return "OK", 200

                if text == "✉ Xabarnoma":
                    admin_state[user_id] = "waiting_for_broadcast"
                    send_message(chat_id, "✉️ Botdagi barcha foydalanuvchilarga yubormoqchi bo'lgan xabaringizni yozing:")
                    return "OK", 200

                if admin_state.get(user_id) == "waiting_for_broadcast":
                    admin_state.pop(user_id, None)
                    conn = get_db()
                    cursor = conn.cursor()
                    cursor.execute("SELECT user_id FROM users")
                    users = cursor.fetchall()
                    conn.close()

                    send_message(chat_id, f"🚀 Xabarnoma yuborilmoqda ({len(users)} ta foydalanuvchiga)...")
                    success = 0
                    for u in users:
                        try:
                            send_message(u["user_id"], text)
                            success += 1
                        except:
                            pass
                    send_message(chat_id, f"✅ Xabarnoma yakunlandi! *{success}* ta foydalanuvchiga yetib bordi.", reply_markup=get_admin_keyboard())
                    return "OK", 200

                if text == "📊 Statistika":
                    conn = get_db()
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) as count FROM users")
                    u_count = cursor.fetchone()["count"]
                    cursor.execute("SELECT COUNT(*) as count FROM movies")
                    m_count = cursor.fetchone()["count"]
                    cursor.execute("SELECT COUNT(DISTINCT code) as count FROM series")
                    s_count = cursor.fetchone()["count"]
                    cursor.execute("SELECT SUM(views) as total_views FROM movies")
                    m_views = cursor.fetchone()["total_views"] or 0
                    cursor.execute("SELECT SUM(views) as total_views FROM series")
                    s_views = cursor.fetchone()["total_views"] or 0
                    conn.close()

                    stat_msg = (
                        f"📊 *Bot statistikasi:*\n\n"
                        f"👥 Botga kirgan jami odamlar: *{u_count} ta*\n"
                        f"🎬 Bazadagi kinolar: *{m_count} ta*\n"
                        f"📺 Bazadagi seriallar: *{s_count} ta*\n"
                        f"👁 Jami ko'rilgan kinolar/qismlar: *{m_views + s_views} marta*"
                    )
                    send_message(chat_id, stat_msg)
                    return "OK", 200

                if text == "🤖 Bot holati":
                    send_message(chat_id, "✅ *Bot holati:* A'lo darajada! Server 24/7 rejimida uzluksiz, tezkor va muammosiz ishlamoqda.")
                    return "OK", 200

                if text == "👥 Adminlar":
                    send_message(chat_id, "👨‍💻 *Bosh admin:* @Drsolijanov\n🆔 *Admin ID:* `1256682649`")
                    return "OK", 200

                if text == "◀️ Orqaga":
                    admin_state.pop(user_id, None)
                    send_message(chat_id, "Asosiy menyuga qaytdingiz. Kino kodini yuborishingiz mumkin:", reply_markup={"remove_keyboard": True})
                    return "OK", 200

                if isinstance(admin_state.get(user_id), dict) and admin_state[user_id].get("state") == "waiting_for_caption":
                    trailer_file_id = admin_state[user_id]["trailer_file_id"]
                    file_id = admin_state[user_id]["full_file_id"]
                    caption = text

                    conn = get_db()
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO movies (file_id, trailer_file_id, caption) VALUES (?, ?, ?)", (file_id, trailer_file_id, caption))
                    conn.commit()
                    code = cursor.lastrowid
                    conn.close()

                    send_message(chat_id, f"✅ *Kino bazaga saqlandi!*\n\n🔢 *Kino kodi:* `{code}`\n📢 Kanalga treyler chiqarish uchun: `/triller {code}` deb yuboring.", reply_markup=get_admin_keyboard())
                    admin_state.pop(user_id, None)
                    return "OK", 200

            if text.isdigit():
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute("SELECT channel_id, channel_url, name FROM channels")
                channels = cursor.fetchall()

                unsubbed_buttons = []
                for ch in channels:
                    if not check_sub(user_id, ch["channel_id"]):
                        unsubbed_buttons.append([{"text": f"➕ {ch['name']}", "url": ch["channel_url"]}])

                if unsubbed_buttons:
                    unsubbed_buttons.append([{"text": "🔄 Obunani tekshirish", "callback_data": "check_sub"}])
                    send_message(chat_id, "iltimos obuna boling ❤💬", reply_markup={"inline_keyboard": unsubbed_buttons})
                    conn.close()
                    return "OK", 200

                code = int(text)

                cursor.execute("SELECT file_id, caption FROM movies WHERE code = ?", (code,))
                movie = cursor.fetchone()

                if movie:
                    cursor.execute("UPDATE movies SET views = views + 1 WHERE code = ?", (code,))
                    conn.commit()
                    conn.close()

                    video_caption = f"{movie['caption']}\n\nrahmat 🥰"
                    send_video(chat_id, movie["file_id"], video_caption, reply_markup=get_instagram_keyboard())
                    return "OK", 200

                cursor.execute("SELECT episode, caption FROM series WHERE code = ? ORDER BY episode ASC", (code,))
                episodes = cursor.fetchall()
                conn.close()

                if episodes:
                    series_title = episodes[0]["caption"]
                    inline_buttons = []
                    row = []
                    for ep in episodes:
                        row.append({"text": str(ep['episode']), "callback_data": f"ep_{code}_{ep['episode']}"})
                        if len(row) == 5:
                            inline_buttons.append(row)
                            row = []
                    if row:
                        inline_buttons.append(row)

                    inline_buttons.append([{"text": "📸 Instagram sahifamizga obuna bo'lish", "url": "https://www.instagram.com/uznetfilm?stkn=MzBqamVuYXQzOWsw"}])

                    send_message(chat_id, f"📺 *{series_title}*\n\nKerakli qism raqamini tanlang:", reply_markup={"inline_keyboard": inline_buttons})
                else:
                    send_message(chat_id, "Bunday kodli kino yoki serial topilmadi.")
                return "OK", 200

        if "video" in msg and user_id == ADMIN_ID:
            state_data = admin_state.get(user_id)
            if isinstance(state_data, dict):
                current_state = state_data.get("state")

                if current_state == "waiting_for_trailer":
                    admin_state[user_id]["trailer_file_id"] = msg["video"]["file_id"]
                    admin_state[user_id]["state"] = "waiting_for_type"
                    send_message(chat_id, "Bu video **Kino**mi yoki **Serial**mi?", reply_markup=get_media_type_keyboard())
                    return "OK", 200

                elif current_state == "waiting_for_full_movie":
                    admin_state[user_id]["full_file_id"] = msg["video"]["file_id"]
                    admin_state[user_id]["state"] = "waiting_for_caption"
                    send_message(chat_id, "✍️ Endi ushbu kinoning nomi yoki tavsifini yuboring:")
                    return "OK", 200

                elif current_state == "waiting_for_full_series":
                    admin_state[user_id]["full_file_id"] = msg["video"]["file_id"]
                    admin_state[user_id]["state"] = "waiting_for_series_caption"
                    send_message(chat_id, "✍️ Endi serial nomini yuboring:")
                    return "OK", 200

    return "OK", 200

@app.route("/")
def index():
    return "Bot active", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
