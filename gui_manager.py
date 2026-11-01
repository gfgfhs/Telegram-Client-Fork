#!/usr/bin/env python3
"""
GUI менеджер профилей Telegram Desktop
Быстрая смена аккаунтов через разные workdir (tdata).
Интерфейс остаётся полностью оригинальным.
"""

import os
import sys
import json
import subprocess
import shutil
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog

# ================== НАСТРОЙКИ ==================
# Папка, где будут храниться все профили
PROFILES_ROOT = Path(__file__).parent / "tg_profiles"

# Имя конфига
CONFIG_FILE = Path(__file__).parent / "gui_config.json"

# Возможные пути к Telegram Desktop (Windows)
DEFAULT_TG_PATHS = [
    Path(os.environ.get("APPDATA", "")) / "Telegram Desktop" / "Telegram.exe",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Telegram Desktop" / "Telegram.exe",
    Path("C:/") / "Users" / os.environ.get("USERNAME", "") / "AppData" / "Roaming" / "Telegram Desktop" / "Telegram.exe",
    Path("C:/") / "Program Files" / "Telegram Desktop" / "Telegram.exe",
    Path("C:/") / "Program Files (x86)" / "Telegram Desktop" / "Telegram.exe",
]


def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"telegram_path": "", "last_profile": ""}


def save_config(cfg: dict):
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def find_telegram() -> str | None:
    cfg = load_config()
    if cfg.get("telegram_path") and Path(cfg["telegram_path"]).exists():
        return cfg["telegram_path"]

    for p in DEFAULT_TG_PATHS:
        if p.exists():
            return str(p)
    return None


class ProfileManagerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Telegram Multi-Profile Manager")
        self.root.geometry("520x480")
        self.root.minsize(420, 380)

        self.cfg = load_config()
        self.tg_path = find_telegram()

        PROFILES_ROOT.mkdir(exist_ok=True)

        self._build_ui()
        self.refresh_list()

    def _build_ui(self):
        # Верхняя панель — путь к Telegram
        top = ttk.Frame(self.root, padding=8)
        top.pack(fill="x")

        ttk.Label(top, text="Telegram.exe:").pack(side="left")
        self.path_var = tk.StringVar(value=self.tg_path or "не найден")
        path_entry = ttk.Entry(top, textvariable=self.path_var, width=45)
        path_entry.pack(side="left", padx=5, fill="x", expand=True)
        ttk.Button(top, text="Обзор...", command=self.browse_telegram).pack(side="left")

        # Список профилей
        mid = ttk.Frame(self.root, padding=8)
        mid.pack(fill="both", expand=True)

        ttk.Label(mid, text="Профили (каждый = отдельный аккаунт):").pack(anchor="w")

        list_frame = ttk.Frame(mid)
        list_frame.pack(fill="both", expand=True, pady=4)

        self.listbox = tk.Listbox(list_frame, font=("Segoe UI", 11), activestyle="dotbox")
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scrollbar.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.listbox.bind("<Double-Button-1>", lambda e: self.launch_selected())

        # Кнопки
        btn_frame = ttk.Frame(self.root, padding=8)
        btn_frame.pack(fill="x")

        ttk.Button(btn_frame, text="▶ Запустить", command=self.launch_selected).pack(side="left", padx=3)
        ttk.Button(btn_frame, text="+ Новый профиль", command=self.create_profile).pack(side="left", padx=3)
        ttk.Button(btn_frame, text="Переименовать", command=self.rename_profile).pack(side="left", padx=3)
        ttk.Button(btn_frame, text="Удалить", command=self.delete_profile).pack(side="left", padx=3)
        ttk.Button(btn_frame, text="Обновить", command=self.refresh_list).pack(side="right", padx=3)

        # Подсказка
        hint = ttk.Label(
            self.root,
            text="Двойной клик = запуск. Каждый профиль — отдельная папка tdata.\n"
                 "Регистрацию новых номеров удобнее делать через python main.py",
            foreground="#555",
            justify="center",
        )
        hint.pack(pady=6)

    def browse_telegram(self):
        path = filedialog.askopenfilename(
            title="Выбери Telegram.exe",
            filetypes=[("Telegram", "Telegram.exe"), ("Все файлы", "*.*")],
        )
        if path:
            self.tg_path = path
            self.path_var.set(path)
            self.cfg["telegram_path"] = path
            save_config(self.cfg)

    def get_profiles(self) -> list[str]:
        if not PROFILES_ROOT.exists():
            return []
        return sorted(
            [d.name for d in PROFILES_ROOT.iterdir() if d.is_dir()],
            key=str.lower,
        )

    def refresh_list(self):
        self.listbox.delete(0, tk.END)
        profiles = self.get_profiles()
        for name in profiles:
            self.listbox.insert(tk.END, name)

        # Подсветка последнего
        last = self.cfg.get("last_profile")
        if last and last in profiles:
            idx = profiles.index(last)
            self.listbox.selection_set(idx)
            self.listbox.see(idx)

    def selected_profile(self) -> str | None:
        sel = self.listbox.curselection()
        if not sel:
            return None
        return self.listbox.get(sel[0])

    def create_profile(self):
        name = simpledialog.askstring("Новый профиль", "Имя профиля (латиница/цифры):")
        if not name:
            return
        name = name.strip().replace(" ", "_")
        if not name:
            return

        path = PROFILES_ROOT / name
        if path.exists():
            messagebox.showerror("Ошибка", f"Профиль «{name}» уже существует")
            return

        path.mkdir(parents=True)
        self.refresh_list()
        messagebox.showinfo(
            "Готово",
            f"Профиль «{name}» создан.\n\n"
            f"Запусти его и войди / зарегистрируй аккаунт.\n"
            f"Данные сохранятся в:\n{path}",
        )

    def rename_profile(self):
        old = self.selected_profile()
        if not old:
            messagebox.showwarning("", "Сначала выбери профиль")
            return

        new = simpledialog.askstring("Переименовать", "Новое имя:", initialvalue=old)
        if not new or new.strip() == old:
            return
        new = new.strip().replace(" ", "_")

        old_path = PROFILES_ROOT / old
        new_path = PROFILES_ROOT / new
        if new_path.exists():
            messagebox.showerror("Ошибка", "Такое имя уже занято")
            return

        old_path.rename(new_path)
        if self.cfg.get("last_profile") == old:
            self.cfg["last_profile"] = new
            save_config(self.cfg)
        self.refresh_list()

    def delete_profile(self):
        name = self.selected_profile()
        if not name:
            messagebox.showwarning("", "Сначала выбери профиль")
            return

        if not messagebox.askyesno(
            "Удалить?",
            f"Удалить профиль «{name}» и все его данные?\nЭто необратимо.",
        ):
            return

        path = PROFILES_ROOT / name
        shutil.rmtree(path, ignore_errors=True)
        if self.cfg.get("last_profile") == name:
            self.cfg["last_profile"] = ""
            save_config(self.cfg)
        self.refresh_list()

    def launch_selected(self):
        name = self.selected_profile()
        if not name:
            messagebox.showwarning("", "Выбери профиль")
            return

        tg = self.path_var.get().strip()
        if not tg or not Path(tg).exists():
            messagebox.showerror(
                "Telegram не найден",
                "Укажи путь к Telegram.exe кнопкой «Обзор...»",
            )
            return

        workdir = PROFILES_ROOT / name
        workdir.mkdir(exist_ok=True)

        # Запускаем Telegram с отдельной папкой данных
        try:
            subprocess.Popen(
                [tg, "-workdir", str(workdir)],
                cwd=str(Path(tg).parent),
            )
            self.cfg["last_profile"] = name
            self.cfg["telegram_path"] = tg
            save_config(self.cfg)
        except Exception as e:
            messagebox.showerror("Ошибка запуска", str(e))


def main():
    root = tk.Tk()
    # Более-менее современный вид на Windows
    try:
        root.call("source", "sun-valley.tcl")  # если есть тема
    except Exception:
        pass
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    app = ProfileManagerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
