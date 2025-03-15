import os
import asyncio
import logging
import json
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO)

TOKEN = ""
ACCOUNTS_FILE = "accounts.json"
STATUS_FILE = "status.json"
NOTIFICATIONS_FILE = "notifications.json"
WORKERS_FILE = "workers.json"
CONFIG_FILE = "config.json"
ACTIVE_SESSIONS_FILE = "active_sessions.json"

if not os.path.exists("data"):
    os.makedirs("data")


def load_active_sessions():
    try:
        with open(ACTIVE_SESSIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_active_sessions(data):
    with open(ACTIVE_SESSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


active_monitoring_sessions = load_active_sessions()


def ensure_account_folder(email, category=None):
    account_folder = os.path.join("data", email)
    if not os.path.exists(account_folder):
        os.makedirs(account_folder)

    if category:
        category_folder = os.path.join(account_folder, category.lower())
        if not os.path.exists(category_folder):
            os.makedirs(category_folder)
        return category_folder

    return account_folder


def load_chat_statuses(email, category=None):
    if category:
        account_folder = ensure_account_folder(email, category)
    else:
        account_folder = ensure_account_folder(email)

    static_users_file = os.path.join(account_folder, "static_users.json")
    if not os.path.exists(static_users_file):
        return {}

    static_users = load_json("static_users.json", email, category)

    all_statuses = {}

    for filename in os.listdir(account_folder):
        if filename.startswith("chat_statuses_page_") and filename.endswith(".json"):
            filepath = os.path.join(account_folder, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    filtered_data = {user: data[user] for user in data if user in static_users}
                    all_statuses.update(filtered_data)
            except Exception as e:
                logging.error(f"Ошибка при загрузке файла {filename}: {e}")

    return all_statuses


def load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        default_config = {
            "admin_login": "admin",
            "admin_password": "admin123"
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=4)
        return default_config


def load_workers():
    try:
        with open(WORKERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def load_json(filename, email=None, category=None):
    if email:
        if category:
            account_folder = ensure_account_folder(email, category)
        else:
            account_folder = ensure_account_folder(email)
        filepath = os.path.join(account_folder, filename)
    else:
        filepath = os.path.join("data", filename)

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_json(filename, data, email=None, category=None):
    if email:
        if category:
            account_folder = ensure_account_folder(email, category)
        else:
            account_folder = ensure_account_folder(email)
        filepath = os.path.join(account_folder, filename)
    else:
        filepath = os.path.join("data", filename)

    with open(filepath, "w") as f:
        json.dump(data, f, indent=4)


def save_to_json(data, email, category, filename="chat_statuses.json"):
    category_folder = ensure_account_folder(email, category)
    filepath = os.path.join(category_folder, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def merge_json_files(email, category, output_filename="all_chat_statuses.json"):
    category_folder = ensure_account_folder(email, category)
    all_data = {}

    for filename in os.listdir(category_folder):
        if filename.startswith("chat_statuses_page_") and filename.endswith(".json"):
            filepath = os.path.join(category_folder, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                all_data.update(data)

    output_filepath = os.path.join(category_folder, output_filename)
    with open(output_filepath, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=4, ensure_ascii=False)


def split_message(text, max_length=4096):
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]


bot = Bot(token=TOKEN)
dp = Dispatcher()
accounts = load_json(ACCOUNTS_FILE)
prev_statuses = load_json(STATUS_FILE)
notifications = load_json(NOTIFICATIONS_FILE)
user_states = {}
monitoring_active = {}
user_drivers = {}
active_sessions = {}
user_lists = {}
config = load_config()
workers = load_workers()


def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Приступить к работе")],
            [KeyboardButton(text="Выйти из аккаунта")],
        ],
        resize_keyboard=True
    )


def admin_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Выбор раздела (модели/работники)")],
            [KeyboardButton(text="Выйти из аккаунта")]
        ],
        resize_keyboard=True
    )


def admin_back_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔙 Назад (Админ)")],
            [KeyboardButton(text="🏠 Главное меню")]
        ],
        resize_keyboard=True
    )


def models_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Запустить сессию"), KeyboardButton(text="Отключить сессию")],  # Добавлена кнопка
            [KeyboardButton(text="Редактирование Нейросети")],
            [KeyboardButton(text="Вывести список моделей")],
            [KeyboardButton(text="🔙 Шаг назад")],
            [KeyboardButton(text="Выйти из аккаунта")]
        ],
        resize_keyboard=True
    )


def monitoring_menu(user_id=None):
    chat_id = str(user_id)
    keyboard = [
        [KeyboardButton(text="Редактировать сессии")],
        [KeyboardButton(text="Текущий онлайн")],
    ]

    all_notifications_enabled = True
    if chat_id in notifications:
        all_notifications_enabled = all(
            notifications[chat_id][email][category]["enabled"]
            for email in notifications[chat_id]
            for category in notifications[chat_id][email]
        )

    toggle_button_text = "Остановить мониторинг" if all_notifications_enabled else "Восстановить мониторинг"
    keyboard.append([KeyboardButton(text=toggle_button_text)])

    keyboard.append([KeyboardButton(text="🏠 Главное меню")])

    if user_id and user_id in active_sessions and active_sessions[user_id]:
        keyboard.insert(0, [KeyboardButton(text="➕ Добавить модель к сессии")])

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def back_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔙 Назад")],
            [KeyboardButton(text="🏠 Главное меню")],
        ],
        resize_keyboard=True
    )


def workers_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Добавить работника")],
            [KeyboardButton(text="Удалить работника")],
            [KeyboardButton(text="🔙 Назад (Работник)")],
            [KeyboardButton(text="Выйти из аккаунта")]
        ],
        resize_keyboard=True
    )


def workers_back_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔙 Назад (Работник)")],
            [KeyboardButton(text="🏠 Главное меню")]
        ],
        resize_keyboard=True
    )


def monitoring_section_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Subscribers")],
            [KeyboardButton(text="VIPs")],
            [KeyboardButton(text="Followers")],
            [KeyboardButton(text="All")],
            [KeyboardButton(text="🏠 Главное меню")]
        ],
        resize_keyboard=True
    )


