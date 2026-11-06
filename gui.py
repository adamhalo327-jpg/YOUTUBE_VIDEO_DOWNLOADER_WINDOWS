"""YouTube Video Downloader 3.0 PRO EDITION (Windows desktop).
Use only with recordings you own or have permission to download.
"""
from __future__ import annotations

import io
import json
import os
import queue
import subprocess
import sys
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, fields
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image, ImageOps

from core import (
    APP_TITLE, APP_VERSION, History, KINDS, PREMIUM_KINDS, PREMIUM_SPEEDS,
    QUALITY_OPTIONS, SPEED_PROFILES, fetch_thumbnail, is_playlist_url, load_json,
    make_download_command as _make_download_command, metadata_command, normalize_trim_range,
    parse_progress, parse_urls, save_json, tool, update_engine, user_data_dir,
    valid_youtube_url, valid_video_url, yt_base_command as _yt_base_command,
)
from licensing import LicenseManager

# Public compatibility with 1.0 tests / 2.0 integrations.
def yt_base_command():
    return _yt_base_command()


def make_download_command(url, dest, kind, quality, **kwargs):
    return _make_download_command(url, dest, kind, quality,
                                  _tool=tool, _base_command=yt_base_command, **kwargs)


PALETTES = {
    "Ciemny": {"bg": "#090E1B", "panel": "#121B2D", "panel2": "#19253C", "border": "#293951",
               "text": "#EAF3FF", "muted": "#9DACCA", "accent": "#23D3C5", "hover": "#17A89D", "error": "#F47A86"},
    "Jasny": {"bg": "#EDF3F9", "panel": "#FFFFFF", "panel2": "#E3EDF6", "border": "#B5C5D6",
              "text": "#14253B", "muted": "#53657D", "accent": "#116AA5", "hover": "#0D5687", "error": "#C42B49"},
    "Neonowy": {"bg": "#0B0717", "panel": "#1B1030", "panel2": "#291B48", "border": "#6937AD",
                "text": "#F4EFFF", "muted": "#BDA9E3", "accent": "#B54AFF", "hover": "#8D27D8", "error": "#FF6C9E"},
}
FONT = "Segoe UI"
ctk.set_default_color_theme("blue")


@dataclass
class DownloadTask:
    id: str
    url: str
    folder: Path
    kind: str
    quality: str
    playlist: bool
    subtitles: bool
    languages: str
    fragments: int
    trim_start: str = ""
    trim_end: str = ""
    title: str = "W kolejce..."
    status: str = "W kolejce"
    percent: float = 0.0
    speed: str = ""
    eta: str = ""
    files: int = 0
    pause_requested: bool = False
    cancelled: bool = False
    started: bool = False
    process: subprocess.Popen | None = field(default=None, repr=False, compare=False)

    def persist(self) -> dict:
        data = {k: getattr(self, k) for k in (
            "id", "url", "folder", "kind", "quality", "playlist", "subtitles",
            "languages", "fragments", "trim_start", "trim_end", "title", "status")}
        data["folder"] = str(data["folder"])
        return data

    @classmethod
    def restore(cls, saved: dict) -> "DownloadTask":
        allowed = {f.name for f in fields(cls) if f.init and f.name not in {"process"}}
        args = {k: v for k, v in saved.items() if k in allowed}
        args["folder"] = Path(args["folder"])
        task = cls(**args)
        if task.status in {"Pobieranie", "W kolejce"}:
            task.status = "Wstrzymano"  # explicit resume after program restart
        task.percent = 0.0
        return task


