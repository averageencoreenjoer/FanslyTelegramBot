import os
import asyncio
import logging
import json
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
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

TOKEN = "7745376176:AAH0q7LS3k_PCB9ZzWlxYyY9fS5eFPMAxMc"  # paste tg bot token
ACCOUNTS_FILE = "accounts.json"
STATUS_FILE = "status.json"
NOTIFICATIONS_FILE = "notifications.json"

if not os.path.exists("data"):
    os.makedirs("data")


def load_json(filename):
    try:
        with open(f"data/{filename}", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_json(filename, data):
    with open(f"data/{filename}", "w") as f:
        json.dump(data, f, indent=4)


def save_to_json(data, filename="chat_statuses.json"):
    with open(f"data/{filename}", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def merge_json_files(output_filename="all_chat_statuses.json"):
    all_data = {}
    for filename in os.listdir("data"):
        if filename.startswith("chat_statuses_page_") and filename.endswith(".json"):
            with open(f"data/{filename}", "r", encoding="utf-8") as f:
                data = json.load(f)
                all_data.update(data)

    with open(f"data/{output_filename}", "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=4, ensure_ascii=False)


bot = Bot(token=TOKEN)
dp = Dispatcher()
accounts = load_json(ACCOUNTS_FILE)
prev_statuses = load_json(STATUS_FILE)
notifications = load_json(NOTIFICATIONS_FILE)
user_states = {}
monitoring_active = {}
user_drivers = {}


def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Выбрать модель")],
            [KeyboardButton(text="Добавить модель")],
        ],
        resize_keyboard=True
    )


def monitoring_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Текущий онлайн")],
            [KeyboardButton(text="Прервать мониторинг")],
            [KeyboardButton(text="Возобновить мониторинг")],
            [KeyboardButton(text="🏠 Главное меню")]
        ],
        resize_keyboard=True
    )


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
            [KeyboardButton(text="Subscribes")],
            [KeyboardButton(text="VIP")],
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


@dp.message(lambda message: message.text == "Добавить модель")
async def add_model(message: types.Message):
    user_states[message.from_user.id] = {"stage": "waiting_for_email"}
    await message.answer("Введите email модели:", reply_markup=back_menu())


@dp.message(lambda message: message.text == "🔙 Назад")
async def go_back(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_states:
        await message.answer("Вы уже в главном меню.", reply_markup=main_menu())
        return

    stage = user_states[user_id]["stage"]

    if stage == "waiting_for_password":
        user_states[user_id]["stage"] = "waiting_for_email"
        await message.answer("Введите email модели:", reply_markup=back_menu())
    else:
        user_states.pop(user_id)
        await message.answer("Вы вернулись в главное меню.", reply_markup=main_menu())


@dp.message(lambda message: message.from_user.id in user_states and user_states[message.from_user.id]["stage"] == "waiting_for_email")
async def get_email(message: types.Message):
    user_states[message.from_user.id]["email"] = message.text
    user_states[message.from_user.id]["stage"] = "waiting_for_password"
    await message.answer("Введите пароль модели:", reply_markup=back_menu())


@dp.message(lambda message: message.from_user.id in user_states and user_states[message.from_user.id]["stage"] == "waiting_for_password")
async def get_password(message: types.Message):
    user_states[message.from_user.id]["password"] = message.text
    email = user_states[message.from_user.id]["email"]
    accounts[email] = {
        "email": email,
        "password": user_states[message.from_user.id]["password"]
    }
    save_json(ACCOUNTS_FILE, accounts)
    del user_states[message.from_user.id]
    await message.answer("✅ Аккаунт успешно добавлен!", reply_markup=main_menu())


@dp.message(lambda message: message.text == "Выбрать модель")
async def select_model(message: types.Message):
    if not accounts:
        await message.answer("⚠️ Нет добавленных моделей. Добавьте хотя бы одну!", reply_markup=main_menu())
        return

    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=email)] for email in accounts.keys()] + [
            [KeyboardButton(text="🏠 Главное меню")]],
        resize_keyboard=True
    )
    await message.answer("📌 Выберите модель:", reply_markup=kb)