async def start_monitoring_for_admin(email, category, driver, chat_id):
    active_sessions_data = load_active_sessions()

    if email not in active_sessions_data:
        active_sessions_data[email] = {
            "username": accounts[email]["username"],
            "categories": {
                category: {
                    "chat_ids": []
                }
            }
        }
    else:
        if category not in active_sessions_data[email]["categories"]:
            active_sessions_data[email]["categories"][category] = {
                "chat_ids": []
            }

    save_active_sessions(active_sessions_data)

    task = asyncio.create_task(monitor_users(email, driver, chat_id, None, category))
    if email not in active_monitoring_sessions:
        active_monitoring_sessions[email] = {}
    if category not in active_monitoring_sessions[email]:
        active_monitoring_sessions[email][category] = {
            "driver": driver,
            "task": task,
            "chat_ids": active_sessions_data[email]["categories"][category]["chat_ids"]
        }

    user_id = chat_id
    if user_id in user_states and user_states[user_id].get("is_admin", False):
        await bot.send_message(chat_id,
                               f"✅ Мониторинг для модели {accounts[email]['username']} (Категория: {category}) запущен.",
                               reply_markup=admin_main_menu())


async def restore_monitoring_sessions():
    active_sessions_data = load_active_sessions()

    for email, data in active_sessions_data.items():
        for category, session_data in data.get("categories", {}).items():
            chat_ids = session_data["chat_ids"]
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
            task = asyncio.create_task(monitor_users(email, driver, chat_ids[0], None, category))
            if email not in active_monitoring_sessions:
                active_monitoring_sessions[email] = {}
            active_monitoring_sessions[email][category] = {
                "driver": driver,
                "task": task,
                "chat_ids": chat_ids
            }


async def connect_user_to_monitoring(email, category, chat_id):
    active_sessions_data = load_active_sessions()

    if email in active_sessions_data and category in active_sessions_data[email].get("categories", {}):
        chat_id_str = str(chat_id)
        if chat_id_str not in active_sessions_data[email]["categories"][category]["chat_ids"]:
            active_sessions_data[email]["categories"][category]["chat_ids"].append(chat_id_str)
            save_active_sessions(active_sessions_data)

        if email in active_monitoring_sessions and category in active_monitoring_sessions[email]:
            if chat_id_str not in active_monitoring_sessions[email][category]["chat_ids"]:
                active_monitoring_sessions[email][category]["chat_ids"].append(chat_id_str)

        if chat_id_str not in notifications:
            notifications[chat_id_str] = {}
        if email not in notifications[chat_id_str]:
            notifications[chat_id_str][email] = {}
        if category not in notifications[chat_id_str][email]:
            notifications[chat_id_str][email][category] = {"enabled": True}

        save_json(NOTIFICATIONS_FILE, notifications)

        await bot.send_message(chat_id, f"✅ Вы подключены к мониторингу модели {accounts[email]['username']} (Категория: {category}).", reply_markup=monitoring_menu(chat_id))
    else:
        await bot.send_message(chat_id, f"❌ Мониторинг для модели {accounts[email]['username']} (Категория: {category}) не запущен.")


async def stop_monitoring(email, category, chat_id):
    active_sessions_data = load_active_sessions()

    if email in active_sessions_data and category in active_sessions_data[email].get("categories", {}):
        if chat_id in active_sessions_data[email]["categories"][category]["chat_ids"]:
            active_sessions_data[email]["categories"][category]["chat_ids"].remove(chat_id)

            if email in active_monitoring_sessions and category in active_monitoring_sessions[email]:
                active_monitoring_sessions[email][category]["chat_ids"].remove(chat_id)

            save_active_sessions(active_sessions_data)
            await bot.send_message(chat_id, f"❌ Вы отключены от мониторинга модели {accounts[email]['username']} (Категория: {category}).")
        else:
            await bot.send_message(chat_id, f"❌ Вы не подключены к мониторингу модели {accounts[email]['username']} (Категория: {category}).")
    else:
        await bot.send_message(chat_id, f"❌ Мониторинг для модели {accounts[email]['username']} (Категория: {category}) не запущен.")


@asynccontextmanager
async def loading_indicator(message: types.Message, original_reply_markup: ReplyKeyboardMarkup):
    loading_markup = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Выполняется загрузка, подождите...")]],
        resize_keyboard=True
    )
    sent_message = await message.answer("⏳", reply_markup=loading_markup)

    try:
        yield

    finally:
        await bot.delete_message(chat_id=sent_message.chat.id, message_id=sent_message.message_id)
        await message.answer("✅ Загрузка завершена!", reply_markup=original_reply_markup)


@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer("Добро пожаловать! Нажмите кнопку 'Войти', чтобы продолжить.", reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Войти")]],
        resize_keyboard=True
    ))


@dp.message(lambda message: message.text == "Войти")
async def login_handler(message: types.Message):
    user_id = message.from_user.id
    user_states[user_id] = {"stage": "waiting_for_login"}
    await message.answer("Введите логин:", reply_markup=types.ReplyKeyboardRemove())


@dp.message(lambda message: message.text == "Выбор раздела (модели/работники)")
async def select_section(message: types.Message):
    user_id = message.from_user.id
    user_states[user_id] = {"stage": "selecting_section"}
    await message.answer("Выберите раздел:", reply_markup=ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Модели")],
            [KeyboardButton(text="Работники")],
            [KeyboardButton(text="🔙 Назад (Админ)")]
        ],
        resize_keyboard=True
    ))


@dp.message(lambda message: message.text == "Работники")
async def show_workers(message: types.Message):
    if not workers:
        await message.answer("Нет добавленных работников.", reply_markup=admin_main_menu())
        return

    workers_list = [f"{login}" for login in workers.keys()]
    await message.answer("Список работников:\n" + "\n".join(workers_list), reply_markup=workers_menu())


@dp.message(lambda message: message.text == "Добавить работника")
async def add_worker(message: types.Message):
    user_id = message.from_user.id
    user_states[user_id] = {"stage": "waiting_for_worker_login"}
    await message.answer("Введите логин нового работника:")


@dp.message(lambda message: message.from_user.id in user_states and user_states[message.from_user.id]["stage"] == "waiting_for_worker_login")
async def get_worker_login(message: types.Message):
    user_id = message.from_user.id
    user_states[user_id]["login"] = message.text
    user_states[user_id]["stage"] = "waiting_for_worker_password"
    await message.answer("Введите пароль нового работника:")


