import json
import os
import logging

logging.basicConfig(level=logging.INFO)

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

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)