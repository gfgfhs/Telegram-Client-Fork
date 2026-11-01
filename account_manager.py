from pathlib import Path
from telethon import TelegramClient
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneNumberInvalidError,
    PhoneNumberUnoccupiedError,
    FloodWaitError,
    PhoneCodeExpiredError,
)
from telethon.tl.functions.auth import SignUpRequest

from config import API_ID, API_HASH, SESSIONS_DIR, USE_FREE_PROXY


class AccountManager:
    def __init__(self, proxy: tuple | None = None):
        self.sessions_path = Path(SESSIONS_DIR)
        self.sessions_path.mkdir(exist_ok=True)
        self.proxy = proxy  # (socks.SOCKS5, host, port) или None

    def list_sessions(self) -> list[str]:
        return sorted(p.stem for p in self.sessions_path.glob("*.session"))

    def get_client(self, session_name: str) -> TelegramClient:
        session_path = self.sessions_path / session_name
        kwargs = {
            "session": str(session_path),
            "api_id": API_ID,
            "api_hash": API_HASH,
        }
        if self.proxy:
            kwargs["proxy"] = self.proxy
        return TelegramClient(**kwargs)

    async def register_account(
        self,
        phone: str,
        first_name: str,
        last_name: str = "",
        session_name: str | None = None,
    ) -> dict:
        phone = phone.strip().replace(" ", "").replace("-", "")
        if not phone.startswith("+"):
            phone = "+" + phone

        if session_name is None:
            session_name = phone.lstrip("+")

        client = self.get_client(session_name)

        try:
            await client.connect()

            if await client.is_user_authorized():
                me = await client.get_me()
                return {
                    "success": False,
                    "error": f"Сессия уже авторизована как {me.first_name} ({me.phone})",
                    "session": session_name,
                }

            print(f"\n[+] Отправляю код на {phone}...")
            sent = await client.send_code_request(phone)
            phone_code_hash = sent.phone_code_hash

            code = input("[?] Введи код из Telegram/SMS: ").strip()

            try:
                await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
                me = await client.get_me()
                return {
                    "success": True,
                    "action": "login",
                    "user": {
                        "id": me.id,
                        "first_name": me.first_name,
                        "last_name": me.last_name,
                        "phone": me.phone,
                        "username": me.username,
                    },
                    "session": session_name,
                }

            except SessionPasswordNeededError:
                password = input("[?] Введи пароль 2FA: ").strip()
                await client.sign_in(password=password)
                me = await client.get_me()
                return {
                    "success": True,
                    "action": "login_2fa",
                    "user": {
                        "id": me.id,
                        "first_name": me.first_name,
                        "last_name": me.last_name,
                        "phone": me.phone,
                        "username": me.username,
                    },
                    "session": session_name,
                }

            except PhoneNumberUnoccupiedError:
                print("[+] Номер свободен. Регистрирую новый аккаунт...")
                try:
                    await client(SignUpRequest(
                        phone_number=phone,
                        phone_code_hash=phone_code_hash,
                        first_name=first_name,
                        last_name=last_name or "",
                    ))
                    me = await client.get_me()
                    return {
                        "success": True,
                        "action": "register",
                        "user": {
                            "id": me.id,
                            "first_name": me.first_name,
                            "last_name": me.last_name,
                            "phone": me.phone,
                            "username": me.username,
                        },
                        "session": session_name,
                    }
                except Exception as reg_err:
                    return {
                        "success": False,
                        "error": f"Ошибка регистрации: {reg_err}",
                        "session": session_name,
                    }

            except Exception as e:
                error_str = str(e).lower()
                if "unoccupied" in error_str or "sign up" in error_str or "signup" in error_str:
                    print("[+] Пробую зарегистрировать новый аккаунт...")
                    try:
                        await client(SignUpRequest(
                            phone_number=phone,
                            phone_code_hash=phone_code_hash,
                            first_name=first_name,
                            last_name=last_name or "",
                        ))
                        me = await client.get_me()
                        return {
                            "success": True,
                            "action": "register",
                            "user": {
                                "id": me.id,
                                "first_name": me.first_name,
                                "last_name": me.last_name,
                                "phone": me.phone,
                                "username": me.username,
                            },
                            "session": session_name,
                        }
                    except Exception as reg_err:
                        return {
                            "success": False,
                            "error": f"Ошибка регистрации: {reg_err}",
                            "session": session_name,
                        }
                return {
                    "success": False,
                    "error": str(e),
                    "session": session_name,
                }

        except FloodWaitError as e:
            return {
                "success": False,
                "error": f"FloodWait: подожди {e.seconds} секунд",
                "session": session_name,
            }
        except PhoneNumberInvalidError:
            return {"success": False, "error": "Неверный номер телефона", "session": session_name}
        except PhoneCodeInvalidError:
            return {"success": False, "error": "Неверный код", "session": session_name}
        except PhoneCodeExpiredError:
            return {"success": False, "error": "Код истёк. Попробуй снова", "session": session_name}
        except Exception as e:
            return {"success": False, "error": str(e), "session": session_name}
        finally:
            await client.disconnect()

    async def login_existing(self, session_name: str) -> dict:
        client = self.get_client(session_name)
        try:
            await client.connect()
            if await client.is_user_authorized():
                me = await client.get_me()
                return {
                    "success": True,
                    "action": "already_authorized",
                    "user": {
                        "id": me.id,
                        "first_name": me.first_name,
                        "last_name": me.last_name,
                        "phone": me.phone,
                        "username": me.username,
                    },
                    "session": session_name,
                }

            phone = input("[?] Введи номер телефона (+7...): ").strip()
            if not phone.startswith("+"):
                phone = "+" + phone

            print(f"[+] Отправляю код на {phone}...")
            await client.send_code_request(phone)
            code = input("[?] Введи код: ").strip()

            try:
                await client.sign_in(phone, code)
            except SessionPasswordNeededError:
                password = input("[?] Пароль 2FA: ").strip()
                await client.sign_in(password=password)

            me = await client.get_me()
            return {
                "success": True,
                "action": "login",
                "user": {
                    "id": me.id,
                    "first_name": me.first_name,
                    "last_name": me.last_name,
                    "phone": me.phone,
                    "username": me.username,
                },
                "session": session_name,
            }
        except Exception as e:
            return {"success": False, "error": str(e), "session": session_name}
        finally:
            await client.disconnect()

    async def check_account(self, session_name: str) -> dict:
        client = self.get_client(session_name)
        try:
            await client.connect()
            if not await client.is_user_authorized():
                return {"success": False, "error": "Сессия не авторизована", "session": session_name}

            me = await client.get_me()
            return {
                "success": True,
                "user": {
                    "id": me.id,
                    "first_name": me.first_name,
                    "last_name": me.last_name or "",
                    "phone": me.phone,
                    "username": me.username or "",
                },
                "session": session_name,
            }
        except Exception as e:
            return {"success": False, "error": str(e), "session": session_name}
        finally:
            await client.disconnect()