@dp.message(lambda message: message.text == "🔙 Назад (Админ)")
async def admin_go_back(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_states and user_states[user_id].get("is_admin", False):
        await message.answer("Вы вернулись в главное меню админки.", reply_markup=admin_main_menu())
    else:
        await message.answer("Вы вернулись в главное меню.", reply_markup=admin_main_menu())


@dp.message(lambda message: message.text == "🔙 Назад (Работник)")
async def worker_go_back(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_states:
        stage = user_states[user_id].get("stage", "")
        if stage == "waiting_for_worker_login":
            await message.answer("Вы вернулись в меню работников.", reply_markup=admin_main_menu())
        elif stage == "waiting_for_worker_password":
            user_states[user_id]["stage"] = "waiting_for_worker_login"
            await message.answer("Введите логин нового работника:", reply_markup=workers_back_menu())
        elif stage == "deleting_worker":
            await message.answer("Вы вернулись в меню работников.", reply_markup=admin_main_menu())
        else:
            user_states.pop(user_id, None)
            await message.answer("Вы вернулись в главное меню.", reply_markup=admin_main_menu())
    else:
        await message.answer("Вы уже в главном меню.", reply_markup=admin_main_menu())


@dp.message(lambda message: message.from_user.id in user_states and user_states[message.from_user.id]["stage"] == "waiting_for_worker_password")
async def get_worker_password(message: types.Message):
    user_id = message.from_user.id
    login = user_states[user_id]["login"]
    password = message.text
    workers[login] = {"password": password}
    save_json(WORKERS_FILE, workers)
    del user_states[user_id]
    await message.answer(f"✅ Работник {login} успешно добавлен!", reply_markup=workers_menu())


@dp.message(lambda message: message.text == "Удалить работника")
async def delete_worker(message: types.Message):
    user_id = message.from_user.id
    user_states[user_id] = {"stage": "deleting_worker"}
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=worker)] for worker in workers.keys()] + [
            [KeyboardButton(text="🔙 Назад")]],
        resize_keyboard=True
    )
    await message.answer("Выберите работника для удаления:", reply_markup=kb)


@dp.message(lambda message: message.text == "Вывести список моделей")
async def handle_show_models(message: types.Message):
    await show_models(message)


@dp.message(lambda message: message.text == "Отключить сессию")
async def stop_session_handler(message: types.Message):
    active_sessions_data = load_active_sessions()

    if not active_sessions_data:
        await message.answer("Нет активных сессий для отключения.", reply_markup=models_menu())
        return

    sessions_list = []
    for email, data in active_sessions_data.items():
        username = data["username"]
        for category, session_data in data["categories"].items():
            sessions_list.append(f"{username} ({category})")

    if not sessions_list:
        await message.answer("Нет активных сессий для отключения.", reply_markup=models_menu())
        return

    keyboard = [
        [KeyboardButton(text=f"❌ Отключить {session}")] for session in sessions_list
    ]
    keyboard.append([KeyboardButton(text="🔙 Назад")])

    await message.answer(
        "Выберите сессию для отключения:",
        reply_markup=ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
    )


@dp.message(lambda message: message.text.startswith("❌ Отключить "))
async def stop_selected_session(message: types.Message):
    selected_session = message.text.replace("❌ Отключить ", "").strip()

    active_sessions_data = load_active_sessions()

    for email, data in active_sessions_data.items():
        username = data["username"]
        for category, session_data in data["categories"].items():
            if f"{username} ({category})" == selected_session:
                if email in active_monitoring_sessions and category in active_monitoring_sessions[email]:
                    active_monitoring_sessions[email][category]["task"].cancel()
                    active_monitoring_sessions[email][category]["driver"].quit()
                    del active_monitoring_sessions[email][category]

                del active_sessions_data[email]["categories"][category]
                if not active_sessions_data[email]["categories"]:
                    del active_sessions_data[email]

                save_active_sessions(active_sessions_data)
                await message.answer(f"✅ Сессия для {selected_session} успешно отключена.", reply_markup=models_menu())
                return

    await message.answer("❌ Сессия не найдена.", reply_markup=models_menu())


@dp.message(lambda message: message.from_user.id in user_states and user_states[message.from_user.id]["stage"] == "deleting_worker")
async def confirm_delete_worker(message: types.Message):
    selected_worker = message.text
    if selected_worker in workers:
        del workers[selected_worker]
        save_json(WORKERS_FILE, workers)
        await message.answer(f"✅ Работник {selected_worker} успешно удален!", reply_markup=workers_menu())
    else:
        await message.answer("❌ Работник не найден.", reply_markup=workers_menu())


@dp.message(lambda message: message.text == "Модели")
async def show_models(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_states and user_states[user_id].get("is_admin", False):
        user_states[user_id]["is_admin"] = True

    active_sessions_data = load_active_sessions()

    if not accounts:
        await message.answer("Нет добавленных моделей.", reply_markup=admin_main_menu())

    models_list = []
    for email, account in accounts.items():
        username = account["username"]
        categories = ["Subscribers", "VIPs", "Followers", "All"]

        category_statuses = []
        for category in categories:
            is_active = False
            if email in active_sessions_data and category in active_sessions_data[email]["categories"]:
                is_active = True
            status_icon = "🟢" if is_active else "🔴"
            category_statuses.append(f"{status_icon} {category}")

        models_list.append(f"👤 {username}\n" + "\n".join(category_statuses))

    response = "Список моделей и их категорий:\n\n" + "\n\n".join(models_list)
    await message.answer(response, reply_markup=models_menu())


@dp.message(lambda message: message.from_user.id in user_states and user_states[message.from_user.id]["stage"] == "waiting_for_login")
async def get_login(message: types.Message):
    user_id = message.from_user.id
    user_states[user_id]["login"] = message.text
    user_states[user_id]["stage"] = "waiting_for_password"
    await message.answer("Введите пароль:")


@dp.message(lambda message: message.from_user.id in user_states and user_states[message.from_user.id]["stage"] == "waiting_for_password")
async def check_password(message: types.Message):
    user_id = message.from_user.id
    entered_password = message.text
    login = user_states[user_id]["login"]

    if login == config["admin_login"] and entered_password == config["admin_password"]:
        user_states[user_id]["is_admin"] = True
        await message.answer("Добро пожаловать в админку!", reply_markup=admin_main_menu())
    elif login in workers and workers[login]["password"] == entered_password:
        await message.answer("Добро пожаловать в меню работника!", reply_markup=main_menu())
    else:
        await message.answer("Неверный логин или пароль. Попробуйте снова.", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Войти")]],
            resize_keyboard=True
        ))
    user_states.pop(user_id, None)