@dp.message(lambda message: message.text in accounts)
async def monitor_model(message: types.Message):
    email = message.text
    password = accounts[email]["password"]
    chat_id = str(message.chat.id)

    notifications[chat_id] = {"email": email, "enabled": True}
    save_json(NOTIFICATIONS_FILE, notifications)

    await message.answer("⏳ Авторизация в Fansly...", reply_markup=main_menu())

    twofa_needed, driver = await login_to_fansly(email, password, message.chat.id)

    if not twofa_needed:
        await message.answer("✅ Авторизация успешна! Запускаем мониторинг...", reply_markup=monitoring_menu())
        monitoring_active[message.from_user.id] = True  # Включаем мониторинг
        user_drivers[message.from_user.id] = driver  # Сохраняем драйвер
        asyncio.create_task(monitor_users(email, driver, message.chat.id, message.from_user.id))
    else:
        user_states[message.from_user.id] = {"stage": "waiting_for_2fa", "email": email, "driver": driver}
        await message.answer(f"🔐 Введите 2FA-код для модели **{email}**:", reply_markup=back_menu(), parse_mode="Markdown")


@dp.message(lambda message: message.text == "Прервать мониторинг")
async def stop_notifications(message: types.Message):
    chat_id = str(message.chat.id)
    if chat_id in notifications:
        notifications[chat_id]["enabled"] = False
        save_json(NOTIFICATIONS_FILE, notifications)
        await message.answer("🔕 Уведомления отключены!", reply_markup=monitoring_menu())
    else:
        await message.answer("⚠️ Нет активного мониторинга!")


@dp.message(lambda message: message.text == "Возобновить мониторинг")
async def resume_notifications(message: types.Message):
    chat_id = str(message.chat.id)
    if chat_id in notifications:
        notifications[chat_id]["enabled"] = True
        save_json(NOTIFICATIONS_FILE, notifications)
        await message.answer("🔔 Уведомления включены!", reply_markup=monitoring_menu())
    else:
        await message.answer("⚠️ Нет активного мониторинга!")


@dp.message(lambda message: message.text == "Текущий онлайн")
async def show_online_users(message: types.Message):
    chat_id = str(message.chat.id)
    if chat_id not in notifications:
        await message.answer("⚠️ Нет активного мониторинга!")
        return

    email = notifications[chat_id]["email"]
    if email not in prev_statuses:
        await message.answer("❌ Нет данных о пользователях.")
        return

    chat_statuses = prev_statuses[email]

    response = f"📜 <b>Список пользователей онлайн для {email}:</b>\n"
    online_users = [f"🔹 {chat} — 🟢 <b>ОНЛАЙН</b>" for chat, status in chat_statuses.items() if status]

    if online_users:
        response += "\n".join(online_users)
    else:
        response += "❌ Никто из пользователей не в сети."

    await message.answer(response, parse_mode="HTML")


@dp.message(lambda message: message.from_user.id in user_states and user_states[message.from_user.id]["stage"] == "waiting_for_2fa")
async def enter_2fa(message: types.Message):
    email = user_states[message.from_user.id]["email"]
    twofa_code = message.text
    driver = user_states[message.from_user.id]["driver"]

    await message.answer("🔑 Вводим 2FA-код...")

    twofa_field = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "fansly_twofa")))
    twofa_field.send_keys(twofa_code)
    twofa_field.send_keys(Keys.RETURN)

    WebDriverWait(driver, 20).until(EC.url_changes(driver.current_url))
    await message.answer("✅ Авторизация успешна! Выберите раздел для мониторинга:", reply_markup=monitoring_section_menu())

    user_states[message.from_user.id]["stage"] = "waiting_for_monitoring_section"
    user_states[message.from_user.id]["driver"] = driver


