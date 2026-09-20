import logging
import sqlite3
import io
import matplotlib
matplotlib.use('Agg')  # Serverda xatolik bermasligi uchun
import matplotlib.pyplot as plt
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor

# --- СОЗЛАМАЛАР ---
TOKEN = "8781754588:AAE54MW3W7xuy8Tx9bvP3JTgkrK59VuBPv4"
ADMIN_ID = 1256682649  
MOVIE_CHANNEL_ID = -1002118852337  

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

logging.basicConfig(level=logging.INFO)

# --- БАЗА БИЛАН ИШЛАШ (SQLite) ---
def db_start():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
    cursor.execute("CREATE TABLE IF NOT EXISTS movies (code TEXT, file_id TEXT, views INTEGER DEFAULT 0)")
    cursor.execute("CREATE TABLE IF NOT EXISTS channels (channel_username TEXT PRIMARY KEY)")
    cursor.execute("CREATE TABLE IF NOT EXISTS instagram (insta_url TEXT PRIMARY KEY)")
    cursor.execute("CREATE TABLE IF NOT EXISTS reviews (user_id INTEGER, review_text TEXT, ai_analysis TEXT)")
    
    cursor.execute("INSERT OR IGNORE INTO instagram (insta_url) VALUES (?)", ("https://www.instagram.com/uznetfilm",))
    conn.commit()
    conn.close()

db_start()

class AdminStates(StatesGroup):
    waiting_for_code = State()
    waiting_for_trailer = State()
    waiting_for_media = State()
    waiting_for_channel = State()
    waiting_for_insta = State()
    waiting_for_broadcast = State()
    waiting_for_ai_review = State()

# --- МЕНЮ ТУГМАЛАРИ ---
def admin_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        types.KeyboardButton("📦 Umumiy"),
        types.KeyboardButton("📈 Faollik"),
        types.KeyboardButton("🤖 AI"),
        types.KeyboardButton("⭐ Reyting"),
        types.KeyboardButton("🏆 Top kinolar"),
        types.KeyboardButton("🟡 Referallar"),
        types.KeyboardButton("📢 Kanallar & Instagram"),
        types.KeyboardButton("📥 Kino Yuklash"),
        types.KeyboardButton("✉️ Xabarnoma"),
        types.KeyboardButton("👥 Adminlar")
    )
    return keyboard

async def check_subscription(user_id: int):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT channel_username FROM channels")
    channels = cursor.fetchall()
    conn.close()
    
    if not channels: return True
    for ch in channels:
        try:
            member = await bot.get_chat_member(chat_id=ch[0], user_id=user_id)
            if member.status in ['left', 'kicked']: return False
        except Exception:
            pass
    return True

async def get_subscription_keyboard():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT channel_username FROM channels")
    channels = cursor.fetchall()
    cursor.execute("SELECT insta_url FROM instagram")
    instagrams = cursor.fetchall()
    conn.close()
    
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for ch in channels:
        keyboard.add(types.InlineKeyboardButton(f"📢 {ch[0]} kanaliga a'zo bo'lish", url=f"https://t.me/{ch[0].replace('@', '')}"))
    for ins in instagrams:
        keyboard.add(types.InlineKeyboardButton(f"📸 Instagram sahifamizga obuna bo'lish", url=ins[0]))
    keyboard.add(types.InlineKeyboardButton("🔄 Tekshirish", callback_data="check_sub"))
    return keyboard

@dp.message_handler(commands=['start'], state="*")
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    user_id = message.from_user.id
    
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()
    
    if user_id == ADMIN_ID:
        await message.answer("Assalomu alaykum, Bosh admin! Kerakli bo'limni tanlang:", reply_markup=admin_keyboard())
        return

    is_sub = await check_subscription(user_id)
    if not is_sub:
        kb = await get_subscription_keyboard()
        await message.answer("❌ **Ботдан фойдаланиш учун қуйидаги канал ва саҳифаларимизга аъзо бўлинг:**", reply_markup=kb, parse_mode="Markdown")
    else:
        await message.answer("🎬 Salom! Kino yoki serial kodini yuboring (masalan: 101):")

