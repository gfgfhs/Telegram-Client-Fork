#!/usr/bin/env python3
"""
Telegram Multi-Account Client
Поддержка регистрации, multi-account и бесплатных прокси.
"""

import asyncio
import sys
from pathlib import Path

from config import API_ID, API_HASH, SESSIONS_DIR, USE_FREE_PROXY
from account_manager import AccountManager
from proxy_manager import find_working_proxy, proxy_to_telethon


def check_config():
    if not API_ID or not API_HASH:
        print("\n[!] Ошибка: не указаны API_ID и API_HASH")
        print("    Открой config.py и заполни их.")
        print("    Получить можно на https://my.telegram.org\n")
        sys.exit(1)


def print_header():
    print("\n" + "=" * 55)
    print("  Telegram Multi-Account Client")
    print("  Регистрация + 100+ аккаунтов + бесплатные прокси")
    print("=" * 55)


def print_menu():
    print("\n--- Меню ---")
    print("1. Зарегистрировать / войти по номеру")
    print("2. Войти в существующую сессию")
    print("3. Список всех аккаунтов")
    print("4. Проверить аккаунт")
    print("5. Найти бесплатный прокси заново")
    print("6. Выход")
    print()


async def setup_proxy() -> tuple | None:
    """Ищет бесплатный прокси, если включено в config."""
    if not USE_FREE_PROXY:
        print("[*] Прокси отключены (USE_FREE_PROXY = False)")
        return None

    print("[*] Ищу бесплатный SOCKS5 прокси...")
    proxy_str = await find_working_proxy(max_try=30)
    if proxy_str:
        print(f"[✓] Использую прокси: {proxy_str}")
        return proxy_to_telethon(proxy_str)
    else:
        print("[!] Бесплатный прокси не найден. Продолжаю без прокси.")
        print("    (Часто бесплатные прокси мертвы — это нормально)")
        return None


async def register_flow(manager: AccountManager):
    print("\n=== Регистрация / Вход по номеру ===")
    phone = input("Номер телефона (с +): ").strip()
    if not phone:
        print("[!] Номер не может быть пустым")
        return

    first_name = input("Имя (для нового аккаунта): ").strip() or "User"
    last_name = input("Фамилия (необязательно): ").strip()

    session_name = input("Имя сессии (Enter = номер): ").strip()
    if not session_name:
        session_name = None

    print("\n[*] Начинаю процесс...")
    result = await manager.register_account(
        phone=phone,
        first_name=first_name,
        last_name=last_name,
        session_name=session_name,
    )

    if result["success"]:
        user = result["user"]
        action = result.get("action", "")
        print("\n[✓] Успешно!")
        print(f"    Действие : {action}")
        print(f"    ID       : {user['id']}")
        print(f"    Имя      : {user['first_name']} {user.get('last_name') or ''}")
        print(f"    Телефон  : {user['phone']}")
        print(f"    Username : @{user['username']}" if user.get("username") else "    Username : —")
        print(f"    Сессия   : {result['session']}.session")
    else:
        print(f"\n[✗] Ошибка: {result.get('error')}")


async def login_flow(manager: AccountManager):
    print("\n=== Вход в существующую сессию ===")
    sessions = manager.list_sessions()
    if sessions:
        print("Существующие сессии:")
        for i, s in enumerate(sessions, 1):
            print(f"  {i}. {s}")
        print()

    session_name = input("Имя сессии (или новый номер): ").strip()
    if not session_name:
        print("[!] Имя сессии обязательно")
        return

    result = await manager.login_existing(session_name)

    if result["success"]:
        user = result["user"]
        print("\n[✓] Успешно!")
        print(f"    ID       : {user['id']}")
        print(f"    Имя      : {user['first_name']} {user.get('last_name') or ''}")
        print(f"    Телефон  : {user['phone']}")
        print(f"    Username : @{user['username']}" if user.get("username") else "    Username : —")
    else:
        print(f"\n[✗] Ошибка: {result.get('error')}")


async def list_accounts(manager: AccountManager):
    sessions = manager.list_sessions()
    print("\n=== Список аккаунтов ===")
    if not sessions:
        print("Нет сохранённых сессий.")
        return
    print(f"Найдено сессий: {len(sessions)}\n")
    for i, name in enumerate(sessions, 1):
        print(f"  {i:3}. {name}")


async def check_flow(manager: AccountManager):
    sessions = manager.list_sessions()
    if not sessions:
        print("\n[!] Нет сессий для проверки")
        return

    print("\n=== Проверка аккаунта ===")
    for i, s in enumerate(sessions, 1):
        print(f"  {i}. {s}")

    choice = input("\nНомер или имя сессии: ").strip()
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(sessions):
            session_name = sessions[idx]
        else:
            print("[!] Неверный номер")
            return
    else:
        session_name = choice

    print(f"\n[*] Проверяю {session_name}...")
    result = await manager.check_account(session_name)

    if result["success"]:
        user = result["user"]
        print("\n[✓] Аккаунт активен")
        print(f"    ID       : {user['id']}")
        print(f"    Имя      : {user['first_name']} {user.get('last_name') or ''}")
        print(f"    Телефон  : {user['phone']}")
        print(f"    Username : @{user['username']}" if user.get("username") else "    Username : —")
    else:
        print(f"\n[✗] {result.get('error')}")


async def main():
    check_config()
    Path(SESSIONS_DIR).mkdir(exist_ok=True)

    print_header()

    proxy = await setup_proxy()
    manager = AccountManager(proxy=proxy)

    while True:
        print_menu()
        choice = input("Выбор: ").strip()

        if choice == "1":
            await register_flow(manager)
        elif choice == "2":
            await login_flow(manager)
        elif choice == "3":
            await list_accounts(manager)
        elif choice == "4":
            await check_flow(manager)
        elif choice == "5":
            proxy = await setup_proxy()
            manager = AccountManager(proxy=proxy)
        elif choice == "6":
            print("\nВыход.")
            break
        else:
            print("[!] Неверный выбор")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nПрервано пользователем.")