@dp.message(lambda message: message.text == "🏠 Главное меню")
async def back_to_main(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_states and user_states[user_id].get("is_admin", False):
        await message.answer("Вы вернулись в главное меню админки.", reply_markup=admin_main_menu())
    else:
        await message.answer("Вы вернулись в главное меню.", reply_markup=main_menu())


@dp.message(lambda message: message.text == "🔙 Назад")
async def go_back(message: types.Message):
    user_id = message.from_user.id

    if user_id in user_states:
        stage = user_states[user_id].get("stage", "")

        if stage == "waiting_for_password":
            user_states[user_id]["stage"] = "waiting_for_login"
            await message.answer("Введите логин:", reply_markup=back_menu())
        elif stage == "waiting_for_worker_login":
            await message.answer("Вы вернулись в меню работников.", reply_markup=workers_menu())
        elif stage == "waiting_for_worker_password":
            user_states[user_id]["stage"] = "waiting_for_worker_login"
            await message.answer("Введите логин нового работника:", reply_markup=back_menu())
        elif stage == "deleting_worker":
            await message.answer("Вы вернулись в меню работников.", reply_markup=workers_menu())
        elif stage == "selecting_section":
            await message.answer("Вы вернулись в главное меню админки.", reply_markup=admin_main_menu())
        else:
            user_states.pop(user_id, None)
            await message.answer("Вы вернулись в главное меню.", reply_markup=main_menu())
        return

    if user_id in active_sessions and active_sessions[user_id]:
        await message.answer("Возвращаемся в меню мониторинга.", reply_markup=monitoring_menu(user_id))
        return

    await message.answer("Вы уже в главном меню.", reply_markup=monitoring_menu())


@dp.message(lambda message: message.text == "🔙 Шаг назад")
async def step_back(message: types.Message):
    user_id = message.from_user.id

    if user_id in user_states:
        stage = user_states[user_id].get("stage", "")

        if stage == "waiting_for_worker_login":
            await message.answer("Вы вернулись в меню работников.", reply_markup=admin_main_menu())
        elif stage == "waiting_for_worker_password":
            user_states[user_id]["stage"] = "waiting_for_worker_login"
            await message.answer("Введите логин нового работника:", reply_markup=admin_back_menu())
        elif stage == "deleting_worker":
            await message.answer("Вы вернулись в меню работников.", reply_markup=admin_main_menu())
        elif stage == "selecting_section":
            await message.answer("Вы вернулись в главное меню админки.", reply_markup=admin_main_menu())
        else:
            user_states.pop(user_id, None)
            await message.answer("Вы вернулись в главное меню.", reply_markup=admin_main_menu())
        return

    if user_id in active_sessions and active_sessions[user_id]:
        await message.answer("Возвращаемся в меню мониторинга.", reply_markup=monitoring_menu(user_id))
        return

    await message.answer("Вы уже в главном меню.", reply_markup=main_menu())


@dp.message(lambda message: message.text == "🔙 Шаг назад")
async def step_back_in_models(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_states and user_states[user_id].get("is_admin", False):
        await message.answer("Вы вернулись в главное меню админки.", reply_markup=admin_main_menu())
    else:
        await message.answer("Вы вернулись в главное меню.", reply_markup=main_menu())


@dp.message(lambda message: message.text == "🔙 Шаг назад" and user_states.get(message.from_user.id, {}).get("stage") == "deleting_worker")
async def step_back_in_workers(message: types.Message):
    user_id = message.from_user.id
    user_states[user_id] = {"stage": "selecting_section"}
    await message.answer("Вы вернулись в главное меню админки.", reply_markup=admin_main_menu())


@dp.message(lambda message: message.text == "🔙 Назад" and user_states.get(message.from_user.id, {}).get("stage") == "monitoring")
async def step_back_in_monitoring(message: types.Message):
    user_id = message.from_user.id
    user_states[user_id] = {"stage": "selecting_section"}
    await message.answer("Вы вернулись в главное меню админки.", reply_markup=admin_main_menu())


@dp.message(lambda message: message.text == "Приступить к работе")
async def start_work(message: types.Message):
    active_sessions_data = load_active_sessions()

    if not active_sessions_data:
        await message.answer("⚠️ Модели еще не настроены, обратитесь к администратору.", reply_markup=main_menu())
        return

    user_id = message.from_user.id
    user_states[user_id] = {"stage": "selecting_category"}

    keyboard = []
    for email, data in active_sessions_data.items():
        username = data["username"]
        categories = data["categories"]
        for category in categories:
            keyboard.append([KeyboardButton(text=f"{username} ({category})")])

    keyboard.append([KeyboardButton(text="🏠 Главное меню")])
    await message.answer("📌 Выберите категорию для мониторинга:", reply_markup=ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True))


@dp.message(lambda message: message.text == "Выйти из аккаунта")
async def logout(message: types.Message):
    user_id = message.from_user.id
    user_states.pop(user_id, None)
    await message.answer("Вы вышли из аккаунта. Для входа нажмите кнопку 'Войти'.", reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Войти")]],
        resize_keyboard=True
    ))


@dp.message(lambda message: message.text == "Запустить сессию")
async def start_session_from_admin(message: types.Message):
    user_id = message.from_user.id

    if not accounts:
        await message.answer("⚠️ Нет добавленных моделей. Добавьте хотя бы одну!", reply_markup=admin_main_menu())
        return

    user_states[user_id] = {"stage": "selecting_model_for_session", "is_admin": True}
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=account["username"])] for account in accounts.values()] + [
            [KeyboardButton(text="🏠 Главное меню")]],
        resize_keyboard=True
    )
    await message.answer("📌 Выберите модель для запуска сессии:", reply_markup=kb)


@dp.message(lambda message: message.from_user.id in user_states and user_states[message.from_user.id]["stage"] == "selecting_category")
async def handle_category_selection(message: types.Message):
    user_id = message.from_user.id
    selected_text = message.text

    active_sessions_data = load_active_sessions()

    for email, data in active_sessions_data.items():
        username = data["username"]
        categories = data["categories"]
        for category in categories:
            if f"{username} ({category})" == selected_text:
                async with loading_indicator(message, monitoring_menu(user_id)):
                    await connect_user_to_monitoring(email, category, message.chat.id)
                if user_id in user_states:
                    del user_states[user_id]
                return

    await message.answer("❌ Категория не найдена.", reply_markup=main_menu())


@dp.message(lambda message: message.from_user.id in user_states and user_states[message.from_user.id]["stage"] == "selecting_model_for_session")
async def handle_model_selection_for_session(message: types.Message):
    user_id = message.from_user.id
    selected_username = message.text

    if selected_username not in [acc["username"] for acc in accounts.values()]:
        await message.answer("❌ Модель не найдена. Попробуйте еще раз.", reply_markup=admin_main_menu())
        return

    email = next(email for email, acc in accounts.items() if acc["username"] == selected_username)
    password = accounts[email]["password"]
    chat_id = str(message.chat.id)

    async with loading_indicator(message, admin_main_menu()):
        twofa_needed, driver = await login_to_fansly(email, password)

    if not twofa_needed:
        await start_monitoring_for_admin(email, "All", driver, chat_id)
    else:
        user_states[user_id] = {"stage": "waiting_for_2fa", "email": email, "driver": driver, "is_admin": True}  # Сохраняем флаг администратора
        await message.answer(f"🔐 Введите 2FA-код для модели **{selected_username}**:", reply_markup=back_menu(), parse_mode="Markdown")


