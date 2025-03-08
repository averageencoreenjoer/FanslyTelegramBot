# handlers/admin_handlers.py

from aiogram import Router, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from utils.keyboard_utils import admin_main_menu, models_editor_menu, workers_editor_menu, back_menu
from utils.file_utils import load_json, save_json
import os

router = Router()

# Данные моделей
ACCOUNTS_FILE = "accounts.json"
accounts = load_json(ACCOUNTS_FILE)

# Состояния пользователей
user_states = {}

# Обработчик кнопки "🔙 Назад" в админке
@router.message(lambda message: message.text == "🔙 Назад")
async def go_back_in_admin(message: types.Message):
    user_id = message.from_user.id

    if user_id not in user_states:
        await message.answer("Вы уже в главном меню.", reply_markup=admin_main_menu())
        return

    stage = user_states[user_id].get("stage")

    if stage == "adding_model":
        # Если пользователь добавлял модель, возвращаем его в меню редактора моделей
        await message.answer("Возвращаемся в редактор моделей.", reply_markup=models_editor_menu())
        user_states[user_id]["stage"] = None  # Сбрасываем состояние
    elif stage == "deleting_model":
        # Если пользователь удалял модель, возвращаем его в меню редактора моделей
        await message.answer("Возвращаемся в редактор моделей.", reply_markup=models_editor_menu())
        user_states[user_id]["stage"] = None  # Сбрасываем состояние
    else:
        # Если состояние неизвестно, возвращаем в главное меню админки
        await message.answer("Возвращаемся в главное меню админки.", reply_markup=admin_main_menu())
        user_states.pop(user_id, None)  # Сбрасываем состояние

# Обработчик выбора "Редактор моделей"
@router.message(lambda message: message.text == "Редактор моделей")
async def models_editor(message: types.Message):
    await message.answer("Выберите действие:", reply_markup=models_editor_menu())

# Обработчик выбора "Добавить модель"
@router.message(lambda message: message.text == "Добавить модель")
async def add_model(message: types.Message):
    user_id = message.from_user.id
    user_states[user_id] = {"stage": "adding_model"}
    await message.answer("Введите email модели:", reply_markup=back_menu())

# Обработчик ввода email модели
@router.message(lambda message: message.from_user.id in user_states and user_states[message.from_user.id]["stage"] == "adding_model" and "email" not in user_states[message.from_user.id])
async def get_model_email(message: types.Message):
    email = message.text.strip()
    user_states[message.from_user.id]["email"] = email
    user_states[message.from_user.id]["stage"] = "adding_model_password"
    await message.answer("Введите пароль модели:", reply_markup=back_menu())

# Обработчик ввода пароля модели
@router.message(lambda message: message.from_user.id in user_states and user_states[message.from_user.id]["stage"] == "adding_model_password")
async def get_model_password(message: types.Message):
    password = message.text.strip()
    user_states[message.from_user.id]["password"] = password
    user_states[message.from_user.id]["stage"] = "adding_model_username"
    await message.answer("Введите ник модели:", reply_markup=back_menu())

# Обработчик ввода ника модели
@router.message(lambda message: message.from_user.id in user_states and user_states[message.from_user.id]["stage"] == "adding_model_username")
async def get_model_username(message: types.Message):
    username = message.text.strip()
    email = user_states[message.from_user.id]["email"]
    password = user_states[message.from_user.id]["password"]

    accounts[email] = {
        "email": email,
        "password": password,
        "username": username
    }
    save_json(ACCOUNTS_FILE, accounts)

    await message.answer(f"✅ Модель **{username}** успешно добавлена!", reply_markup=models_editor_menu())
    user_states.pop(message.from_user.id, None)  # Сбрасываем состояние


@router.message(lambda message: message.text == "Список моделей")
async def show_models_list(message: types.Message):
    if not accounts:
        await message.answer("Список моделей пуст.")
        return

    models_list = "\n".join([f"🔹 {acc['username']} ({email})" for email, acc in accounts.items()])
    await message.answer(f"📜 Список моделей:\n{models_list}")


@router.message(lambda message: message.text == "Редактор работников")
async def workers_editor(message: types.Message):
    await message.answer("Выберите действие:", reply_markup=workers_editor_menu())


