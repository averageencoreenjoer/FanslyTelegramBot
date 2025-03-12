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
from webdriver_manager.chrome import ChromeDriverManager

logging.basicConfig(level=logging.INFO)

TOKEN = "7745376176:AAH0q7LS3k_PCB9ZzWlxYyY9fS5eFPMAxMc"
ACCOUNTS_FILE = "accounts.json"
STATUS_FILE = "status.json"
NOTIFICATIONS_FILE = "notifications.json"

if not os.path.exists("data"):
    os.makedirs("data")


def load_config():
    config_file = "config.json"
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        default_config = {"editor_password": "1234567890123456"}
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=4)
        return default_config


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

    all_statuses = {}

    for filename in os.listdir(account_folder):
        if filename.startswith("chat_statuses_page_") and filename.endswith(".json"):
            filepath = os.path.join(account_folder, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    all_statuses.update(data)
            except Exception as e:
                logging.error(f"Ошибка при загрузке файла {filename}: {e}")

    return all_statuses


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


def split_message(text, max_length=4096):
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]


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


bot = Bot(token=TOKEN)
dp = Dispatcher()
accounts = load_json(ACCOUNTS_FILE)
prev_statuses = load_json(STATUS_FILE)
notifications = load_json(NOTIFICATIONS_FILE)
user_states = {}
monitoring_active = {}
user_drivers = {}
active_sessions = {}


def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Приступить к работе")],
            [KeyboardButton(text="Редактор учетных записей")],
        ],
        resize_keyboard=True
    )


def account_editor_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Добавить модель")],
            [KeyboardButton(text="Удалить модель")],
            [KeyboardButton(text="🏠 Главное меню")],
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


@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer("Выберите действие:", reply_markup=main_menu())


@dp.message(lambda message: message.text == "🏠 Главное меню")
async def back_to_main(message: types.Message):
    user_id = message.from_user.id
    user_states.pop(user_id, None)
    monitoring_active[user_id] = False

    if user_id in user_drivers:
        driver = user_drivers[user_id]
        try:
            driver.quit()
        except Exception as e:
            print(f"⚠️ Ошибка при закрытии драйвера: {e}")
        del user_drivers[user_id]

    await message.answer("Вы вернулись в главное меню.", reply_markup=main_menu())


@dp.message(lambda message: message.text == "Редактор учетных записей")
async def request_password(message: types.Message):
    user_id = message.from_user.id
    user_states[user_id] = {"stage": "waiting_for_editor_password"}
    await message.answer("🔐 Введите 16-значный пароль для доступа к редактору учетных записей:", reply_markup=back_menu())


@dp.message(lambda message: message.from_user.id in user_states and user_states[message.from_user.id]["stage"] == "waiting_for_editor_password")
async def check_editor_password(message: types.Message):
    user_id = message.from_user.id
    entered_password = message.text.strip()

    config = load_config()
    correct_password = config.get("editor_password", "1234567890123456")

    if entered_password == correct_password:
        await message.answer("✅ Доступ разрешен. Выберите действие:", reply_markup=account_editor_menu())
        user_states.pop(user_id, None)
    else:
        await message.answer("❌ Отказано в доступе. Неверный пароль.", reply_markup=main_menu())
        user_states.pop(user_id, None)


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


