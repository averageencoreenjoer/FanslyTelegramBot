# utils/keyboard_utils.py

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Приступить к работе")],
            [KeyboardButton(text="Редактор учетных записей")],
        ],
        resize_keyboard=True
    )

def admin_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Редактор моделей")],
            [KeyboardButton(text="Редактор работников")],
            [KeyboardButton(text="Выйти из админки")],
        ],
        resize_keyboard=True
    )

def worker_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Редактор сессий")],
            [KeyboardButton(text="Общий онлайн")],
            [KeyboardButton(text="Приостановить мониторинг")],
            [KeyboardButton(text="Выйти из аккаунта")],
        ],
        resize_keyboard=True
    )

def models_editor_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Список моделей")],
            [KeyboardButton(text="Добавить модель")],
            [KeyboardButton(text="Удалить модель")],
            [KeyboardButton(text="Управление сессиями")],
            [KeyboardButton(text="Управление автоответчиком")],
            [KeyboardButton(text="🔙 Назад")],
        ],
        resize_keyboard=True
    )

def workers_editor_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Список работников")],
            [KeyboardButton(text="Добавить работника")],
            [KeyboardButton(text="Удалить работника")],
            [KeyboardButton(text="🔙 Назад")],
        ],
        resize_keyboard=True
    )

def sessions_editor_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Список сессий")],
            [KeyboardButton(text="Добавить модель в сессию")],
            [KeyboardButton(text="Удалить модель из сессии")],
            [KeyboardButton(text="Управление уведомлениями")],
            [KeyboardButton(text="🔙 Назад")],
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