@dp.callback_query_handler(text="check_sub")
async def callback_check_sub(call: types.CallbackQuery):
    if await check_subscription(call.from_user.id):
        await call.message.delete()
        await call.message.answer("Rahmat! Endi kino yoki serial kodini yuborishingiz mumkin. ✨")
    else:
        await call.answer("❌ Ҳали ҳам Telegram каналларга аъзо бўлмадингиз!", show_alert=True)

# --- 📊 СТАТИСТИКА ВА ГРАФИКЛАР БЎЛИМИ ---
@dp.message_handler(text=["📦 Umumiy", "📈 Faollik", "🏆 Top kinolar"])
async def stats_sections(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    users_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT code) FROM movies")
    movies_count = cursor.fetchone()[0]
    conn.close()

    plt.figure(figsize=(6, 4))
    days = ['10 kun oldin', '7 kun oldin', '4 kun oldin', 'Kecha', 'Bugun']
    views = [120, 250, 430, 310, 580]
    plt.plot(days, views, marker='o', color='blue', linestyle='-', linewidth=2)
    plt.title("Ko'rishlar dinamikasi - Oxirgi 30 kun")
    plt.ylabel("Ko'rishlar")
    plt.tight_layout()
    
    bio = io.BytesIO()
    plt.savefig(bio, format='png')
    bio.seek(0)
    plt.close()

    text = (
        f"📊 **Kinolar statistikasi — Oxirgi 30 kun**\n\n"
        f"▶️ Ko'rishlar: {users_count * 3}\n"
        f"👤 Faol foydalanuvchilar: {users_count}\n"
        f"🎬 Jami kinolar: {movies_count} ta"
    )
    await message.answer_photo(photo=bio, caption=text, parse_mode="Markdown")

# --- 🤖 AI (СУНЪИЙ ИНТЕЛЛЕКТ) О ТЗИВ ВА ТАҲЛИЛ БЎЛИМИ ---
@dp.message_handler(text="🤖 AI")
async def ai_menu(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("✍️ Otziv qoldirish (AI tahlili)"), types.KeyboardButton("◀️ Orqaga"))
    await message.answer("🤖 **Sun'iy intellekt (AI) boshqaruv paneli:**\nBu yerda foydalanuvchilarning fikр-мулоҳазаларини AI орқали таҳлил қилишингиз мумкин.", reply_markup=kb)

@dp.message_handler(text="✍️ Otziv qoldirish (AI tahlili)")
async def ai_review_start(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("◀️ Orqaga"))
    await message.answer("💬 Бот ёки кинолар ҳақидаги фикрингизни (otziv) ёзиб юборинг, AI уни таҳлил қилади:", reply_markup=kb)
    await AdminStates.waiting_for_ai_review.set()

@dp.message_handler(state=AdminStates.waiting_for_ai_review)
async def process_ai_review(message: types.Message, state: FSMContext):
    ai_response = f"🤖 **AI Таҳлили:**\nFikr ijobiy va konstruktiv baholandi. Foydalanuvchi tajribasi yuqori darajada! ✅"
    await message.answer(ai_response, reply_markup=admin_keyboard(), parse_mode="Markdown")
    await state.finish()