@dp.message(lambda message: message.text == "🔙 Назад")
async def go_back(message: types.Message):
    user_id = message.from_user.id

    if user_id in user_states:
        stage = user_states[user_id]["stage"]

        if stage == "waiting_for_password":
            user_states[user_id]["stage"] = "waiting_for_email"
            await message.answer("Введите email модели:", reply_markup=back_menu())
        else:
            user_states.pop(user_id)
            await message.answer("Вы вернулись в главное меню.", reply_markup=main_menu())
        return

    if user_id in active_sessions and active_sessions[user_id]:
        await message.answer("Возвращаемся в меню мониторинга.", reply_markup=monitoring_menu(user_id))
        return

    await message.answer("Вы уже в главном меню.", reply_markup=main_menu())


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
    password = accounts[email]["password"]
    chat_id = str(message.chat.id)

    if chat_id not in notifications:
        notifications[chat_id] = {}
    if email not in notifications[chat_id]:
        notifications[chat_id][email] = {}

    notifications[chat_id][email]["All"] = {"enabled": True}
    save_json(NOTIFICATIONS_FILE, notifications)
    logging.info(f"Уведомления сохранены: {notifications}")

    await message.answer(f"⏳ Запуск мониторинга для модели **{selected_username}**...", reply_markup=main_menu())

    twofa_needed, driver = await login_to_fansly(email, password, message.chat.id)

    if not twofa_needed:
        await message.answer("✅ Авторизация успешна! Запускаем мониторинг...", reply_markup=monitoring_menu(message.from_user.id))
        monitoring_active[message.from_user.id] = True
        user_drivers[message.from_user.id] = driver

        if message.from_user.id not in active_sessions:
            active_sessions[message.from_user.id] = []
        active_sessions[message.from_user.id].append({
            "username": selected_username,
            "email": email,
            "driver": driver,
            "category": "All"
        })

        asyncio.create_task(monitor_users(email, driver, message.chat.id, message.from_user.id, "All"))
    else:
        user_states[message.from_user.id] = {"stage": "waiting_for_2fa", "email": email, "driver": driver}
        await message.answer(f"🔐 Введите 2FA-код для модели **{accounts[email]['username']}**:", reply_markup=back_menu(), parse_mode="Markdown")


@dp.message(lambda message: message.from_user.id in user_states and user_states[message.from_user.id]["stage"] == "waiting_for_2fa")
async def enter_2fa(message: types.Message):
    try:
        user_id = message.from_user.id
        email = user_states[user_id]["email"]
        twofa_code = message.text
        driver = user_states[user_id]["driver"]

        logging.info(f"Получен 2FA-код от пользователя {user_id}: {twofa_code}")
        await message.answer("🔑 Вводим 2FA-код...")

        twofa_field = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "fansly_twofa")))
        twofa_field.send_keys(twofa_code)
        twofa_field.send_keys(Keys.RETURN)

        WebDriverWait(driver, 30).until(EC.url_changes(driver.current_url))

        await message.answer("✅ Авторизация успешна! Выберите раздел для мониторинга:", reply_markup=monitoring_section_menu())

        user_states[user_id]["stage"] = "waiting_for_monitoring_section"
        user_states[user_id]["driver"] = driver

    except Exception as e:
        logging.error(f"Ошибка при вводе 2FA: {e}")
        await message.answer("❌ Произошла ошибка при вводе 2FA. Попробуйте еще раз.")


@dp.message(lambda message: message.from_user.id in user_states and user_states[message.from_user.id]["stage"] == "waiting_for_monitoring_section")
async def select_monitoring_section(message: types.Message):
    try:
        user_id = message.from_user.id
        email = user_states[user_id]["email"]
        driver = user_states[user_id]["driver"]
        section = message.text

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

            if user_id not in active_sessions:
                active_sessions[user_id] = []
            active_sessions[user_id].append({
                "username": accounts[email]["username"],
                "email": email,
                "driver": driver,
                "category": section
            })

            await message.answer(f"✅ Запускаем мониторинг раздела {section}...", reply_markup=monitoring_menu(user_id))
            monitoring_active[user_id] = True
            user_drivers[user_id] = driver

            user_states.pop(user_id, None)

            asyncio.create_task(monitor_users(email, driver, message.chat.id, user_id, section))
        else:
            await message.answer("❌ Неизвестный раздел. Пожалуйста, выберите раздел из меню.", reply_markup=monitoring_section_menu())

    except Exception as e:
        logging.error(f"Ошибка при выборе раздела мониторинга: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте еще раз.")