@dp.message(lambda message: message.text == "Удалить модель")
async def delete_model(message: types.Message):
    if not accounts:
        await message.answer("⚠️ Нет добавленных моделей.", reply_markup=main_menu())
        return

    user_id = message.from_user.id
    user_states[user_id] = {"stage": "deleting_model"}
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=account["username"])] for account in accounts.values()] + [
            [KeyboardButton(text="🏠 Главное меню")]],
        resize_keyboard=True
    )
    await message.answer("📌 Выберите модель для удаления:", reply_markup=kb)


@dp.message(lambda message: message.from_user.id in user_states and user_states[message.from_user.id]["stage"] == "deleting_model")
async def confirm_delete_model(message: types.Message):
    selected_username = message.text
    email = next(email for email, acc in accounts.items() if acc["username"] == selected_username)

    del accounts[email]
    save_json(ACCOUNTS_FILE, accounts)

    account_folder = os.path.join("data", email)
    if os.path.exists(account_folder):
        import shutil
        shutil.rmtree(account_folder)

    await message.answer(f"✅ Модель **{selected_username}** успешно удалена!", reply_markup=main_menu())


@dp.message(lambda message: message.text == "Добавить модель")
async def add_model(message: types.Message):
    user_id = message.from_user.id
    user_states[user_id] = {"stage": "waiting_for_model_email"}
    await message.answer("Введите email модели:", reply_markup=back_menu())


@dp.message(lambda message: message.from_user.id in user_states and user_states[message.from_user.id]["stage"] == "waiting_for_model_email")
async def get_model_email(message: types.Message):
    user_id = message.from_user.id
    user_states[user_id]["email"] = message.text
    user_states[user_id]["stage"] = "waiting_for_model_password"
    await message.answer("Введите пароль модели:", reply_markup=back_menu())


@dp.message(lambda message: message.from_user.id in user_states and user_states[message.from_user.id]["stage"] == "waiting_for_model_password")
async def get_model_password(message: types.Message):
    user_id = message.from_user.id
    user_states[user_id]["password"] = message.text
    user_states[user_id]["stage"] = "waiting_for_model_username"
    await message.answer("Введите ник модели:", reply_markup=back_menu())


@dp.message(lambda message: message.from_user.id in user_states and user_states[message.from_user.id]["stage"] == "waiting_for_model_username")
async def get_model_username(message: types.Message):
    user_id = message.from_user.id
    user_states[user_id]["username"] = message.text
    email = user_states[user_id]["email"]
    accounts[email] = {
        "email": email,
        "password": user_states[user_id]["password"],
        "username": user_states[user_id]["username"]
    }
    save_json(ACCOUNTS_FILE, accounts)
    del user_states[user_id]
    await message.answer("✅ Аккаунт успешно добавлен!", reply_markup=main_menu())


@dp.message(lambda message: message.text == "Приступить к работе")
async def start_work(message: types.Message):
    if not accounts:
        await message.answer("⚠️ Нет добавленных моделей. Добавьте хотя бы одну!", reply_markup=main_menu())
        return

    user_id = message.from_user.id
    user_states[user_id] = {"stage": "selecting_model"}
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=account["username"])] for account in accounts.values()] + [
            [KeyboardButton(text="🏠 Главное меню")]],
        resize_keyboard=True
    )
    await message.answer("📌 Выберите модель:", reply_markup=kb)


@dp.message(lambda message: message.from_user.id in user_states and user_states[message.from_user.id]["stage"] == "selecting_model")
async def monitor_model(message: types.Message):
    selected_username = message.text
    email = next(email for email, acc in accounts.items() if acc["username"] == selected_username)
    chat_id = str(message.chat.id)

    await connect_user_to_monitoring(email, "All", chat_id)


@dp.message(lambda message: message.from_user.id in user_states and user_states[message.from_user.id]["stage"] == "waiting_for_2fa")
async def enter_2fa(message: types.Message):
    try:
        user_id = message.from_user.id
        twofa_code = message.text
        driver = user_states[user_id]["driver"]

        async with loading_indicator(message, monitoring_section_menu()):
            logging.info(f"Получен 2FA-код от пользователя {user_id}: {twofa_code}")

            twofa_field = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "fansly_twofa")))

            twofa_field.clear()
            
            twofa_field.send_keys(twofa_code)
            twofa_field.send_keys(Keys.RETURN)

            WebDriverWait(driver, 30).until(EC.url_changes(driver.current_url))

            user_states[user_id]["stage"] = "waiting_for_monitoring_section"
            user_states[user_id]["driver"] = driver

        await message.answer("✅ Выберите раздел для мониторинга:", reply_markup=monitoring_section_menu())

    except Exception as e:
        logging.error(f"Ошибка при вводе 2FA: {e}")
        await message.answer("❌ Произошла ошибка при вводе 2FA. Попробуйте еще раз.", reply_markup=types.ReplyKeyboardRemove())


@dp.message(lambda message: message.from_user.id in user_states and user_states[message.from_user.id]["stage"] == "waiting_for_monitoring_section")
async def select_monitoring_section(message: types.Message):
    try:
        user_id = message.from_user.id
        email = user_states[user_id]["email"]
        driver = user_states[user_id]["driver"]
        section = message.text
        chat_id = str(message.chat.id)

        if section in ["Subscribers", "VIPs", "Followers", "All"]:
            is_already_running = False
            if user_id in active_sessions:
                for session in active_sessions[user_id]:
                    if session["email"] == email and session.get("category") == section:
                        is_already_running = True
                        break

            if is_already_running:
                await message.answer(f"⚠️ Мониторинг для категории {section} уже запущен.", reply_markup=monitoring_section_menu())
                return

            if chat_id not in notifications:
                notifications[chat_id] = {}
            if email not in notifications[chat_id]:
                notifications[chat_id][email] = {}
            if section not in notifications[chat_id][email]:
                notifications[chat_id][email][section] = {"enabled": True}

            save_json(NOTIFICATIONS_FILE, notifications)
            logging.info(f"Уведомления для категории {section} включены: {notifications}")

            if user_id not in active_sessions:
                active_sessions[user_id] = []
            active_sessions[user_id].append({
                "username": accounts[email]["username"],
                "email": email,
                "driver": driver,
                "category": section
            })

            active_sessions_data = load_active_sessions()

            if email not in active_sessions_data:
                active_sessions_data[email] = {
                    "username": accounts[email]["username"],
                    "categories": {
                        section: {
                            "chat_ids": []
                        }
                    }
                }
            else:
                if section not in active_sessions_data[email]["categories"]:
                    active_sessions_data[email]["categories"][section] = {
                        "chat_ids": []
                    }
                else:
                    active_sessions_data[email]["categories"][section]["chat_ids"].append()

            save_active_sessions(active_sessions_data)

            task = asyncio.create_task(monitor_users(email, driver, chat_id, user_id, section))
            if email not in active_monitoring_sessions:
                active_monitoring_sessions[email] = {}
            if section not in active_monitoring_sessions[email]:
                active_monitoring_sessions[email][section] = {
                    "driver": driver,
                    "task": task,
                    "chat_ids": active_sessions_data[email]["categories"][section]["chat_ids"]
                }

            await message.answer(f"✅ Запускаем мониторинг раздела {section}...", reply_markup=models_menu())
            monitoring_active[user_id] = True
            user_drivers[user_id] = driver

            user_states.pop(user_id, None)

            asyncio.create_task(monitor_users(email, driver, message.chat.id, user_id, section))
        else:
            await message.answer("❌ Неизвестный раздел. Пожалуйста, выберите раздел из меню.", reply_markup=models_menu())

    except Exception as e:
        logging.error(f"Ошибка при выборе раздела мониторинга: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте еще раз.")


