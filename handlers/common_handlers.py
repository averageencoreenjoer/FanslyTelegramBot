from aiogram import Router, types
from aiogram.filters import Command
from config import ADMIN_CREDENTIALS
from utils.keyboard_utils import main_menu, admin_main_menu, worker_main_menu, back_menu
from utils.file_utils import load_json, save_json
import logging
import json

router = Router()

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Данные работников
WORKERS_FILE = "workers.json"
workers = load_json(WORKERS_FILE)

# Состояния пользователей
user_states = {}

# Обработчики для старта и авторизации
@router.message(Command("start"))
async def start_handler(message: types.Message):
    user_states[message.from_user.id] = {"stage": "waiting_for_login"}
    await message.answer("Введите логин:")

@router.message(lambda message: message.from_user.id in user_states and user_states[message.from_user.id]["stage"] == "waiting_for_login")
async def handle_login(message: types.Message):
    login = message.text.strip()
    user_states[message.from_user.id]["login"] = login
    user_states[message.from_user.id]["stage"] = "waiting_for_password"
    await message.answer("Введите пароль:", reply_markup=back_menu())

@router.message(lambda message: message.from_user.id in user_states and user_states[message.from_user.id]["stage"] == "waiting_for_password")
async def handle_password(message: types.Message):
    password = message.text.strip()
    login = user_states[message.from_user.id]["login"]

    logging.info(f"Попытка входа: логин={login}, пароль={password}")
    logging.info(f"Данные workers: {workers}")

    if login == ADMIN_CREDENTIALS["login"] and password == ADMIN_CREDENTIALS["password"]:
        await message.answer("Добро пожаловать в админку!", reply_markup=admin_main_menu())
        user_states[message.from_user.id]["role"] = "admin"
        user_states.pop(message.from_user.id, None)  # Сбрасываем состояние после успешной авторизации
    elif login in workers and workers[login]["password"] == password:
        await message.answer("Добро пожаловать в рабочее меню!", reply_markup=worker_main_menu())
        user_states[message.from_user.id]["role"] = "worker"
        user_states[message.from_user.id]["worker_login"] = login
        user_states.pop(message.from_user.id, None)  # Сбрасываем состояние после успешной авторизации
    else:
        await message.answer("Неверный логин или пароль. Попробуйте еще раз.", reply_markup=back_menu())
        user_states[message.from_user.id]["stage"] = "waiting_for_login"