class UltraDownloader(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_TITLE} {APP_VERSION}")
        self.geometry("1200x930")
        self.minsize(990, 760)
        self.home = user_data_dir()
        self.home.mkdir(parents=True, exist_ok=True)
        self.history = History()
        self.license = LicenseManager()
        self.settings_file = self.home / "settings.json"
        self.queue_file = self.home / "queue-v3.json"
        s = load_json(self.settings_file, {})
        if not isinstance(s, dict):
            s = {}
        folder = Path.home() / "Downloads"
        self.folder_var = ctk.StringVar(value=str(s.get("folder", folder if folder.is_dir() else Path.home())))
        self.kind_var = ctk.StringVar(value=s.get("kind", "MP4 (wideo)"))
        self.quality_var = ctk.StringVar(value=s.get("quality", QUALITY_OPTIONS[0]))
        self.speed_var = ctk.StringVar(value=s.get("speed", "Szybki"))
        self.parallel_var = ctk.StringVar(value=str(s.get("parallel", "3")))
        self.playlist_var = ctk.BooleanVar(value=bool(s.get("playlist", True)))
        self.subs_var = ctk.BooleanVar(value=bool(s.get("subtitles", False)))
        self.languages_var = ctk.StringVar(value=s.get("languages", "pl,en"))
        self.auto_update_var = ctk.BooleanVar(value=bool(s.get("auto_update", True)))
        self.notify_var = ctk.BooleanVar(value=bool(s.get("notify", False)))
        self.trim_start_var = ctk.StringVar(value=s.get("trim_start", ""))
        self.trim_end_var = ctk.StringVar(value=s.get("trim_end", ""))
        self.theme_var = ctk.StringVar(value=s.get("theme", "Ciemny") if s.get("theme") in PALETTES else "Ciemny")
        self.events: queue.Queue[tuple] = queue.Queue()
        self.pool = ThreadPoolExecutor(max_workers=5, thread_name_prefix="yvd")
        self.tasks: dict[str, DownloadTask] = {}
        self.order: list[str] = []
        self.task_views: dict[str, dict] = {}
        self.active_count = 0
        self.max_parallel = max(1, min(5 if self.license.premium() else 3, int(self.parallel_var.get()) if self.parallel_var.get() in {"1","2","3","4","5"} else 3))
        self.preview_image = None
        self.preview_request = 0
        self.engine_update_in_progress = False
        self.closing = False
        self.history_render_pending = False
        self._set_palette(self.theme_var.get())
        self._build_ui()
        self._restore_queue()
        self._settings_changed()
        self._render_history()
        self._refresh_stats()
        self.after(100, self._drain_events)
        self.after(400, self._scheduler)
        if self.auto_update_var.get() and sys.platform == "win32":
            self.after(3000, lambda: self._update_engine(force=False))
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _set_palette(self, theme):
        p = PALETTES[theme]
        self.bg, self.panel, self.panel2, self.border = (p[k] for k in ("bg", "panel", "panel2", "border"))
        self.text, self.muted, self.accent, self.hover, self.error = (p[k] for k in ("text", "muted", "accent", "hover", "error"))
        ctk.set_appearance_mode("light" if theme == "Jasny" else "dark")
        self.configure(fg_color=self.bg)

    def _text(self, parent, value, size=13, color=None, bold=False, **kwargs):
        return ctk.CTkLabel(parent, text=value, text_color=color or self.text,
                            font=(FONT, size, "bold" if bold else "normal"), **kwargs)

    def _button(self, parent, value, cmd, *, secondary=False, width=120, height=34):
        return ctk.CTkButton(parent, text=value, command=cmd, width=width, height=height,
                             corner_radius=9, font=(FONT, 12, "bold"),
                             fg_color=self.panel2 if secondary else self.accent,
                             hover_color=self.border if secondary else self.hover,
                             text_color=self.text if secondary else ("#FFFFFF" if self.theme_var.get()=="Jasny" else self.bg))

    def _entry(self, parent, var, width=150, *, placeholder=None):
        return ctk.CTkEntry(parent, textvariable=var, width=width, height=36, corner_radius=8,
                            fg_color=self.bg, border_color=self.border, text_color=self.text,
                            placeholder_text=placeholder)

    def _choice(self, parent, var, choices, cb=None, width=160):
        return ctk.CTkOptionMenu(parent, variable=var, values=list(choices), width=width, height=36,
                                 fg_color=self.panel2, button_color=self.border, button_hover_color=self.hover,
                                 text_color=self.text, command=cb)

    def _check(self, parent, text, var, callback=None):
        return ctk.CTkCheckBox(parent, text=text, variable=var, command=callback,
                               fg_color=self.accent, hover_color=self.hover, text_color=self.text)

    def _build_ui(self):
        head = ctk.CTkFrame(self, fg_color=self.bg)
        head.pack(fill="x", padx=20, pady=(15, 5))
        self._text(head, "▶  YOUTUBE VIDEO DOWNLOADER", 22, bold=True).pack(side="left")
        self._text(head, "PRO EDITION 3.0", 13, self.accent, bold=True).pack(side="right", padx=8)
        self._text(self, "Playlisty  •  MP4 / MP3  •  Napisy  •  Turbo Pro  •  Kolejka  •  Konwersja  •  Premium", 12, self.muted).pack(anchor="w", padx=25)
        self.tabs = ctk.CTkTabview(self, fg_color=self.bg, segmented_button_fg_color=self.panel,
                                  segmented_button_selected_color=self.hover,
                                  segmented_button_unselected_color=self.panel2)
        self.tabs.pack(fill="both", expand=True, padx=16, pady=(7, 7))
        for tab in ("Pobieranie", "Historia", "Ustawienia", "Premium"):
            self.tabs.add(tab)
        self._download_tab(self.tabs.tab("Pobieranie"))
        self._history_tab(self.tabs.tab("Historia"))
        self._settings_tab(self.tabs.tab("Ustawienia"))
        self._premium_tab(self.tabs.tab("Premium"))
        foot = ctk.CTkFrame(self, fg_color=self.bg)
        foot.pack(fill="x", padx=25, pady=(0, 10))
        self.footer_status = self._text(foot, "Gotowe do pobierania.", 11, self.muted)
        self.footer_status.pack(side="left")
        self.counter = self._text(foot, "", 11, self.accent)
        self.counter.pack(side="right")

    def _download_tab(self, root):
        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(1, weight=1)
        form = ctk.CTkFrame(root, fg_color=self.panel, corner_radius=13)
        form.grid(row=0, column=0, sticky="ew", pady=(2, 8))
        form.grid_columnconfigure(0, weight=1)
        urlrow = ctk.CTkFrame(form, fg_color="transparent")
        urlrow.grid(row=0, column=0, sticky="ew", padx=13, pady=(9, 4))
        urlrow.grid_columnconfigure(0, weight=1)
        self._text(urlrow, "LINK YOUTUBE / PLAYLISTA — jeden adres w linii", 11, self.muted, bold=True).grid(row=0, column=0, sticky="w")
        self.urlbox = ctk.CTkTextbox(urlrow, height=54, fg_color=self.bg, border_color=self.border,
                                     border_width=1, corner_radius=9, text_color=self.text)
        self.urlbox.grid(row=1, column=0, sticky="ew", padx=(0, 8))
        right = ctk.CTkFrame(urlrow, fg_color="transparent")
        right.grid(row=1, column=1, sticky="n")
        self._button(right, "Wklej", self._paste, secondary=True, width=100, height=29).pack(pady=(0, 4))
        self._button(right, "Podgląd", self._preview, secondary=True, width=100, height=29).pack()
        preview = ctk.CTkFrame(form, fg_color=self.bg, corner_radius=9)
        preview.grid(row=1, column=0, sticky="ew", padx=13, pady=3)
        preview.grid_columnconfigure(1, weight=1)
        self.thumb = self._text(preview, "▶", 28, self.accent, bold=True, width=132, height=75,
                                 fg_color=self.panel2, corner_radius=9)
        self.thumb.grid(row=0, column=0, padx=7, pady=7)
        self.preview_title = self._text(preview, "Tutaj pojawi się miniatura i tytuł filmu.", 12,
                                        wraplength=760, anchor="w", justify="left")
        self.preview_title.grid(row=0, column=1, sticky="ew", padx=(5, 10))
        options = ctk.CTkFrame(form, fg_color="transparent")
        options.grid(row=2, column=0, sticky="ew", padx=13, pady=(5, 3))
        for i, name in enumerate(("FORMAT", "JAKOŚĆ", "TRYB POBIERANIA", "FILMY RÓWNOLEGLE")):
            options.grid_columnconfigure(i, weight=1)
            self._text(options, name, 10, self.muted, bold=True).grid(row=0, column=i, sticky="w")
        self._choice(options, self.kind_var, KINDS, lambda _: self._settings_changed()).grid(row=1, column=0, sticky="ew", padx=(0, 7), pady=3)
        self.quality_menu = self._choice(options, self.quality_var, QUALITY_OPTIONS, lambda _: self._settings_changed())
        self.quality_menu.grid(row=1, column=1, sticky="ew", padx=(0, 7), pady=3)
        self._choice(options, self.speed_var, SPEED_PROFILES, lambda _: self._settings_changed()).grid(row=1, column=2, sticky="ew", padx=(0, 7), pady=3)
        self._choice(options, self.parallel_var, ("1", "2", "3", "4", "5"), self._parallel_changed).grid(row=1, column=3, sticky="ew", pady=3)
        flags = ctk.CTkFrame(form, fg_color="transparent")
        flags.grid(row=3, column=0, sticky="ew", padx=13, pady=4)
        self._check(flags, "Cała playlista", self.playlist_var, self._settings_changed).pack(side="left", padx=(0, 20))
        self._check(flags, "Pobierz napisy", self.subs_var, self._settings_changed).pack(side="left", padx=(0, 12))
        self._text(flags, "Języki:", 11, self.muted).pack(side="left")
        self._entry(flags, self.languages_var, 90).pack(side="left", padx=6)
        trims = ctk.CTkFrame(form, fg_color="transparent")
        trims.grid(row=4, column=0, sticky="ew", padx=13, pady=4)
        self._text(trims, "✂  PRZYCIĄĆ (PREMIUM)", 11, self.accent, bold=True).pack(side="left", padx=(0, 10))
        self._text(trims, "Od:", 11, self.muted).pack(side="left")
        self._entry(trims, self.trim_start_var, 110, placeholder="00:01:20").pack(side="left", padx=6)
        self._text(trims, "Do:", 11, self.muted).pack(side="left")
        self._entry(trims, self.trim_end_var, 110, placeholder="00:02:50").pack(side="left", padx=6)
        self._text(trims, "Puste pola = cały film", 11, self.muted).pack(side="left", padx=8)
        bottom = ctk.CTkFrame(form, fg_color="transparent")
        bottom.grid(row=5, column=0, sticky="ew", padx=13, pady=(5, 11))
        bottom.grid_columnconfigure(0, weight=1)
        self._entry(bottom, self.folder_var).grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self._button(bottom, "Folder…", self._choose_folder, secondary=True, width=92).grid(row=0, column=1, padx=(0, 5))
        self._button(bottom, "＋  DODAJ DO KOLEJKI", self._queue_downloads, width=210).grid(row=0, column=2)
        area = ctk.CTkFrame(root, fg_color=self.panel, corner_radius=12)
        area.grid(row=1, column=0, sticky="nsew")
        bar = ctk.CTkFrame(area, fg_color="transparent")
        bar.pack(fill="x", padx=12, pady=(7, 3))
        self._text(bar, "KOLEJKA — ↑ ↓ zmieniają kolejność; Pauza zachowuje .part", 12, bold=True).pack(side="left")
        self._button(bar, "Otwórz folder", self._open_folder, secondary=True, width=115, height=28).pack(side="right")
        self.queue_scroll = ctk.CTkScrollableFrame(area, fg_color="transparent")
        self.queue_scroll.pack(fill="both", expand=True, padx=5, pady=4)
        self.empty_label = self._text(self.queue_scroll, "Kolejka jest pusta.", 12, self.muted)
        self.empty_label.pack(pady=25)

    def _history_tab(self, root):
        frame = ctk.CTkFrame(root, fg_color=self.panel, corner_radius=12)
        frame.pack(fill="x", pady=4)
        self._text(frame, "HISTORIA POBRAŃ", 15, bold=True).pack(side="left", padx=12, pady=12)
        self.history_query = ctk.StringVar()
        search = self._entry(frame, self.history_query, 270, placeholder="Szukaj tytułu, linku lub pliku...")
        search.pack(side="left", padx=12)
        search.bind("<KeyRelease>", lambda _: self._render_history())
        self._button(frame, "Wyczyść", self._clear_history, secondary=True, width=97, height=30).pack(side="right", padx=10)
        self._button(frame, "Odśwież", self._render_history, secondary=True, width=90, height=30).pack(side="right")
        self.history_scroll = ctk.CTkScrollableFrame(root, fg_color=self.panel, corner_radius=12)
        self.history_scroll.pack(fill="both", expand=True)

    def _settings_tab(self, root):
        frame = ctk.CTkScrollableFrame(root, fg_color=self.panel, corner_radius=12)
        frame.pack(fill="both", expand=True, pady=4)
        self._text(frame, "USTAWIENIA PROGRAMU", 19, bold=True).pack(anchor="w", padx=18, pady=(18, 9))
        theme = ctk.CTkFrame(frame, fg_color="transparent")
        theme.pack(fill="x", padx=18, pady=8)
        self._text(theme, "Motyw:", 13).pack(side="left", padx=(0, 12))
        self._choice(theme, self.theme_var, PALETTES.keys(), self._change_theme, width=180).pack(side="left")
        self._check(frame, "Powiadomienia Windows po zakończeniu (PREMIUM)", self.notify_var, self._notify_changed).pack(anchor="w", padx=20, pady=12)
        self._check(frame, "Automatyczne aktualizacje yt-dlp (co 24 godziny)", self.auto_update_var, self._settings_changed).pack(anchor="w", padx=20, pady=10)
        engine = ctk.CTkFrame(frame, fg_color="transparent")
        engine.pack(fill="x", padx=18, pady=10)
        self._button(engine, "Sprawdź aktualizację yt-dlp", self._update_engine, width=240).pack(side="left", padx=(0, 12))
        self.engine_status = self._text(engine, "Aktualizacja silnika z oficjalnego wydania yt-dlp, weryfikacja SHA256.", 11,
                                        self.muted, wraplength=440, justify="left")
        self.engine_status.pack(side="left")
        self._text(frame, "TURBO PRO — PREMIUM", 16, self.accent, bold=True).pack(anchor="w", padx=20, pady=(23, 10))
        self._text(frame, "Standard 4 / Szybki 8 / Turbo 12 / Turbo Pro 16 lub 24 fragmenty równocześnie.\n"
                         "Darmowa wersja: 1–3 filmy naraz. Premium: do 5 filmów naraz.\n"
                         "Przyspieszenie zależy od źródła i łącza — więcej wątków nie zawsze pomaga.",
                   12, self.muted, wraplength=820, justify="left").pack(anchor="w", padx=20)
        self._text(frame, "Pauza zachowuje częściowe pliki .part, gdy format i serwer umożliwiają wznowienie.\n"
                         "Przycinanie i niektóre konwersje używają FFmpeg — mogą potrwać dłużej niż pobranie.\n"
                         "Pobieraj wyłącznie własne lub dozwolone materiały. Bez obchodzenia DRM.",
                   12, self.muted, wraplength=820, justify="left").pack(anchor="w", padx=20, pady=(20, 25))

    def _premium_tab(self, root):
        frame = ctk.CTkFrame(root, fg_color=self.panel, corner_radius=13)
        frame.pack(fill="x", padx=8, pady=8)
        self._text(frame, "💎  PREMIUM — AKTYWACJA SPECJALNYM KODEM", 21, bold=True).pack(anchor="w", padx=21, pady=(23, 7))
        self.premium_info = self._text(frame, "", 13, self.accent, anchor="w")
        self.premium_info.pack(fill="x", padx=21, pady=10)
        self._text(frame, "Odblokowuje: Turbo Pro 16/24, 4–5 równoległych zadań, przycinanie,\n"
                          "MKV / WEBM / WAV oraz powiadomienia Windows.", 12, self.muted,
                   justify="left").pack(anchor="w", padx=21, pady=(0, 14))
        self.license_box = ctk.CTkTextbox(frame, height=100, fg_color=self.bg, text_color=self.text,
                                          border_width=1, border_color=self.border, corner_radius=9)
        self.license_box.pack(fill="x", padx=21)
        buttons = ctk.CTkFrame(frame, fg_color="transparent")
        buttons.pack(fill="x", padx=21, pady=15)
        self._button(buttons, "AKTYWUJ PREMIUM", self._activate_license, width=200).pack(side="left")
        self._button(buttons, "Dezaktywuj na tym komputerze", self._deactivate_license, secondary=True, width=245).pack(side="left", padx=9)
        self._text(frame, "Wklej otrzymany kod YVD3-...; licencja jest weryfikowana lokalnie podpisem cyfrowym.\n"
                          "Nie udostępniaj klucza prywatnego właściciela aplikacji.",
                   11, self.muted, justify="left").pack(anchor="w", padx=21, pady=(0, 25))
        self._refresh_premium_ui()

    def _refresh_premium_ui(self):
        data = self.license.info()
        if data:
            exp = data.get("expires") or "bezterminowa"
            self.premium_info.configure(text=f"✅ PREMIUM AKTYWNE  •  {data.get('owner', 'Użytkownik')}  •  ważna do: {exp}", text_color=self.accent)
        else:
            self.premium_info.configure(text="🔒 WERSJA DARMOWA — wpisz kod, aby aktywować Premium.", text_color=self.muted)

    def _activate_license(self):
        code = self.license_box.get("1.0", "end").strip()
        try:
            self.license.activate(code)
        except (ValueError, OSError) as exc:
            messagebox.showerror("Kod Premium", str(exc))
            return
        self.license_box.delete("1.0", "end")
        self._refresh_premium_ui()
        messagebox.showinfo("Premium", "Kod został zweryfikowany. Premium jest aktywne na tym komputerze.")
        self._status("Aktywowano Premium.")

    def _deactivate_license(self):
        if messagebox.askyesno("Premium", "Wyłączyć Premium na tym komputerze?"):
            self.license.deactivate()
            self.notify_var.set(False)
            self._parallel_changed(self.parallel_var.get())
            self._refresh_premium_ui()
            self._settings_changed()

    def _notify_changed(self):
        if self.notify_var.get() and not self.license.premium():
            self.notify_var.set(False)
            messagebox.showinfo("Premium", "Powiadomienia Windows są dostępne po aktywacji Premium.")
        self._settings_changed()

    def _change_theme(self, value):
        self._set_palette(value)
        for w in self.winfo_children():
            w.destroy()
        self.task_views.clear()
        self._build_ui()
        for task_id in self.order:
            self._task_row(self.tasks[task_id])
        self._arrange_rows()
        self._render_history()
        self._refresh_stats()
        self._save_settings()

    def _settings_changed(self):
        self.quality_menu.configure(state="disabled" if self.kind_var.get().endswith("(audio)") else "normal")
        self._save_settings()

    def _parallel_changed(self, value):
        try:
            wanted = int(value)
        except ValueError:
            wanted = 3
        if wanted > 3 and not self.license.premium():
            self.parallel_var.set("3")
            wanted = 3
            messagebox.showinfo("Premium", "4–5 równoległych filmów wymaga kodu Premium.")
        self.max_parallel = max(1, min(5, wanted))
        self._settings_changed()

    def _save_settings(self):
        save_json(self.settings_file, {
            "folder": self.folder_var.get(), "kind": self.kind_var.get(),
            "quality": self.quality_var.get(), "speed": self.speed_var.get(),
            "parallel": self.parallel_var.get(), "playlist": self.playlist_var.get(),
            "subtitles": self.subs_var.get(), "languages": self.languages_var.get(),
            "auto_update": self.auto_update_var.get(), "notify": self.notify_var.get(),
            "trim_start": self.trim_start_var.get(), "trim_end": self.trim_end_var.get(),
            "theme": self.theme_var.get(),
        })

    def _save_queue(self):
        try:
            save_json(self.queue_file, [self.tasks[k].persist() for k in self.order[-120:]])
        except OSError:
            pass

    def _restore_queue(self):
        saved = load_json(self.queue_file, [])
        if not isinstance(saved, list):
            return
        for record in saved[-120:]:
            try:
                task = DownloadTask.restore(record)
                if task.status == "Zakończono" or task.id in self.tasks:
                    continue
                self.tasks[task.id] = task
                self.order.append(task.id)
                self._task_row(task)
            except (TypeError, KeyError, ValueError, OSError):
                continue
        self._arrange_rows()

    def _paste(self):
        try:
            content = self.clipboard_get().strip()
            if content:
                previous = self.urlbox.get("1.0", "end").strip()
                self.urlbox.delete("1.0", "end")
                self.urlbox.insert("1.0", (previous + "\n" if previous else "") + content)
        except Exception:
            self._status("Nie udało się wkleić schowka.")

    def _choose_folder(self):
        selected = filedialog.askdirectory(initialdir=self.folder_var.get() or str(Path.home()))
        if selected:
            self.folder_var.set(selected)
            self._save_settings()

    def _open_folder(self):
        path = Path(self.folder_var.get()).expanduser()
        if not path.is_dir():
            messagebox.showerror("Folder", "Podany folder nie istnieje.")
            return
        if sys.platform == "win32":
            os.startfile(str(path))
        else:
            import webbrowser
            webbrowser.open(path.as_uri())

    def _preview(self):
        urls = self.urlbox.get("1.0", "end").strip().splitlines()
        if not urls:
            self._status("Wklej link do filmu lub playlisty.")
            return
        url = urls[0].strip()
        if not valid_youtube_url(url):
            messagebox.showerror("Link", "Nieprawidłowy adres YouTube.")
            return
        self.preview_request += 1
        sequence = self.preview_request
        self.preview_title.configure(text="⏳ Pobieranie informacji...")
        self.thumb.configure(text="▶", image=None)
        self.preview_image = None
        def run():
            try:
                cmd = metadata_command(url, self.playlist_var.get() and is_playlist_url(url))
                flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                        encoding="utf-8", errors="replace", timeout=70, creationflags=flags)
                if result.returncode:
                    raise RuntimeError((result.stderr or result.stdout)[-400:])
                info = json.loads(result.stdout)
                title = info.get("title") or "Bez tytułu"
                if isinstance(info.get("entries"), list):
                    title += f"  •  Playlista ({info.get('playlist_count') or len(info['entries'])} filmów)"
                elif info.get("duration"):
                    secs = int(info["duration"])
                    title += f"  •  {secs//3600:02d}:{(secs//60)%60:02d}:{secs%60:02d}"
                thumbnail = info.get("thumbnail") or next((x.get("url") for x in reversed(info.get("thumbnails") or []) if x.get("url")), "")
                try:
                    data = fetch_thumbnail(thumbnail) if thumbnail else None
                except (OSError, ValueError):
                    data = None
                self.events.put(("preview", sequence, title, data))
            except Exception as exc:
                self.events.put(("preview_error", sequence, str(exc)[:350]))
        threading.Thread(target=run, daemon=True).start()

    def _premium_required(self, kind, fragments, start, end, parallel) -> bool:
        return kind in PREMIUM_KINDS or fragments > 12 or bool(start or end) or parallel > 3

    def _queue_downloads(self):
        try:
            urls = parse_urls(self.urlbox.get("1.0", "end"))
            dest = Path(self.folder_var.get()).expanduser()
            dest.mkdir(parents=True, exist_ok=True)
            kind, speed = self.kind_var.get(), self.speed_var.get()
            fragments = SPEED_PROFILES[speed]
            start, end = self.trim_start_var.get().strip(), self.trim_end_var.get().strip()
            if start or end:
                normalize_trim_range(start, end)
            if self._premium_required(kind, fragments, start, end, int(self.parallel_var.get())) and not self.license.premium():
                raise ValueError("Ta funkcja wymaga aktywacji Premium w zakładce Premium.")
            if not tool("yt-dlp.exe") and not tool("yt-dlp"):
                raise FileNotFoundError("Brak yt-dlp.exe. Rozpakuj CAŁY artefakt EXE, wraz z narzędziami.")
            drafts = []
            for url in urls:
                task = DownloadTask(id=uuid.uuid4().hex, url=url, folder=dest,
                                    kind=kind, quality=self.quality_var.get(),
                                    playlist=self.playlist_var.get() and is_playlist_url(url),
                                    subtitles=self.subs_var.get(), languages=self.languages_var.get(),
                                    fragments=fragments, trim_start=start, trim_end=end, title=url)
                make_download_command(task.url, task.folder, task.kind, task.quality, playlist=task.playlist,
                                      subtitles=task.subtitles, languages=task.languages, fragments=task.fragments,
                                      trim_start=start, trim_end=end)
                drafts.append(task)
        except (ValueError, OSError, KeyError, FileNotFoundError) as exc:
            messagebox.showerror("Dodawanie", str(exc))
            return
        for task in drafts:
            self.tasks[task.id] = task
            self.order.append(task.id)
            self._task_row(task)
        self._arrange_rows()
        self._save_settings()
        self._save_queue()
        self._refresh_stats()
        self._status(f"Dodano {len(drafts)} zadania do kolejki.")

    def _task_row(self, task):
        self.empty_label.pack_forget()
        box = ctk.CTkFrame(self.queue_scroll, fg_color=self.bg, corner_radius=9)
        box.pack(fill="x", padx=5, pady=4)
        box.grid_columnconfigure(0, weight=1)
        title = self._text(box, str(task.title)[:200], 12, bold=True, anchor="w", wraplength=600, justify="left")
        title.grid(row=0, column=0, sticky="w", padx=11, pady=(9, 3))
        status = self._text(box, task.status, 11, self.muted, anchor="w", wraplength=550)
        status.grid(row=1, column=0, sticky="w", padx=11)
        progress = ctk.CTkProgressBar(box, progress_color=self.accent, fg_color=self.panel2, height=8)
        progress.grid(row=2, column=0, sticky="ew", padx=11, pady=(3, 9))
        progress.set(0.0 if task.status != "Zakończono" else 1)
        actions = ctk.CTkFrame(box, fg_color="transparent")
        actions.grid(row=0, column=1, rowspan=3, padx=7, sticky="e")
        up = self._button(actions, "↑", lambda k=task.id: self._move(k, -1), secondary=True, width=28, height=27)
        down = self._button(actions, "↓", lambda k=task.id: self._move(k, 1), secondary=True, width=28, height=27)
        pause = self._button(actions, "Pauza", lambda k=task.id: self._pause(k), secondary=True, width=60, height=27)
        retry = self._button(actions, "Wznów", lambda k=task.id: self._resume(k), secondary=True, width=62, height=27)
        stop = self._button(actions, "Usuń", lambda k=task.id: self._cancel(k), secondary=True, width=57, height=27)
        for i, control in enumerate((up, down, pause, retry, stop)):
            control.grid(row=0, column=i, padx=2)
        self.task_views[task.id] = {"box": box, "title": title, "status": status,
                                    "progress": progress, "pause": pause, "retry": retry, "stop": stop,
                                    "up": up, "down": down}
        self._update_row(task)

    def _update_row(self, task):
        w = self.task_views.get(task.id)
        if not w:
            return
        state = task.status
        w["status"].configure(text=state[:410], text_color=self.error if state.startswith("Błąd") else (self.accent if state == "Zakończono" else self.muted))
        w["title"].configure(text=task.title[:200])
        w["progress"].set(1 if state == "Zakończono" else task.percent / 100)
        w["pause"].configure(state="normal" if state in {"Pobieranie", "W kolejce"} else "disabled")
        w["retry"].configure(state="normal" if state in {"Wstrzymano", "Błąd", "Przerwano"} else "disabled")
        w["up"].configure(state="normal" if state in {"W kolejce", "Wstrzymano", "Błąd"} else "disabled")
        w["down"].configure(state="normal" if state in {"W kolejce", "Wstrzymano", "Błąd"} else "disabled")

    def _arrange_rows(self):
        for k in self.order:
            if k in self.task_views:
                box = self.task_views[k]["box"]
                box.pack_forget()
                box.pack(fill="x", padx=5, pady=4)
        if not self.order:
            self.empty_label.pack(pady=25)

    def _move(self, key, offset):
        task = self.tasks.get(key)
        if not task or task.status not in {"W kolejce", "Wstrzymano", "Błąd"}:
            return
        pos = self.order.index(key)
        at = pos + offset
        if at < 0 or at >= len(self.order):
            return
        self.order[pos], self.order[at] = self.order[at], self.order[pos]
        self._arrange_rows()
        self._save_queue()

    def _pause(self, key):
        task = self.tasks.get(key)
        if not task or task.status not in {"W kolejce", "Pobieranie"}:
            return
        task.pause_requested = True
        if task.status == "W kolejce":
            task.status = "Wstrzymano"
            self._update_row(task)
            self._save_queue()
        if task.process and task.process.poll() is None:
            try:
                task.process.terminate()
            except OSError:
                pass
        self._status("Wstrzymywanie. Pozostawiamy pliki .part do wznowienia.")

    def _resume(self, key):
        task = self.tasks.get(key)
        if not task or task.status not in {"Wstrzymano", "Błąd", "Przerwano"}:
            return
        if self._premium_required(task.kind, task.fragments, task.trim_start, task.trim_end, 1) and not self.license.premium():
            messagebox.showinfo("Premium", "Do wznowienia tego zadania potrzebna jest ważna licencja Premium.")
            return
        task.pause_requested = False
        task.cancelled = False
        task.started = False
        task.status = "W kolejce"
        task.percent = 0
        self._update_row(task)
        self._save_queue()

    def _cancel(self, key):
        task = self.tasks.get(key)
        if not task:
            return
        task.cancelled = True
        task.pause_requested = False
        if task.process and task.process.poll() is None:
            try:
                task.process.terminate()
            except OSError:
                pass
            # Keep row until worker exits; then remove in final state event.
            task.status = "Przerwano"
            self._update_row(task)
        else:
            self._remove_task(key)
        self._save_queue()

    def _remove_task(self, key):
        if key in self.task_views:
            self.task_views.pop(key)["box"].destroy()
        self.tasks.pop(key, None)
        if key in self.order:
            self.order.remove(key)
        if not self.order:
            self.empty_label.pack(pady=25)
        self._refresh_stats()
        self._save_queue()

    def _scheduler(self):
        if self.closing:
            return
        while self.active_count < self.max_parallel:
            task = next((self.tasks[k] for k in self.order if self.tasks[k].status == "W kolejce" and not self.tasks[k].started), None)
            if task is None:
                break
            if self._premium_required(task.kind, task.fragments, task.trim_start, task.trim_end, 1) and not self.license.premium():
                task.status = "Wstrzymano"
                self._update_row(task)
                self._save_queue()
                continue
            task.started = True
            task.status = "Pobieranie"
            self.active_count += 1
            self._update_row(task)
            self.pool.submit(self._worker, task)
        self.after(400, self._scheduler)

    def _worker(self, task):
        logs = []
        had_file = False
        current_title = task.title
        state, message = "Błąd", ""
        try:
            cmd = make_download_command(task.url, task.folder, task.kind, task.quality,
                                        playlist=task.playlist, subtitles=task.subtitles,
                                        languages=task.languages, fragments=task.fragments,
                                        trim_start=task.trim_start, trim_end=task.trim_end)
            flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, encoding="utf-8", errors="replace", bufsize=1,
                                    creationflags=flags)
            task.process = proc
            if task.pause_requested or task.cancelled or self.closing:
                proc.terminate()
            try:
                assert proc.stdout is not None
                for raw_line in proc.stdout:
                    line = raw_line.strip()
                    evt = parse_progress(line)
                    if evt:
                        if evt["type"] == "progress":
                            self.events.put(("progress", task.id, evt))
                        elif evt["type"] == "item":
                            current_title = evt["title"] or current_title
                            self.events.put(("item", task.id, evt))
                        elif evt["type"] == "file":
                            had_file = True
                            task.files += 1
                            self.history.add({"title": current_title, "url": task.url,
                                              "path": evt["path"], "kind": task.kind,
                                              "playlist": task.playlist})
                            self.events.put(("file", task.id, evt["path"]))
                    elif line and not line.startswith("[download]"):
                        logs.append(line)
                        if len(logs) > 25:
                            logs.pop(0)
                code = proc.wait()
            finally:
                task.process = None
            if task.cancelled or self.closing:
                state = "Przerwano"
            elif task.pause_requested:
                state = "Wstrzymano"
            elif code == 0:
                state = "Zakończono"
                message = f"Pobrano {task.files} plik(ów)" if had_file else "Już istnieje / ukończono"
                if not had_file:
                    self.history.add({"title": current_title, "path": str(task.folder),
                                      "url": task.url, "kind": task.kind, "playlist": task.playlist})
            else:
                state, message = "Błąd", ("\n".join(logs[-3:])[-360:] or f"Kod: {code}")
        except Exception as exc:
            if task.pause_requested:
                state = "Wstrzymano"
            elif task.cancelled:
                state = "Przerwano"
            else:
                state, message = "Błąd", str(exc)[:350]
        finally:
            self.events.put(("final", task.id, state, message))

    def _update_engine(self, *, force=True):
        if self.engine_update_in_progress:
            return
        self.engine_update_in_progress = True
        self.engine_status.configure(text="Sprawdzanie aktualizacji yt-dlp...")
        def run():
            try:
                result = update_engine(force=force)
                self.events.put(("engine", result, False))
            except Exception as exc:
                self.events.put(("engine", f"Aktualizacja nieudana: {str(exc)[:160]}", True))
        threading.Thread(target=run, daemon=True).start()

    def _notify_windows(self, title, body):
        if not (self.license.premium() and self.notify_var.get() and sys.platform == "win32"):
            return
        def run():
            try:
                from winotify import Notification
                Notification(app_id="YOUTUBE VIDEO DOWNLOADER", title=title[:70], msg=body[:160], duration="short").show()
            except Exception:
                # No popups or crashes if OS notifications are disabled.
                pass
        threading.Thread(target=run, daemon=True).start()

    def _drain_events(self):
        if self.closing:
            return
        try:
            for _ in range(110):
                ev = self.events.get_nowait()
                kind = ev[0]
                if kind == "preview":
                    _, n, title, raw = ev
                    if n == self.preview_request:
                        self.preview_title.configure(text=title)
                        if raw:
                            try:
                                pic = ImageOps.contain(Image.open(io.BytesIO(raw)).convert("RGB"), (132, 75))
                                self.preview_image = ctk.CTkImage(light_image=pic, dark_image=pic, size=pic.size)
                                self.thumb.configure(image=self.preview_image, text="")
                            except Exception:
                                pass
                elif kind == "preview_error":
                    if ev[1] == self.preview_request:
                        self.preview_title.configure(text="Błąd podglądu: " + ev[2])
                elif kind == "engine":
                    self.engine_update_in_progress = False
                    self.engine_status.configure(text=ev[1], text_color=self.error if ev[2] else self.accent)
                    self._status(ev[1])
                elif kind in {"progress", "item", "file", "final"}:
                    key = ev[1]
                    if key not in self.tasks:
                        if kind == "final":
                            self.active_count = max(0, self.active_count - 1)
                        continue
                    task = self.tasks[key]
                    if kind == "progress" and task.status == "Pobieranie":
                        d = ev[2]
                        task.percent, task.speed, task.eta = d["percent"], d["speed"], d["eta"]
                        self.task_views[key]["progress"].set(task.percent / 100)
                        self.task_views[key]["status"].configure(text=f"{task.percent:.1f}%  •  {task.speed}  •  ETA {task.eta}")
                    elif kind == "item":
                        task.title = ev[2]["title"]
                        self.task_views[key]["title"].configure(text=task.title[:200])
                    elif kind == "file":
                        if not self.history_render_pending:
                            self.history_render_pending = True
                            self.after(300, self._refresh_history_delayed)
                        self._status(f"Zapisano: {Path(ev[2]).name[:110]}")
                    elif kind == "final":
                        self.active_count = max(0, self.active_count - 1)
                        task.started = False
                        if task.cancelled:
                            self._remove_task(key)
                            continue
                        task.status = ev[2]
                        task.percent = 100 if task.status == "Zakończono" else task.percent
                        self._update_row(task)
                        if ev[3]:
                            self.task_views[key]["status"].configure(text=(task.status + "  •  " + ev[3])[-410:])
                        if task.status == "Zakończono":
                            self._notify_windows("Zakończono pobieranie", task.title)
                        self._save_queue()
                        self._refresh_stats()
        except queue.Empty:
            pass
        self.after(100, self._drain_events)

    def _refresh_history_delayed(self):
        self.history_render_pending = False
        if not self.closing:
            self._render_history()

    def _render_history(self):
        for w in self.history_scroll.winfo_children():
            w.destroy()
        query = self.history_query.get().strip().lower()
        entries = self.history.all()
        if query:
            entries = [x for x in entries if query in (" ".join(str(x.get(k, "")) for k in ("title","url","path","kind"))).lower()]
        entries = entries[:300]
        if not entries:
            self._text(self.history_scroll, "Nie znaleziono pobrań.", 13, self.muted).pack(pady=20)
        for record in entries:
            row = ctk.CTkFrame(self.history_scroll, fg_color=self.bg, corner_radius=8)
            row.pack(fill="x", padx=7, pady=4)
            self._text(row, str(record.get("title") or "Film")[:160], 12, bold=True,
                       anchor="w", justify="left", wraplength=820).pack(fill="x", padx=11, pady=(8, 2))
            self._text(row, f"{record.get('date','')}  •  {record.get('kind','')}  •  {record.get('path','')}"[:240],
                       11, self.muted, anchor="w").pack(fill="x", padx=11, pady=(0, 9))

    def _clear_history(self):
        if messagebox.askyesno("Historia", "Wyczyścić historię? Pliki pozostaną na dysku."):
            self.history.clear()
            self._render_history()

    def _refresh_stats(self):
        active = sum(1 for t in self.tasks.values() if t.status == "Pobieranie")
        completed = sum(1 for t in self.tasks.values() if t.status == "Zakończono")
        self.counter.configure(text=f"Pobieranie: {active}  •  Ukończone: {completed}  •  Kolejka: {len(self.tasks)}")

    def _status(self, message):
        self.footer_status.configure(text=str(message)[:200])

    def _close(self):
        if any(t.status == "Pobieranie" for t in self.tasks.values()):
            if not messagebox.askyesno("Zamykanie", "Pobieranie trwa. Wstrzymać zadania i zamknąć program?"):
                return
        self.closing = True
        for task in self.tasks.values():
            if task.status in {"Pobieranie", "W kolejce"}:
                task.pause_requested = True
                task.status = "Wstrzymano"
            if task.process and task.process.poll() is None:
                try:
                    task.process.terminate()
                except OSError:
                    pass
        self._save_queue()
        self._save_settings()
        self.pool.shutdown(wait=False, cancel_futures=True)
        self.destroy()


def main():
    UltraDownloader().mainloop()


if __name__ == "__main__":
    main()