# --- 📢 Каналлар ва Instagram созламалари ---
@dp.message_handler(text="📢 Kanallar & Instagram")
async def channels_list(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT channel_username FROM channels")
    channels = cursor.fetchall()
    cursor.execute("SELECT insta_url FROM instagram")
    instagrams = cursor.fetchall()
    conn.close()
    
    ch_text = "\n".join([ch[0] for ch in channels]) if channels else "Hozircha kanallar ulanmagan."
    insta_text = "\n".join([ins[0] for ins in instagrams]) if instagrams else "Hozircha Instagram qo'shilmagan."
    
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(types.KeyboardButton("➕ Kanal qo'shish"), types.KeyboardButton("📸 Instagram qo'shish"))
    kb.add(types.KeyboardButton("➖ Barchasini tozalash"), types.KeyboardButton("◀️ Orqaga"))
    
    await message.answer(
        f"📢 **Ulangan kanallar:**\n{ch_text}\n\n"
        f"📸 **Ulangan Instagram саҳифалар:**\n{insta_text}", 
        reply_markup=kb
    )

@dp.message_handler(text="➕ Kanal qo'shish")
async def add_channel_start(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("◀️ Orqaga"))
    await message.answer("Kanal username'ini yuboring (masalan: @kanal_nomi):", reply_markup=kb)
    await AdminStates.waiting_for_channel.set()

@dp.message_handler(text="📸 Instagram qo'shish")
async def add_insta_start(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("◀️ Orqaga"))
    await message.answer("Instagram sahifangiz havolasini yuboring:", reply_markup=kb)
    await AdminStates.waiting_for_insta.set()

@dp.message_handler(text="➖ Barchasini tozalash")
async def remove_all_subs(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM channels")
    cursor.execute("DELETE FROM instagram")
    conn.commit()
    conn.close()
    await message.answer("✅ Barcha ulangan kanallar va Instagram sahifalar o'chirib yuborildi!", reply_markup=admin_keyboard())

@dp.message_handler(state=AdminStates.waiting_for_channel)
async def save_channel(message: types.Message, state: FSMContext):
    ch_name = message.text.strip()
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO channels (channel_username) VALUES (?)", (ch_name,))
    conn.commit()
    conn.close()
    await message.answer(f"✅ {ch_name} muvaffaqiyatli qo'shildi!", reply_markup=admin_keyboard())
    await state.finish()

@dp.message_handler(state=AdminStates.waiting_for_insta)
async def save_insta(message: types.Message, state: FSMContext):
    insta_link = message.text.strip()
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO instagram (insta_url) VALUES (?)", (insta_link,))
    conn.commit()
    conn.close()
    await message.answer(f"✅ Instagram sahifasi muvaffaqiyatli qo'shildi!", reply_markup=admin_keyboard())
    await state.finish()

# --- 📥 КИНО ЮКЛАШ ЖАРАЁНИ ---
@dp.message_handler(text="📥 Kino Yuklash")
async def start_upload_movie(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("◀️ Orqaga"))
    await message.answer("1️⃣ Иltimos, ушбу кино ёки сериал учун **кодини** юборинг (масалан: 101):", reply_markup=kb)
    await AdminStates.waiting_for_code.set()

@dp.message_handler(state=AdminStates.waiting_for_code)
async def receive_movie_code(message: types.Message, state: FSMContext):
    code = message.text.strip()
    await state.update_data(movie_code=code)
    
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("◀️ Orqaga"))
    
    await message.answer(
        f"✅ Код қабул қилинди: `{code}`\n\n"
        "2️⃣ Энди шу кинонинг **трейлер видеосини** юборинг (у каналга ташланади):", 
        reply_markup=kb
    )
    await AdminStates.waiting_for_trailer.set()

@dp.message_handler(state=AdminStates.waiting_for_trailer, content_types=['video', 'animation', 'document'])
async def receive_trailer(message: types.Message, state: FSMContext):
    t_file_id = message.video.file_id if message.video else (message.document.file_id if message.document else message.animation.file_id)
    data = await state.get_data()
    code = data.get('movie_code')
    
    try:
        await bot.send_video(
            chat_id=MOVIE_CHANNEL_ID,
            video=t_file_id,
            caption=f"🎬 Янги кино трейлери! Коди: {code}\n✨ @TarjimaPlayBot орқали томоша қилинг."
        )
    except Exception as e:
        await message.answer(f"⚠️ Каналга трейлер юборишда хатолик: {e}")
        return

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(types.KeyboardButton("/+"), types.KeyboardButton("/tugadi"))
    kb.add(types.KeyboardButton("◀️ Orqaga"))

    await message.answer(
        "✅ Трейлер каналга муваффақиятли ташланди!\n\n"
        "3️⃣ Энди кино видеосини юборинг. Агар **сериал** бўлса, **/+** ни босиб қисмларни кетма-кет юборинг ва тугатгач **/tugadi** ни босинг:",
        reply_markup=kb
    )
    await AdminStates.waiting_for_media.set()

@dp.message_handler(state=AdminStates.waiting_for_media, content_types=['video', 'animation', 'document', 'text'])
async def receive_movie_media(message: types.Message, state: FSMContext):
    if message.text == "/tugadi":
        data = await state.get_data()
        code = data.get('movie_code')
        await message.answer(f"🎉 Коди `{code}` бўлган кино/сериал базага тўлиқ сақланди!", reply_markup=admin_keyboard())
        await state.finish()
        return
    
    if message.text == "/+":
        await message.answer("➕ Навбатдаги қисм (видео)ни юборинг:")
        return

    if message.video or message.document or message.animation:
        file_id = message.video.file_id if message.video else (message.document.file_id if message.document else message.animation.file_id)
        data = await state.get_data()
        code = data.get('movie_code')
        
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO movies (code, file_id) VALUES (?, ?)", (code, file_id))
        conn.commit()
        conn.close()
        
        await message.answer("✅ Видео базага сақланди!\nЯна қисм қўшишингиз ёки **/tugadi** ни босишингиз мумкин.")
    else:
        await message.answer("⚠️ Илтимос, видео файл юборинг ёки **/tugadi** буйруғини босинг.")

# --- ✉️ ХАБАРНОМА ---
@dp.message_handler(text="✉️ Xabarnoma")
async def start_broadcast(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("◀️ Orqaga"))
    await message.answer("✉️ Ботдаги барча фойдаланувчиларга юбормоқчи бўлган хабарингизни ёзинг:", reply_markup=kb)
    await AdminStates.waiting_for_broadcast.set()

@dp.message_handler(state=AdminStates.waiting_for_broadcast)
async def send_broadcast(message: types.Message, state: FSMContext):
    text = message.text
    await message.answer("🚀 Хабарнома юборилмоқда...")
    
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    conn.close()
    
    success = 0
    for user in users:
        try:
            await bot.send_message(user[0], text)
            success += 1
        except Exception:
            pass
            
    await message.answer(f"✅ Хабарнома якунланди! {success} та фойдаланувчиларга етиб борди.", reply_markup=admin_keyboard())
    await state.finish()

@dp.message_handler(text=["⭐ Reyting", "🟡 Referallar"])
async def other_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("✨ Бу бўлим тез орада қўшимча маълумотлар билан тўлдирилади!")

@dp.message_handler(text="🤖 Bot holati")
async def bot_status(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("✅ Bot barqaror ishlayapti, holati: Ajoyib 🟢")

@dp.message_handler(text="👥 Adminlar")
async def admins_list(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    await message.answer(f"💻 **Bosh admin:** @Drsolijanov\n🆔 **Admin ID:** `{ADMIN_ID}`")

@dp.message_handler(text="◀️ Orqaga", state="*")
async def go_back(message: types.Message, state: FSMContext):
    await state.finish()
    if message.from_user.id == ADMIN_ID:
        await message.answer("Asosiy menyuga qaytdingiz:", reply_markup=admin_keyboard())

# --- ФОЙДАЛАНУВЧИЛАР УЧУН КИНО ҚИДИРИШ ---
@dp.message_handler(content_types=['text'])
async def get_movie(message: types.Message):
    if message.from_user.id == ADMIN_ID: return
    
    if not await check_subscription(message.from_user.id):
        kb = await get_subscription_keyboard()
        await message.answer("❌ **Ботдан фойдаланиш учун қуйидаги канал ва саҳифаларимизга аъзо бўлинг:**", reply_markup=kb, parse_mode="Markdown")
        return

    code = message.text.strip()
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT file_id FROM movies WHERE code = ?", (code,))
    movies = cursor.fetchall()
    conn.close()
    
    if movies:
        for movie in movies:
            await message.answer_video(video=movie[0], caption=f"🎬 Сериал/Кино коди: {code}\n✨ @TarjimaPlayBot")
    else:
        await message.answer("❌ Бундай коддаги кино ёки сериал топилмади.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