@dp.message(lambda message: message.from_user.id in user_states and user_states[message.from_user.id]["stage"] == "waiting_for_monitoring_section")
async def select_monitoring_section(message: types.Message):
    email = user_states[message.from_user.id]["email"]
    driver = user_states[message.from_user.id]["driver"]
    section = message.text

    if section == "Subscribes" or section == "VIP":
        await message.answer("⚠️ Функционал для этого раздела пока недоступен.", reply_markup=monitoring_section_menu())
    elif section == "All":
        await message.answer("✅ Запускаем мониторинг раздела All...", reply_markup=monitoring_menu())
        monitoring_active[message.from_user.id] = True
        user_drivers[message.from_user.id] = driver
        asyncio.create_task(monitor_users(email, driver, message.chat.id, message.from_user.id))
    else:
        await message.answer("❌ Неизвестный раздел. Пожалуйста, выберите раздел из меню.", reply_markup=monitoring_section_menu())


async def login_to_fansly(username, password, chat_id):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920x1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--log-level=3")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    await bot.send_message(chat_id, "🌍 Открываем сайт Fansly...")
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


async def get_chat_statuses(driver, chat_id):
        driver.get("https://fansly.com/messages")
        await asyncio.sleep(5)

        try:
            modal = driver.find_element(By.CLASS_NAME, "xdModal")
            driver.execute_script("arguments[0].remove();", modal)
            print("Всплывающее окно закрыто!")
            await asyncio.sleep(2)
        except:
            print("Всплывающее окно не найдено, продолжаем...")

        try:
            all_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//div[contains(@class, 'bubble')]/xd-localization-string[contains(text(), 'All')]"))
            )
            all_button.click()
            await asyncio.sleep(5)
        except Exception as e:
            print(f"⚠️ Ошибка при нажатии на кнопку 'All': {e}")

        try:
            chat_container = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "message-list"))
            )
        except Exception as e:
            print(f"❌ Ошибка: контейнер чатов не найден! {e}")
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

                    if username not in unique_users:
                        unique_users.add(username)
                        online_indicator = user.find_elements(By.CLASS_NAME, "online-indicator")

                        is_online = False
                        if online_indicator:
                            status_classes = online_indicator[0].get_attribute("class")
                            is_online = "available" in status_classes or "away" in status_classes

                        all_chat_statuses[username] = is_online
                except Exception as e:
                    print(f"Ошибка при обработке пользователя: {e}")
                    continue

            save_to_json(all_chat_statuses, filename=f"chat_statuses_page_{attempt + 1}.json")
            new_height = driver.execute_script("return arguments[0].scrollHeight;", chat_container)
            current_height = driver.execute_script("return arguments[0].scrollTop;", chat_container)
            if current_height + chat_container.size["height"] >= new_height:
                break

            attempt += 1

        merge_json_files(output_filename="all_chat_statuses.json")

        return all_chat_statuses


async def monitor_users(email, driver, chat_id, user_id):
    global prev_statuses
    while monitoring_active.get(user_id, False):
        try:
            chat_statuses = await get_chat_statuses(driver, chat_id)
            if chat_statuses:
                await check_status_updates(email, chat_statuses, chat_id)

            await asyncio.sleep(10)

        except Exception as e:
            logging.error(f"Ошибка при мониторинге {email}: {e}")
            await asyncio.sleep(10)


async def check_status_updates(email, new_statuses, chat_id):
    global prev_statuses

    chat_id = str(chat_id)
    if chat_id not in notifications or not notifications[chat_id]["enabled"]:
        return

    if email not in prev_statuses:
        prev_statuses[email] = {}

    notifications_list = []
    for user, is_online in new_statuses.items():
        was_online = prev_statuses[email].get(user, False)
        if not was_online and is_online:
            notifications_list.append(f"🔔 <b>{user}</b> теперь онлайн!")

    prev_statuses[email] = new_statuses
    save_json(STATUS_FILE, prev_statuses)

    if notifications_list:
        await bot.send_message(chat_id, "\n".join(notifications_list), parse_mode="HTML")


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