@dp.message(lambda message: message.text == "Текущий онлайн")
async def show_online_users(message: types.Message):
    user_id = message.from_user.id
    if user_id not in active_sessions or not active_sessions[user_id]:
        await message.answer("⚠️ Нет активных сессий!")
        return

    online_users = []
    for session in active_sessions[user_id]:
        email = session["email"]
        category = session.get("category", "All")
        chat_statuses = load_chat_statuses(email, category)
        if not chat_statuses:
            await message.answer("📥 Список пользователей загружается...")
            return

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
    user_id = message.from_user.id
    chat_id = str(message.chat.id)

    if user_id not in active_sessions or not active_sessions[user_id]:
        await message.answer("Нет активных сессий.", reply_markup=main_menu())
        return

    sessions = active_sessions[user_id]
    session_list = []

    for session in sessions:
        email = session["email"]
        username = session["username"]
        category = session.get("category", "All")
        is_enabled = notifications.get(chat_id, {}).get(email, {}).get(category, {}).get("enabled", True)

        status = "🔔" if is_enabled else "🔕"
        session_list.append(f"{status} {username} (Категория: {category})")

    keyboard = []
    for session in sessions:
        email = session["email"]
        username = session["username"]
        category = session.get("category", "All")
        is_enabled = notifications.get(chat_id, {}).get(email, {}).get(category, {}).get("enabled", True)

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

    if user_id not in active_sessions or not active_sessions[user_id]:
        await message.answer("Нет активных сессий.", reply_markup=main_menu())
        return

    button_text = message.text
    username = button_text.split("для ")[1].split(" (")[0]
    category = button_text.split(" (")[1].rstrip(")")

    session_to_toggle = None
    for session in active_sessions[user_id]:
        if session["username"] == username and session.get("category") == category:
            session_to_toggle = session
            break

    if not session_to_toggle:
        await message.answer(f"Сессия для модели {username} ({category}) не найдена.", reply_markup=monitoring_menu(user_id))
        return

    email = session_to_toggle["email"]

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
    await message.answer(f"Уведомления для модели {username} ({category}) {status}.", reply_markup=monitoring_menu(user_id))


@dp.message(lambda message: message.text.startswith("❌ Удалить "))
async def remove_session(message: types.Message):
    user_id = message.from_user.id
    if user_id not in active_sessions or not active_sessions[user_id]:
        await message.answer("Нет активных сессий.", reply_markup=main_menu())
        return

    button_text = message.text
    username = button_text.replace("❌ Удалить ", "").split(" (")[0]
    category = button_text.split(" (")[1].rstrip(")")

    sessions = active_sessions[user_id]
    for session in sessions:
        if session["username"] == username and session.get("category") == category:
            if "driver" in session:
                try:
                    session["driver"].quit()
                except Exception as e:
                    print(f"Ошибка при закрытии драйвера: {e}")

            sessions.remove(session)
            await message.answer(f"Сессия для модели {username} ({category}) удалена.", reply_markup=monitoring_menu(user_id))
            return

    await message.answer(f"Сессия для модели {username} ({category}) не найдена.", reply_markup=monitoring_menu(user_id))


@dp.message(lambda message: message.text == "➕ Добавить модель к сессии")
async def add_model_to_session(message: types.Message):
    user_id = message.from_user.id

    if not accounts:
        await message.answer("⚠️ Нет добавленных моделей. Добавьте хотя бы одну!", reply_markup=main_menu())
        return

    user_states[user_id] = {"stage": "adding_model_to_session"}
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=account["username"])] for account in accounts.values()] + [
            [KeyboardButton(text="🏠 Главное меню")]],
        resize_keyboard=True
    )
    await message.answer("📌 Выберите модель для добавления в сессию:", reply_markup=kb)


@dp.message(lambda message: message.from_user.id in user_states and user_states[message.from_user.id]["stage"] == "adding_model_to_session")
async def handle_add_model_to_session(message: types.Message):
    user_id = message.from_user.id
    selected_username = message.text

    if selected_username not in [acc["username"] for acc in accounts.values()]:
        await message.answer("❌ Модель не найдена. Попробуйте еще раз.", reply_markup=monitoring_menu(user_id))
        return

    email = next(email for email, acc in accounts.items() if acc["username"] == selected_username)
    password = accounts[email]["password"]

    if user_id in active_sessions:
        for session in active_sessions[user_id]:
            if session["email"] == email:
                await message.answer(f"⚠️ Модель **{selected_username}** уже добавлена в сессию.", reply_markup=monitoring_menu(user_id))
                return

    twofa_needed, driver = await login_to_fansly(email, password, message.chat.id)

    if not twofa_needed:
        if user_id not in active_sessions:
            active_sessions[user_id] = []
        active_sessions[user_id].append({
            "username": selected_username,
            "email": email,
            "driver": driver,
            "category": "All"
        })

        await message.answer(f"✅ Модель **{selected_username}** успешно добавлена к сессии!", reply_markup=monitoring_menu(user_id))
        asyncio.create_task(monitor_users(email, driver, message.chat.id, user_id, "All"))
    else:
        user_states[user_id] = {"stage": "waiting_for_2fa", "email": email, "driver": driver}
        await message.answer(f"🔐 Введите 2FA-код для модели **{selected_username}**:", reply_markup=back_menu(), parse_mode="Markdown")