# Обработчик выбора "Удалить модель"
@router.message(lambda message: message.text == "Удалить модель")
async def delete_model(message: types.Message):
    if not accounts:
        await message.answer("Список моделей пуст.", reply_markup=models_editor_menu())
        return

    user_id = message.from_user.id
    user_states[user_id] = {"stage": "deleting_model"}
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=acc["username"])] for acc in accounts.values()] + [
            [KeyboardButton(text="🔙 Назад")],
        ],
        resize_keyboard=True
    )
    await message.answer("Выберите модель для удаления:", reply_markup=kb)

# Обработчик подтверждения удаления модели
@router.message(lambda message: message.from_user.id in user_states and user_states[message.from_user.id]["stage"] == "deleting_model")
async def confirm_delete_model(message: types.Message):
    selected_username = message.text
    email = next(email for email, acc in accounts.items() if acc["username"] == selected_username)

    del accounts[email]
    save_json(ACCOUNTS_FILE, accounts)

    account_folder = os.path.join("data", email)
    if os.path.exists(account_folder):
        import shutil
        shutil.rmtree(account_folder)

    await message.answer(f"✅ Модель **{selected_username}** успешно удалена!", reply_markup=models_editor_menu())
    user_states.pop(message.from_user.id, None)  # Сбрасываем состояние


@router.message(lambda message: message.text == "Редактор работников")
async def workers_editor(message: types.Message):
    await message.answer("Выберите действие:", reply_markup=workers_editor_menu())


@router.message(lambda message: message.text == "Добавить работника")
async def add_worker(message: types.Message):
    user_id = message.from_user.id
    user_states[user_id] = {"stage": "adding_worker"}
    await message.answer("Введите логин работника:", reply_markup=back_menu())

@router.message(lambda message: message.from_user.id in user_states and user_states[message.from_user.id]["stage"] == "adding_worker")
async def get_worker_login(message: types.Message):
    user_id = message.from_user.id
    user_states[user_id]["worker_login"] = message.text
    user_states[user_id]["stage"] = "adding_worker_password"
    await message.answer("Введите пароль работника:", reply_markup=back_menu())

@router.message(lambda message: message.from_user.id in user_states and user_states[message.from_user.id]["stage"] == "adding_worker_password")
async def get_worker_password(message: types.Message):
    user_id = message.from_user.id
    worker_login = user_states[user_id]["worker_login"]
    worker_password = message.text

    workers = load_json("workers.json")
    workers[worker_login] = {
        "password": worker_password,
        "role": "worker"
    }
    save_json("workers.json", workers)

    await message.answer(f"✅ Работник **{worker_login}** успешно добавлен!", reply_markup=workers_editor_menu())
    user_states.pop(user_id, None)


@router.message(lambda message: message.text == "Удалить работника")
async def delete_worker(message: types.Message):
    workers = load_json("workers.json")
    if not workers:
        await message.answer("Список работников пуст.", reply_markup=workers_editor_menu())
        return

    user_id = message.from_user.id
    user_states[user_id] = {"stage": "deleting_worker"}
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=login)] for login in workers.keys()] + [
            [KeyboardButton(text="🔙 Назад")],
        ],
        resize_keyboard=True
    )
    await message.answer("Выберите работника для удаления:", reply_markup=kb)


@router.message(lambda message: message.from_user.id in user_states and user_states[message.from_user.id]["stage"] == "deleting_worker")
async def confirm_delete_worker(message: types.Message):
    selected_login = message.text
    workers = load_json("workers.json")

    if selected_login in workers:
        del workers[selected_login]
        save_json("workers.json", workers)
        await message.answer(f"✅ Работник **{selected_login}** успешно удален!", reply_markup=workers_editor_menu())
    else:
        await message.answer("❌ Работник не найден.", reply_markup=workers_editor_menu())

    user_states.pop(message.from_user.id, None)


@router.message(lambda message: message.text == "Список работников")
async def show_workers_list(message: types.Message):
    workers = load_json("workers.json")
    if not workers:
        await message.answer("Список работников пуст.")
        return

    workers_list = "\n".join([f"🔹 {login} (Роль: {data['role']})" for login, data in workers.items()])
    await message.answer(f"📜 Список работников:\n{workers_list}")


@router.message(lambda message: message.text == "Выйти из админки")
async def logout_from_admin(message: types.Message):
    user_id = message.from_user.id

    # Сбрасываем состояние пользователя
    user_states.pop(user_id, None)

    # Возвращаем пользователя на этап ввода логина
    user_states[user_id] = {"stage": "waiting_for_login"}
    await message.answer("Вы вышли из админки. Введите логин:", reply_markup=types.ReplyKeyboardRemove())