@dp.message(lambda message: message.text == "Текущий онлайн")
async def show_online_users(message: types.Message):
    user_id = message.from_user.id
    chat_id = str(message.chat.id)

    active_sessions_data = load_active_sessions()

    user_sessions = []
    for email, data in active_sessions_data.items():
        for category, session_data in data.get("categories", {}).items():
            if chat_id in session_data["chat_ids"]:
                user_sessions.append({
                    "email": email,
                    "category": category
                })

    if not user_sessions:
        await message.answer("⚠️ Вы не подключены ни к одной модели для мониторинга.", reply_markup=monitoring_menu(user_id))
        return

    async with loading_indicator(message, monitoring_menu(user_id)):
        online_users = []
        for session in user_sessions:
            email = session["email"]
            category = session["category"]

            chat_statuses = load_chat_statuses(email, category)

            online_users.extend([
                f"🔹 {chat} — 🟢 <b>ОНЛАЙН</b> (Модель: {accounts[email]['username']}, Категория: {category})"
                for chat, user_data in chat_statuses.items() if user_data.get("is_online", False)
            ])

        if not online_users:
            await message.answer("📭 В данный момент никого нет в сети.")
            return

        header = f"📜 <b>Список пользователей онлайн:</b>\n"
        response = header + "\n".join(online_users)

        message_parts = split_message(response)

        for part in message_parts:
            await message.answer(part, parse_mode="HTML")


@dp.message(lambda message: message.text == "Редактировать сессии")
async def show_active_sessions(message: types.Message):
    chat_id = str(message.chat.id)

    active_sessions_data = load_active_sessions()
    user_sessions = []

    for email, data in active_sessions_data.items():
        for category, session_data in data.get("categories", {}).items():
            if chat_id in session_data["chat_ids"]:
                user_sessions.append({
                    "email": email,
                    "username": data["username"],
                    "category": category
                })

    if not user_sessions:
        await message.answer("Нет активных сессий.", reply_markup=main_menu())
        return

    session_list = []
    keyboard = []

    for session in user_sessions:
        email = session["email"]
        username = session["username"]
        category = session["category"]
        is_enabled = notifications.get(chat_id, {}).get(email, {}).get(category, {}).get("enabled", True)

        status = "🔔" if is_enabled else "🔕"
        session_list.append(f"{status} {username} (Категория: {category})")

        toggle_text = f"🔕 Отключить уведомления для {username} ({category})" if is_enabled else f"🔔 Включить уведомления для {username} ({category})"
        keyboard.append([KeyboardButton(text=toggle_text)])

        keyboard.append([KeyboardButton(text=f"❌ Удалить {username} ({category})")])

    keyboard.append([KeyboardButton(text="➕ Добавить модель к сессии")])
    keyboard.append([KeyboardButton(text="🔙 Назад")])
    keyboard.append([KeyboardButton(text="🏠 Главное меню")])

    await message.answer(
        f"Активные сессии:\n" + "\n".join(session_list),
        reply_markup=ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
    )


@dp.message(lambda message: message.text in ["Остановить мониторинг", "Восстановить мониторинг"])
async def toggle_all_notifications(message: types.Message):
    user_id = message.from_user.id
    chat_id = str(message.chat.id)

    if chat_id not in notifications:
        notifications[chat_id] = {}

    all_enabled = all(
        notifications[chat_id][email][category]["enabled"]
        for email in notifications[chat_id]
        for category in notifications[chat_id][email]
    )

    new_state = not all_enabled
    for email in notifications[chat_id]:
        for category in notifications[chat_id][email]:
            notifications[chat_id][email][category]["enabled"] = new_state

    save_json(NOTIFICATIONS_FILE, notifications)

    status = "включены" if new_state else "отключены"
    await message.answer(f"Все уведомления {status}.", reply_markup=monitoring_menu(user_id))


@dp.message(lambda message: message.text.startswith("🔔") or message.text.startswith("🔕"))
async def toggle_notifications(message: types.Message):
    user_id = message.from_user.id
    chat_id = str(message.chat.id)

    button_text = message.text
    username = button_text.split("для ")[1].split(" (")[0]
    category = button_text.split(" (")[1].rstrip(")")

    email = next(email for email, acc in accounts.items() if acc["username"] == username)

    if chat_id not in notifications:
        notifications[chat_id] = {}
    if email not in notifications[chat_id]:
        notifications[chat_id][email] = {}
    if category not in notifications[chat_id][email]:
        notifications[chat_id][email][category] = {"enabled": True}

    is_enabled = notifications[chat_id][email][category]["enabled"]
    notifications[chat_id][email][category]["enabled"] = not is_enabled
    save_json(NOTIFICATIONS_FILE, notifications)

    status = "включены" if not is_enabled else "отключены"
    await message.answer(f"Уведомления для модели {username} ({category}) {status}.",
                         reply_markup=monitoring_menu(user_id))


@dp.message(lambda message: message.text.startswith("❌ Удалить "))
async def remove_session(message: types.Message):
    user_id = message.from_user.id
    chat_id = str(message.chat.id)

    button_text = message.text
    username = button_text.replace("❌ Удалить ", "").split(" (")[0]
    category = button_text.split(" (")[1].rstrip(")")

    email = next(email for email, acc in accounts.items() if acc["username"] == username)

    active_sessions_data = load_active_sessions()

    if email in active_sessions_data and category in active_sessions_data[email].get("categories", {}):
        if chat_id in active_sessions_data[email]["categories"][category]["chat_ids"]:
            active_sessions_data[email]["categories"][category]["chat_ids"].remove(chat_id)
            save_active_sessions(active_sessions_data)

            if email in active_monitoring_sessions and category in active_monitoring_sessions[email]:
                if chat_id in active_monitoring_sessions[email][category]["chat_ids"]:
                    active_monitoring_sessions[email][category]["chat_ids"].remove(chat_id)

            await message.answer(f"❌ Вы отключены от мониторинга модели {username} (Категория: {category}).",
                                 reply_markup=monitoring_menu(user_id))
        else:
            await message.answer(f"❌ Вы не подключены к мониторингу модели {username} (Категория: {category}).",
                                 reply_markup=monitoring_menu(user_id))
    else:
        await message.answer(f"❌ Мониторинг для модели {username} (Категория: {category}) не запущен.",
                             reply_markup=monitoring_menu(user_id))


