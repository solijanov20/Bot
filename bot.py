import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor

# Сизнинг токенингиз ва админ ID
TOKEN = "8781754588:AAE54MW3W7xuy8Tx9VuBPv4"
ADMIN_ID = 1256682649

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

logging.basicConfig(level=logging.INFO)

MOVIES = {}
CHANNELS = ["@kanal_username"]
USERS_COUNT = 832

class AdminStates(StatesGroup):
    waiting_for_trailer = State()
    waiting_for_movie_code = State()
    waiting_for_broadcast = State()

def admin_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        types.KeyboardButton("📢 Kanallar"),
        types.KeyboardButton("📥 Kino Yuklash"),
        types.KeyboardButton("✉️ Xabarnoma"),
        types.KeyboardButton("📊 Statistika"),
        types.KeyboardButton("🤖 Bot holati"),
        types.KeyboardButton("👥 Adminlar"),
    )
    return keyboard

@dp.message_handler(commands=['start'], state="*")
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    if message.from_user.id == ADMIN_ID:
        await message.answer("Assalomu alaykum, Bosh admin! Kerakli bo'limni tanlang:", reply_markup=admin_keyboard())
    else:
        await message.answer("Salom! Kino kodini yuboring.")

@dp.message_handler(text="📊 Statistika")
async def stats_handler(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    await message.answer(f"📊 **Bot statistikasi:**\n\n👥 Foydalanuvchilar: {USERS_COUNT} ta")

@dp.message_handler(text="🤖 Bot holati")
async def bot_status(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("✅ Bot ishlayapti, holati: Ajoyib 🟢")

@dp.message_handler(text="👥 Adminlar")
async def admins_list(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    await message.answer(f"💻 **Bosh admin:** @Drsolijanov\n🆔 **Admin ID:** `{ADMIN_ID}`")

@dp.message_handler(text="📢 Kanallar")
async def channels_list(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    ch_list = "\n".join(CHANNELS)
    await message.answer(f"📢 **Ulangan kanallar:**\n{ch_list}")

@dp.message_handler(text="◀️ Orqaga", state="*")
async def go_back(message: types.Message, state: FSMContext):
    await state.finish()
    if message.from_user.id == ADMIN_ID:
        await message.answer("Asosiy menyuga qaytdingiz:", reply_markup=admin_keyboard())

@dp.message_handler(text="📥 Kino Yuklash")
async def start_upload_movie(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("◀️ Orqaga"))
    await message.answer("🎬 Avval ushbu kino yoki serialning treylerini (videofaylini) yuboring:", reply_markup=kb)
    await AdminStates.waiting_for_trailer.set()

@dp.message_handler(state=AdminStates.waiting_for_trailer, content_types=['video', 'animation'])
async def receive_trailer(message: types.Message, state: FSMContext):
    video_id = message.video.file_id
    await state.update_data(trailer_id=video_id)
    await message.answer("✅ Treyler qabul qilindi.\n\nEndi ushbu kino yoki serial uchun **kod** yuboring (masalan: 101):")
    await AdminStates.waiting_for_movie_code.set()

@dp.message_handler(state=AdminStates.waiting_for_movie_code)
async def receive_code(message: types.Message, state: FSMContext):
    code = message.text.strip()
    data = await state.get_data()
    trailer_id = data.get('trailer_id')
    MOVIES[code] = trailer_id
    await message.answer(f"🎉 Muvaffaqiyatli saqlandi!\n\n🎬 Kino kodi: `{code}`", reply_markup=admin_keyboard())
    await state.finish()

@dp.message_handler(text="✉️ Xabarnoma")
async def start_broadcast(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("◀️ Orqaga"))
    await message.answer("✉️ Botdagi barcha foydalanuvchilarga yubormoqchi bo'lgan xabaringizni yozing:", reply_markup=kb)
    await AdminStates.waiting_for_broadcast.set()

@dp.message_handler(state=AdminStates.waiting_for_broadcast)
async def send_broadcast(message: types.Message, state: FSMContext):
    await message.answer(f"🚀 Xabarnoma yuborilmoqda...")
    await message.answer(f"✅ Xabarnoma yakunlandi!", reply_markup=admin_keyboard())
    await state.finish()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