async def login_to_fansly(username, password, chat_id):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920x1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--log-level=3")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    driver.get("https://fansly.com/")

    username_field = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.NAME, "username")))
    password_field = driver.find_element(By.NAME, "password")
    username_field.send_keys(username)
    password_field.send_keys(password)
    password_field.send_keys(Keys.RETURN)

    await asyncio.sleep(5)

    if "twofa" in driver.page_source:
        return True, driver

    return False, driver


async def get_chat_statuses(driver, chat_id, email, category):
    driver.get("https://fansly.com/messages")
    await asyncio.sleep(5)

    try:
        modal = driver.find_element(By.CLASS_NAME, "xdModal")
        driver.execute_script("arguments[0].remove();", modal)
        logging.info("Всплывающее окно закрыто!")
        await asyncio.sleep(2)
    except:
        logging.info("Всплывающее окно не найдено, продолжаем...")

    try:
        category_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (By.XPATH, f"//div[contains(@class, 'bubble')]/xd-localization-string[contains(text(), '{category}')]"))
        )
        category_button.click()
        await asyncio.sleep(5)
    except Exception as e:
        logging.error(f"⚠️ Ошибка при нажатии на кнопку '{category}': {e}")

    try:
        chat_container = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "message-list"))
        )
    except Exception as e:
        logging.error(f"❌ Ошибка: контейнер чатов не найден! {e}")
        return {}

    all_chat_statuses = {}
    unique_users = set()
    scroll_step = 1000
    max_attempts = 40
    attempt = 0

    while attempt < max_attempts:
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
        logging.info(f"Список пользователей для аккаунта {email} и категории {category} обновлен.")
        new_height = driver.execute_script("return arguments[0].scrollHeight;", chat_container)
        current_height = driver.execute_script("return arguments[0].scrollTop;", chat_container)
        if current_height + chat_container.size["height"] >= new_height:
            break

        attempt += 1

    merge_json_files(email, category, output_filename="all_chat_statuses.json")

    return all_chat_statuses


async def monitor_users(email, driver, chat_id, user_id, category):
    global prev_statuses

    prev_statuses = load_json(STATUS_FILE, email, category)

    while monitoring_active.get(user_id, False):
        try:
            chat_statuses = await get_chat_statuses(driver, chat_id, email, category)
            if chat_statuses:
                await check_status_updates(email, chat_statuses, chat_id, category)
                prev_statuses = chat_statuses
                save_json(STATUS_FILE, prev_statuses, email, category)

            await asyncio.sleep(10)

        except Exception as e:
            logging.error(f"Ошибка при мониторинге {email}: {e}")
            await asyncio.sleep(10)


async def check_status_updates(email, new_statuses, chat_id, category):
    global prev_statuses

    chat_id = str(chat_id)

    if (chat_id not in notifications or
        email not in notifications[chat_id] or
        category not in notifications[chat_id][email] or
        not notifications[chat_id][email][category]["enabled"]):
        logging.warning(f"Уведомления отключены для категории {category}.")
        return

    prev_statuses = load_json(STATUS_FILE, email, category)

    if not prev_statuses:
        logging.warning(f"Нет предыдущих статусов для категории {category}. Это первый запуск, уведомления пропускаются.")
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

            try:
                await bot.send_message(chat_id, notification_text, reply_markup=keyboard)
                logging.info(f"Уведомление отправлено для пользователя {user}")
            except Exception as e:
                logging.error(f"Ошибка при отправке уведомления: {e}")

    save_json(STATUS_FILE, new_statuses, email, category)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