async def disconnect_user_from_monitoring(email, category, chat_id):
    active_sessions_data = load_active_sessions()

    if email in active_sessions_data and category in active_sessions_data[email].get("categories", {}):
        chat_id_str = str(chat_id)
        if chat_id_str in active_sessions_data[email]["categories"][category]["chat_ids"]:
            active_sessions_data[email]["categories"][category]["chat_ids"].remove(chat_id_str)
            save_active_sessions(active_sessions_data)

            if email in active_monitoring_sessions and category in active_monitoring_sessions[email]:
                if chat_id_str in active_monitoring_sessions[email][category]["chat_ids"]:
                    active_monitoring_sessions[email][category]["chat_ids"].remove(chat_id_str)

            await bot.send_message(chat_id, f"❌ Вы отключены от мониторинга модели {accounts[email]['username']} (Категория: {category}).")
        else:
            await bot.send_message(chat_id, f"❌ Вы не подключены к мониторингу модели {accounts[email]['username']} (Категория: {category}).")
    else:
        await bot.send_message(chat_id, f"❌ Мониторинг для модели {accounts[email]['username']} (Категория: {category}) не запущен.")


@dp.message(lambda message: message.text == "➕ Добавить модель к сессии")
async def add_model_to_session(message: types.Message):
    user_id = message.from_user.id
    chat_id = str(message.chat.id)

    active_sessions_data = load_active_sessions()

    if not active_sessions_data:
        await message.answer("⚠️ Нет запущенных моделей для подключения.", reply_markup=monitoring_menu(user_id))
        return

    available_models = []
    for email, data in active_sessions_data.items():
        username = data["username"]
        for category in data["categories"]:
            if chat_id not in data["categories"][category]["chat_ids"]:
                available_models.append(f"{username} ({category})")

    if not available_models:
        await message.answer("⚠️ Вы уже подключены ко всем запущенным моделям.", reply_markup=monitoring_menu(user_id))
        return

    keyboard = [[KeyboardButton(text=model)] for model in available_models]
    keyboard.append([KeyboardButton(text="🔙 Назад")])

    await message.answer(
        "📌 Выберите модель для подключения:",
        reply_markup=ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
    )


@dp.message(lambda message: message.text.endswith(")"))
async def handle_model_selection_for_connection(message: types.Message):
    chat_id = str(message.chat.id)

    selected_text = message.text
    username = selected_text.split(" (")[0]
    category = selected_text.split(" (")[1].rstrip(")")

    email = next(email for email, acc in accounts.items() if acc["username"] == username)

    await connect_user_to_monitoring(email, category, chat_id)


@dp.message(lambda message: message.from_user.id in user_states and user_states[message.from_user.id]["stage"] == "adding_model_to_session")
async def handle_add_model_to_session(message: types.Message):
    user_id = message.from_user.id
    selected_username = message.text

    if selected_username not in [acc["username"] for acc in accounts.values()]:
        await message.answer("❌ Модель не найдена. Попробуйте еще раз.", reply_markup=monitoring_menu(user_id))
        return

    email = next(email for email, acc in accounts.items() if acc["username"] == selected_username)
    chat_id = str(message.chat.id)

    if email in active_monitoring_sessions:
        for category in active_monitoring_sessions[email]:
            if chat_id not in active_monitoring_sessions[email][category]["chat_ids"]:
                active_monitoring_sessions[email][category]["chat_ids"].append(chat_id)
                await bot.send_message(chat_id, f"✅ Вы подключены к мониторингу модели {selected_username} (Категория: {category}).", reply_markup=monitoring_menu(user_id))
    else:
        await bot.send_message(chat_id, f"❌ Мониторинг для модели {selected_username} не запущен.", reply_markup=monitoring_menu(user_id))


async def login_to_fansly(username, password):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920x1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--log-level=3")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        driver.get("https://fansly.com/")
        logging.info("Открыта страница Fansly.")

        try:
            await asyncio.sleep(2)
            modal = driver.find_element(By.CLASS_NAME, "xdModal")
            driver.execute_script("arguments[0].remove();", modal)
            logging.info("Всплывающее окно закрыто!")
            await asyncio.sleep(2)
        except NoSuchElementException:
            logging.info("Всплывающее окно не найдено, продолжаем...")

        try:
            login_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'btn solid-blue')][2]"))
            )
            login_button.click()
            print("Кнопка Login найдена и нажата!")

        except Exception as e:
            print("Ошибка: Кнопка Login не найдена или недоступна.", e)

        username_field = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.ID, "fansly_login"))
        )
        username_field.send_keys(username)
        logging.info("Введен username/email.")

        password_field = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.ID, "fansly_password"))
        )
        password_field.send_keys(password)
        logging.info("Введен пароль.")

        password_field.send_keys(Keys.RETURN)
        logging.info("Форма входа отправлена.")

        await asyncio.sleep(2)

        if "twofa" in driver.page_source:
            logging.info("Требуется 2FA.")
            return True, driver

        logging.info("Вход выполнен успешно.")
        return False, driver

    except Exception as e:
        logging.error(f"Ошибка при входе в Fansly: {e}")
        driver.quit()
        raise


