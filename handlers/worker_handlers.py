# handlers/worker_handlers.py

from aiogram import Router, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from utils.keyboard_utils import worker_main_menu, sessions_editor_menu, back_menu
from utils.file_utils import load_json, save_json
from utils.monitoring_utils import login_to_fansly
import os

router = Router()

# Данные работников
WORKERS_FILE = "data/workers.json"
workers = load_json(WORKERS_FILE)

# Состояния пользователей
user_states = {}

# Обработчики для работников
@router.message(lambda message: message.text == "Редактор сессий")
async def sessions_editor(message: types.Message):
    await message.answer("Выберите действие:", reply_markup=sessions_editor_menu())

@router.message(lambda message: message.text == "Список сессий")
async def show_sessions_list(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_states or "worker_login" not in user_states[user_id]:
        await message.answer("Ошибка: данные работника не найдены.")
        return

    worker_login = user_states[user_id]["worker_login"]
    sessions = workers[worker_login]["sessions"]

    if not sessions:
        await message.answer("Нет активных сессий.")
        return

    sessions_list = "\n".join([f"🔹 {session['username']} ({session['email']})" for session in sessions])
    await message.answer(f"📜 Список активных сессий:\n{sessions_list}")

@router.message(lambda message: message.text == "Добавить модель в сессию")
async def add_model_to_session(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_states or "worker_login" not in user_states[user_id]:
        await message.answer("Ошибка: данные работника не найдены.")
        return

    if not accounts:
        await message.answer("Нет доступных моделей.")
        return

    user_states[user_id] = {"stage": "adding_model_to_session"}
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=acc["username"])] for acc in accounts.values()] + [
            [KeyboardButton(text="🔙 Назад")],
        ],
        resize_keyboard=True
    )
    await message.answer("Выберите модель для добавления в сессию:", reply_markup=kb)

@router.message(lambda message: message.from_user.id in user_states and user_states[message.from_user.id]["stage"] == "adding_model_to_session")
async def handle_add_model_to_session(message: types.Message):
    user_id = message.from_user.id
    selected_username = message.text

    if selected_username not in [acc["username"] for acc in accounts.values()]:
        await message.answer("❌ Модель не найдена. Попробуйте еще раз.", reply_markup=sessions_editor_menu())
        return

    email = next(email for email, acc in accounts.items() if acc["username"] == selected_username)
    worker_login = user_states[user_id]["worker_login"]

    workers[worker_login]["sessions"].append({
        "username": selected_username,
        "email": email,
        "notifications_enabled": True
    })
    save_json(WORKERS_FILE, workers)

    await message.answer(f"✅ Модель **{selected_username}** добавлена в сессию!", reply_markup=sessions_editor_menu())
    user_states.pop(user_id, None)