async def get_chat_statuses(driver, email, category):
    driver.get("https://fansly.com/messages")
    await asyncio.sleep(2)

    try:
        modal = driver.find_element(By.CLASS_NAME, "xdModal")
        driver.execute_script("arguments[0].remove();", modal)
        logging.info("Всплывающее окно закрыто!")
        await asyncio.sleep(2)
    except NoSuchElementException:
        logging.info("Всплывающее окно не найдено, продолжаем...")

    try:
        category_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (By.XPATH, f"//div[contains(@class, 'bubble')]/xd-localization-string[contains(text(), '{category}')]"))
        )
        category_button.click()
        await asyncio.sleep(2)
    except Exception as e:
        logging.error(f"⚠️ Ошибка при нажатии на кнопку '{category}': {e}")
        return {}, {}

    try:
        chat_container = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "message-list"))
        )
    except Exception as e:
        logging.error(f"❌ Ошибка: контейнер чатов не найден! {e}")
        return {}, {}

    all_chat_statuses = {}
    unique_users = set()
    scroll_step = 1000
    max_attempts = 40
    attempt = 0

    while attempt < max_attempts:
        logging.info(f"🔄 Шаг {attempt + 1}: Прокрутка списка пользователей для {accounts[email]['username']} {category}...")
        driver.execute_script(f"arguments[0].scrollTop += {scroll_step};", chat_container)
        await asyncio.sleep(5)

        users = driver.find_elements(By.CLASS_NAME, "message")

        for user in users:
            try:
                username = user.find_element(By.CLASS_NAME, "display-name").text

                user_link_element = user.find_element(By.CLASS_NAME, "username-wrapper")
                user_link = user_link_element.get_attribute("href")

                user_username = user_link.split("/")[-1]
                if user_username.startswith("@"):
                    user_username = user_username[1:]

                if username not in unique_users:
                    unique_users.add(username)
                    online_indicator = user.find_elements(By.CLASS_NAME, "online-indicator")

                    is_online = False
                    if online_indicator:
                        status_classes = online_indicator[0].get_attribute("class")
                        is_online = "available" in status_classes or "away" in status_classes

                    all_chat_statuses[username] = {
                        "is_online": is_online,
                        "username": user_username
                    }
            except Exception as e:
                logging.error(f"Ошибка при обработке пользователя: {e}")
                continue

        save_to_json(all_chat_statuses, email, category, filename=f"chat_statuses_page_{attempt + 1}.json")
        logging.info(f"📂 Данные сохранены в файл chat_statuses_page_{attempt + 1}.json для {accounts[email]['username']} {category}")

        new_height = driver.execute_script("return arguments[0].scrollHeight;", chat_container)
        current_height = driver.execute_script("return arguments[0].scrollTop;", chat_container)
        if current_height + chat_container.size["height"] >= new_height:
            logging.info(f"📏 Достигнут конец списка пользователей.")
            break

        attempt += 1

    merge_json_files(email, category, output_filename="all_chat_statuses.json")
    logging.info(f"✅ Все данные объединены в файл all_chat_statuses.json")

    return list(unique_users), all_chat_statuses


async def monitor_users(email, driver, chat_id, user_id, category):
    global prev_statuses

    static_users_file = os.path.join("data", email, category.lower(), "static_users.json")
    if not os.path.exists(static_users_file):
        static_users, _ = await get_chat_statuses(driver, email, category)
        save_json("static_users.json", static_users, email, category)
    else:
        static_users = load_json("static_users.json", email, category)

    prev_statuses = load_json(STATUS_FILE, email, category)
    is_first_run = True

    asyncio.create_task(update_user_list_periodically(email, category))

    while monitoring_active.get(user_id, False):
        try:
            if is_first_run:
                username = accounts[email]["username"]
                await bot.send_message(
                    chat_id,
                    f"✅ Модель **{username}** (Категория: {category}) полностью готова к работе!",
                    parse_mode="Markdown"
                )
                is_first_run = False

            logging.info(f"🚀 Начало новой итерации мониторинга для {email} (Категория: {category})")

            _, chat_statuses = await get_chat_statuses(driver, email, category)
            filtered_statuses = {user: chat_statuses[user] for user in static_users if user in chat_statuses}

            if filtered_statuses:
                logging.info(f"🔍 Проверено {len(filtered_statuses)} пользователей для {email} (Категория: {category}).")
                await check_status_updates(email, filtered_statuses, category)
                prev_statuses = filtered_statuses
                save_json(STATUS_FILE, prev_statuses, email, category)

            logging.info(f"🏁 Итерация мониторинга завершена для {email} (Категория: {category})")

            await asyncio.sleep(10)

        except Exception as e:
            logging.error(f"Ошибка при мониторинге {email}: {e}")
            await asyncio.sleep(10)


async def check_status_updates(email, new_statuses, category):
    global prev_statuses

    if email not in active_monitoring_sessions or category not in active_monitoring_sessions[email]:
        logging.warning(f"Мониторинг для модели {email} (Категория: {category}) не запущен.")
        return

    chat_ids = active_monitoring_sessions[email][category]["chat_ids"]

    prev_statuses = load_json(STATUS_FILE, email, category)

    if not prev_statuses:
        logging.warning(f"Нет предыдущих статусов для категории {email} {category}. Это первый запуск, уведомления пропускаются.")
        save_json(STATUS_FILE, new_statuses, email, category)
        return

    for user, user_data in new_statuses.items():
        if "is_online" not in user_data or "username" not in user_data:
            logging.error(f"Некорректные данные для пользователя {user}: {user_data}")
            continue

        was_online = prev_statuses.get(user, {}).get("is_online", False)
        is_online = user_data["is_online"]
        username = user_data["username"]

        if not was_online and is_online:
            notification_text = (
                f"🔔 {user} теперь онлайн!\n"
                f"Модель: {accounts[email]['username']}\n"
                f"Категория: {category}"
            )

            user_link = f"https://fansly.com/{username}/posts"

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Перейти к пользователю...", url=user_link)]
            ])

            for chat_id in chat_ids:
                if chat_id in notifications and email in notifications[chat_id] and category in notifications[chat_id][email] and notifications[chat_id][email][category]["enabled"]:
                    try:
                        await bot.send_message(chat_id, notification_text, reply_markup=keyboard)
                        logging.info(f"Уведомление отправлено для пользователя {user} в чат {chat_id}")
                    except Exception as e:
                        logging.error(f"Ошибка при отправке уведомления в чат {chat_id}: {e}")

    save_json(STATUS_FILE, new_statuses, email, category)


async def update_user_list_periodically(email, category, interval=7200):
    while True:
        await asyncio.sleep(interval)
        logging.info(f"🔄 Обновление списка пользователей и статусов для {email} (Категория: {category})...")

        try:
            static_users = load_json("static_users.json", email, category)

            current_statuses = load_json(STATUS_FILE, email, category)

            all_chat_statuses = load_json("all_chat_statuses.json", email, category)

            new_users = [user for user in all_chat_statuses if user not in static_users]

            if new_users:
                logging.info(f"🆕 Найдены новые пользователи: {new_users}")
                static_users.extend(new_users)
                save_json("static_users.json", static_users, email, category)

                for user in new_users:
                    if user in all_chat_statuses:
                        current_statuses[user] = all_chat_statuses[user]

                save_json(STATUS_FILE, current_statuses, email, category)
                logging.info(f"✅ Статусы для новых пользователей обновлены.")
            else:
                logging.info(f"🆗 Новых пользователей не обнаружено.")

        except Exception as e:
            logging.error(f"❌ Ошибка при обновлении списка пользователей и статусов: {e}")


async def main():
    asyncio.create_task(restore_monitoring_sessions())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
