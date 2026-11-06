"""YouTube Video Downloader 3.0 PRO EDITION (Windows desktop).
Use only with recordings you own or have permission to download.
"""
from __future__ import annotations

import io
import datetime as dt
import tkinter as tk
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
from licensing import LicenseManager, format_remaining
from download_statistics import summarize, readable_bytes
from updates import check_release, RELEASES_WEB
from infinity_features import schedule_date, is_due, playlist_indices, turbo_fragments, readable_speed
from video_studio import studio_command, run_studio, OUTPUTS
from cloud_license import CloudLicense
from update_management import download_verified_setup
from data_center import diagnostics, export_backup, import_backup
from universal_downloader import UniversalSelection, PLATFORMS, CONTAINERS, QUALITIES, platform_for, build_command, preview_command, validate
from token_shop import CloudTokenShop, PACKAGES
from premium_access import DownloadSelection, require_access, paid_reason, free_quality, FREE_MAX_PARALLEL, PREMIUM_MAX_PARALLEL, PREMIUM_FEATURES

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
    playlist_items: str = ""
    skip_duplicates: bool = False
    premium_mode: bool = False
    schedule_at: str = ""
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
            "languages", "fragments", "trim_start", "trim_end", "playlist_items", "skip_duplicates", "premium_mode", "schedule_at", "title", "status")}
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
        self.title(APP_TITLE)
        # Windows taskbar/title-bar icon. Keep a fallback for launching from source.
        icon_path = (Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
                     / "assets" / "YVD_ICON.ico")
        if not icon_path.is_file():
            icon_path = Path(__file__).resolve().parent / "assets" / "YVD_ICON.ico"
        if icon_path.is_file():
            try:
                self.iconbitmap(str(icon_path))
            except (OSError, tk.TclError):
                pass
        self.geometry("1200x930")
        self.minsize(990, 760)
        self.home = user_data_dir()
        self.home.mkdir(parents=True, exist_ok=True)
        self.history = History()
        self.license = LicenseManager()
        self.cloud = CloudLicense()
        self.tokens = CloudTokenShop(self.home / "token-wallet-cloud-v12-1.json", self.cloud)
        self.live_mib = 0.0
        self.live_samples = []
        self.cloud_expires_at = None
        self.settings_file = self.home / "settings.json"
        self.queue_file = self.home / "queue-v3.json"
        s = load_json(self.settings_file, {})
        if not isinstance(s, dict):
            s = {}
        folder = Path.home() / "Downloads"
        self.folder_var = ctk.StringVar(value=str(s.get("folder", folder if folder.is_dir() else Path.home())))
        self.kind_var = ctk.StringVar(value=s.get("kind", "MP4 (wideo)"))
        self.quality_var = ctk.StringVar(value=s.get("quality", "1080p (Full HD)"))
        self.speed_var = ctk.StringVar(value=s.get("speed", "Szybki"))
        self.parallel_var = ctk.StringVar(value=str(s.get("parallel", "1")))
        self.playlist_var = ctk.BooleanVar(value=bool(s.get("playlist", False)))
        self.subs_var = ctk.BooleanVar(value=bool(s.get("subtitles", False)))
        self.languages_var = ctk.StringVar(value=s.get("languages", "pl,en"))
        self.auto_update_var = ctk.BooleanVar(value=bool(s.get("auto_update", True)))
        self.auto_app_updates_var = ctk.BooleanVar(value=bool(s.get("auto_app_updates", True)))
        self.notify_var = ctk.BooleanVar(value=bool(s.get("notify", False)))
        self.trim_start_var = ctk.StringVar(value=s.get("trim_start", ""))
        self.trim_end_var = ctk.StringVar(value=s.get("trim_end", ""))
        self.theme_var = ctk.StringVar(value=(s.get("theme", "Ciemny") if self._has_premium() else "Ciemny") if s.get("theme", "Ciemny") in PALETTES else "Ciemny")
        self.playlist_items_var = ctk.StringVar(value="")
        self.skip_duplicates_var = ctk.BooleanVar(value=False)
        self.schedule_var = ctk.StringVar(value="")
        self.universal_url = ctk.StringVar(value="")
        self.universal_format = ctk.StringVar(value="MP4")
        self.universal_quality = ctk.StringVar(value="1080p")
        self.universal_playlist = ctk.BooleanVar(value=False)
        self.universal_subs = ctk.BooleanVar(value=False)
        self.universal_thumbnail = ctk.BooleanVar(value=False)
        self.universal_trim = ctk.StringVar(value="")
        self.universal_events = queue.Queue()
        self.universal_process = None
        self.universal_busy = False
        self.cloud_server_var = ctk.StringVar(value=self.cloud.settings.get("server", ""))
        self.cloud_code_var = ctk.StringVar(value="")
        self.studio_file_var = ctk.StringVar(value="")
        self.studio_format_var = ctk.StringVar(value="MP4")
        self.studio_begin_var = ctk.StringVar(value="")
        self.studio_end_var = ctk.StringVar(value="")
        self.events: queue.Queue[tuple] = queue.Queue()
        self.pool = ThreadPoolExecutor(max_workers=5, thread_name_prefix="yvd")
        self.tasks: dict[str, DownloadTask] = {}
        self.order: list[str] = []
        self.task_views: dict[str, dict] = {}
        self.active_count = 0
        self.max_parallel = max(1, min(PREMIUM_MAX_PARALLEL if self._has_premium() else FREE_MAX_PARALLEL, int(self.parallel_var.get()) if self.parallel_var.get().isdigit() else 1))
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
        self._refresh_dashboard()
        self.after(5500, self._check_app_update_auto)
        self.after(1500, self._verify_cloud_async)
        self.after(2800, self._refresh_wallet_async)
        self.after(60_000, self._wallet_heartbeat)
        self.after(2500, self._live_tick)
        self.after(100, self._drain_events)
        self.after(400, self._scheduler)
        self.after(1000, self._tick_premium)
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
        self._text(head, "TOKEN SHOP 12.1", 13, self.accent, bold=True).pack(side="right", padx=8)
        self.premium_header = self._text(head, "", 11, self.accent, bold=True)
        self.premium_header.pack(side="right", padx=12)
        self._text(self, "Universal Downloader  •  Playlisty  •  MP4 / MP3  •  Napisy  •  Turbo Pro  •  Premium", 12, self.muted).pack(anchor="w", padx=25)
        self.tabs = ctk.CTkTabview(self, fg_color=self.bg, segmented_button_fg_color=self.panel,
                                  segmented_button_selected_color=self.hover,
                                  segmented_button_unselected_color=self.panel2)
        self.tabs.pack(fill="both", expand=True, padx=16, pady=(7, 7))
        for tab in ("Pobieranie", "Playlisty", "Video Studio", "Historia", "Statystyki", "Ustawienia", "Premium", "Cloud", "Centrum 10.0", "Universal 12.0", "Sklep tokenow"):
            self.tabs.add(tab)
        self._download_tab(self.tabs.tab("Pobieranie"))
        self._playlist_tab(self.tabs.tab("Playlisty"))
        self._studio_tab(self.tabs.tab("Video Studio"))
        self._history_tab(self.tabs.tab("Historia"))
        self._statistics_tab(self.tabs.tab("Statystyki"))
        self._settings_tab(self.tabs.tab("Ustawienia"))
        self._premium_tab(self.tabs.tab("Premium"))
        self._cloud_tab(self.tabs.tab("Cloud"))
        self._data_center_tab(self.tabs.tab("Centrum 10.0"))
        self._universal_tab(self.tabs.tab("Universal 12.0"))
        self._token_shop_tab(self.tabs.tab("Sklep tokenow"))
        self.after(200, self._universal_poll)
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
        self._choice(options, self.parallel_var, tuple(str(n) for n in range(1,11)), self._parallel_changed).grid(row=1, column=3, sticky="ew", pady=3)
        flags = ctk.CTkFrame(form, fg_color="transparent")
        flags.grid(row=3, column=0, sticky="ew", padx=13, pady=4)
        self._check(flags, "Cała playlista (PREMIUM)", self.playlist_var, self._settings_changed).pack(side="left", padx=(0, 20))
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
        self._text(form,"HARMONOGRAM (PREMIUM): RRRR-MM-DD GG:MM",11,self.muted).grid(row=6,column=0,sticky="w",padx=15)
        self._entry(form,self.schedule_var,210,placeholder="2026-11-15 23:30").grid(row=7,column=0,sticky="w",padx=15,pady=(2,9))
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

    def _universal_tab(self, root):
        panel = ctk.CTkScrollableFrame(root, fg_color=self.panel)
        panel.pack(fill="both", expand=True, padx=5, pady=5)
        self._text(panel, "UNIVERSAL DOWNLOADER 12.0", 22, self.accent, bold=True).pack(anchor="w", padx=18, pady=(16,5))
        self._text(panel, "YouTube • TikTok • Instagram • Twitch • Vimeo • Facebook • SoundCloud • Reddit • i inne", 12, self.muted).pack(anchor="w", padx=18)
        self._text(panel, "Serwisy: " + "  /  ".join(PLATFORMS), 11, self.muted, wraplength=950, justify="left").pack(anchor="w", padx=18, pady=(5, 12))
        self._text(panel, "LINK DO MATERIAŁU", 12, self.muted, bold=True).pack(anchor="w", padx=18)
        self._entry(panel, self.universal_url, 800, placeholder="https://...").pack(fill="x", padx=18, pady=(4,10))
        line = ctk.CTkFrame(panel, fg_color="transparent")
        line.pack(fill="x", padx=18)
        self._text(line, "FORMAT", 11, self.muted).grid(row=0, column=0, sticky="w")
        self._text(line, "JAKOŚĆ", 11, self.muted).grid(row=0, column=1, sticky="w")
        self._choice(line, self.universal_format, CONTAINERS, width=160).grid(row=1, column=0, padx=(0,10))
        self._choice(line, self.universal_quality, QUALITIES, width=210).grid(row=1, column=1)
        flags = ctk.CTkFrame(panel, fg_color="transparent")
        flags.pack(fill="x", padx=18, pady=12)
        self._check(flags, "Cała kolekcja (Premium)", self.universal_playlist).pack(side="left", padx=(0,15))
        self._check(flags, "Napisy SRT (Premium)", self.universal_subs).pack(side="left", padx=(0,15))
        self._check(flags, "Miniatura (Premium)", self.universal_thumbnail).pack(side="left")
        section = ctk.CTkFrame(panel, fg_color="transparent")
        section.pack(fill="x", padx=18)
        self._text(section, "Fragment (Premium):", 12, self.muted).pack(side="left")
        self._entry(section, self.universal_trim, 220, placeholder="00:00:10-00:00:30").pack(side="left", padx=12)
        self._button(section, "Folder…", self._choose_folder, secondary=True, width=110).pack(side="left")
        self._text(panel, "Folder zapisu: wspólny z zakładką Pobieranie. Obsługa serwisów zależy od yt-dlp i dostępności materiału.", 11, self.muted).pack(anchor="w", padx=18, pady=(8,5))
        buttons = ctk.CTkFrame(panel, fg_color="transparent")
        buttons.pack(fill="x", padx=18, pady=8)
        self._button(buttons, "Sprawdź film", self._universal_preview, width=160, secondary=True).pack(side="left", padx=(0,9))
        self._button(buttons, "POBIERZ", self._universal_start, width=160).pack(side="left", padx=(0,9))
        self._button(buttons, "Anuluj", self._universal_cancel, width=100, secondary=True).pack(side="left")
        self.universal_status = self._text(panel, "Gotowe. FREE: jeden MP4 do 1080p lub MP3; dodatkowe opcje wymagają Premium.", 12, self.accent, wraplength=900, justify="left")
        self.universal_status.pack(anchor="w", padx=18, pady=6)
        self.universal_log = ctk.CTkTextbox(panel, height=210, fg_color=self.bg, text_color=self.text)
        self.universal_log.pack(fill="both", expand=True, padx=18, pady=(5,16))
        self.universal_log.insert("1.0", "Universal Downloader korzysta z yt-dlp. Nie obsługuje omijania DRM ani prywatnych adresów sieciowych.\n")

    def _universal_selection(self):
        return UniversalSelection(url=self.universal_url.get().strip(), folder=Path(self.folder_var.get()).expanduser(),
            container=self.universal_format.get(), quality=self.universal_quality.get(), playlist=self.universal_playlist.get(),
            subtitles=self.universal_subs.get(), thumbnail=self.universal_thumbnail.get(), trim=self.universal_trim.get().strip())

    def _universal_preview(self):
        if self.universal_busy: return
        try:
            url = self.universal_url.get().strip()
            provider = platform_for(url)
            cmd = preview_command(url)
        except (ValueError, OSError, FileNotFoundError) as exc:
            messagebox.showerror("Podgląd", str(exc)); return
        self.universal_busy = True
        self.universal_status.configure(text="Sprawdzanie: " + provider)
        def work():
            try:
                flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=70, creationflags=flags)
                if result.returncode: raise RuntimeError((result.stderr or "Błąd ekstraktora")[-350:])
                data = json.loads(result.stdout)
                self.universal_events.put(("preview", str(data.get("title") or "Bez tytułu") + " • " + str(data.get("extractor_key") or provider)))
            except Exception as exc: self.universal_events.put(("error", str(exc)[:350]))
        threading.Thread(target=work, daemon=True).start()

    def _universal_start(self):
        if self.universal_busy:
            messagebox.showinfo("Universal", "Zakończ bieżące zadanie lub kliknij Anuluj."); return
        try:
            selection = self._universal_selection()
            cmd = build_command(selection, premium=self._has_premium())
            selection.folder.mkdir(parents=True, exist_ok=True)
        except (ValueError, PermissionError, OSError, FileNotFoundError) as exc:
            messagebox.showerror("Universal Downloader", str(exc)); return
        self.universal_busy = True
        self.universal_status.configure(text="Pobieranie: " + platform_for(selection.url))
        self.universal_log.insert("end", "\nSTART: " + platform_for(selection.url) + " • " + selection.container + "\n")
        def work():
            flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            ticket = None
            try:
                ticket = self.tokens.start(selection.url)
            except (OSError, ValueError) as exc:
                self.universal_events.put(("line", "Nagrody offline: " + str(exc)[:90]))
            try:
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                    encoding="utf-8", errors="replace", bufsize=1, creationflags=flags)
                self.universal_process = proc
                saw_download = False
                for line in proc.stdout:
                    self.universal_events.put(("line", line.strip()[:500]))
                    if "[download]" in line and ("100%" in line or "Destination:" in line): saw_download = True
                rc = proc.wait()
                self.universal_events.put(("done", "Pobrano pomyślnie." if rc == 0 else "Zadanie przerwano lub wystąpił błąd (" + str(rc) + ").", ticket if rc == 0 and saw_download else None))
            except Exception as exc: self.universal_events.put(("done", "Błąd: " + str(exc)[:250]))
            finally: self.universal_process = None
        threading.Thread(target=work, daemon=True).start()

    def _universal_cancel(self):
        p = self.universal_process
        if p and p.poll() is None:
            try: p.terminate()
            except OSError: pass
            self.universal_status.configure(text="Anulowanie...")

    def _universal_poll(self):
        if self.closing: return
        try:
            for _ in range(60):
                item = self.universal_events.get_nowait()
                event, payload = item[:2]
                if event == "done" and len(item)>2 and item[2]: self._award_tokens(item[2])
                if event in ("done", "error", "preview"):
                    self.universal_busy = False
                    self.universal_status.configure(text=payload)
                if event == "line" and payload.startswith("PROGRESS:"):
                    self.universal_status.configure(text=payload[:140])
                if event != "line" or not payload.startswith("[download]  "):
                    self.universal_log.insert("end", str(payload) + "\n")
                    self.universal_log.see("end")
        except queue.Empty: pass
        self.after(200, self._universal_poll)

    def _has_premium(self):
        return self.license.premium() or self.cloud.premium() or self.tokens.premium()

    def _playlist_tab(self, root):
        panel=ctk.CTkFrame(root,fg_color=self.panel,corner_radius=12)
        panel.pack(fill="both",expand=True,pady=5)
        self._text(panel,"SMART PLAYLISTS — PREMIUM 10.1",21,self.accent,bold=True).pack(anchor="w",padx=20,pady=18)
        self._text(panel,"W zakładce Pobieranie wklej adres playlisty, a tutaj wybierz pozycje (np. 1,3,5-9).",12,self.muted).pack(anchor="w",padx=20)
        self._text(panel,"Wybrane pozycje playlisty (puste = wszystkie)",12,self.muted).pack(anchor="w",padx=20,pady=(20,5))
        self._entry(panel,self.playlist_items_var,300,placeholder="1,3,5-10").pack(anchor="w",padx=20)
        self._check(panel,"Pomiń materiały już pobrane w tym formacie i folderze",self.skip_duplicates_var).pack(anchor="w",padx=20,pady=10)
        self._button(panel,"Zobacz listę filmów z adresu",self._preview_playlist,width=270).pack(anchor="w",padx=20,pady=12)
        self.playlist_output=ctk.CTkTextbox(panel,fg_color=self.bg,text_color=self.text)
        self.playlist_output.pack(fill="both",expand=True,padx=20,pady=15)

    def _preview_playlist(self):
        if not self._has_premium():
            messagebox.showinfo("Premium", "Smart Playlists wymaga aktywnego Premium.")
            return
        try:
            url=parse_urls(self.urlbox.get("1.0","end"))[0]
            if not is_playlist_url(url):raise ValueError("Podaj adres playlisty w zakładce Pobieranie.")
            binary=tool('yt-dlp.exe') or tool('yt-dlp')
            if not binary:raise FileNotFoundError('Brak yt-dlp.exe')
        except Exception as exc:
            messagebox.showerror('Smart Playlists',str(exc));return
        self.playlist_output.delete('1.0','end');self.playlist_output.insert('1.0','Pobieram listę pozycji…')
        def run():
            try:
                flags=subprocess.CREATE_NO_WINDOW if sys.platform=='win32' else 0
                result=subprocess.run([binary,'--ignore-config','--flat-playlist','--print','%(playlist_index)s | %(title)s',
                  '--playlist-end','200','--yes-playlist',url],capture_output=True,text=True,encoding='utf-8',errors='replace',
                  timeout=100,creationflags=flags)
                text=result.stdout[:25000] if result.returncode==0 else ('Błąd: '+result.stderr[-500:])
            except Exception as exc:text=str(exc)
            self.events.put(('playlist_preview',text))
        threading.Thread(target=run,daemon=True).start()

    def _studio_tab(self, root):
        panel=ctk.CTkFrame(root,fg_color=self.panel,corner_radius=12)
        panel.pack(fill='both',expand=True,pady=5)
        self._text(panel,'VIDEO STUDIO 5.0',21,self.accent,bold=True).pack(anchor='w',padx=22,pady=19)
        self._text(panel,'Konwersja i przycinanie lokalnego pliku. Wymaga Premium i FFmpeg.',12,self.muted).pack(anchor='w',padx=22)
        self._entry(panel,self.studio_file_var).pack(fill='x',padx=22,pady=(22,5))
        self._button(panel,'Wybierz plik wideo/audio',self._studio_pick,width=250).pack(anchor='w',padx=22,pady=7)
        self._choice(panel,self.studio_format_var,list(OUTPUTS)).pack(anchor='w',padx=22,pady=8)
        self._text(panel,'Początek i koniec (opcjonalnie, MM:SS lub HH:MM:SS)',12,self.muted).pack(anchor='w',padx=22)
        row=ctk.CTkFrame(panel,fg_color='transparent');row.pack(anchor='w',padx=22,pady=7)
        self._entry(row,self.studio_begin_var,140,placeholder='Od').pack(side='left',padx=(0,12))
        self._entry(row,self.studio_end_var,140,placeholder='Do').pack(side='left')
        self._button(panel,'EKSPORTUJ PLIK',self._studio_start,width=250).pack(anchor='w',padx=22,pady=18)
        self._button(panel,'POŁĄCZ NAGRANIA (MP4, zgodne kodeki)',self._studio_merge,width=325,secondary=True).pack(anchor='w',padx=22,pady=5)
        self.studio_info=self._text(panel,'Gotowe.',13,self.accent);self.studio_info.pack(anchor='w',padx=22)

    def _studio_pick(self):
        path=filedialog.askopenfilename(filetypes=[('Media','*.mp4 *.mkv *.webm *.mp3 *.wav *.mov *.m4a')])
        if path:self.studio_file_var.set(path)

    def _studio_start(self):
        if not self._has_premium():
            messagebox.showinfo('Premium','Video Studio wymaga aktywnego Premium.');return
        src=Path(self.studio_file_var.get());kind=self.studio_format_var.get()
        dest=filedialog.asksaveasfilename(defaultextension=OUTPUTS[kind],filetypes=[(kind,'*'+OUTPUTS[kind])],initialfile=src.stem+'_studio'+OUTPUTS[kind])
        if not dest:return
        try:cmd=studio_command(src,dest,kind,self.studio_begin_var.get(),self.studio_end_var.get())
        except Exception as exc:messagebox.showerror('Video Studio',str(exc));return
        self.studio_info.configure(text='Przetwarzanie w tle…')
        def run():
            try:
                result=run_studio(cmd)
                message='Ukończono: '+dest if result.returncode==0 else 'FFmpeg: '+result.stderr[-400:]
            except Exception as exc:message=str(exc)
            self.events.put(('studio_done',message))
        threading.Thread(target=run,daemon=True).start()

    def _studio_merge(self):
        if not self._has_premium():
            messagebox.showinfo('Premium','Łączenie wideo wymaga Premium.');return
        sources=filedialog.askopenfilenames(filetypes=[('MP4','*.mp4')])
        if len(sources)<2:return
        dest=filedialog.asksaveasfilename(defaultextension='.mp4',filetypes=[('MP4','*.mp4')])
        if not dest:return
        from video_studio import concat_mp4
        try:cmd,list_file=concat_mp4(sources,dest)
        except Exception as exc:messagebox.showerror('Video Studio',str(exc));return
        self.studio_info.configure(text='Łączenie nagrań…')
        def run():
            try:
                result=run_studio(cmd)
                result_msg=('Połączono: '+dest) if result.returncode==0 else 'FFmpeg: '+result.stderr[-360:]
            except Exception as exc:result_msg=str(exc)
            finally:
                try:list_file.unlink(missing_ok=True)
                except OSError:pass
            self.events.put(('studio_done',result_msg))
        threading.Thread(target=run,daemon=True).start()

    def _cloud_tab(self, root):
        panel=ctk.CTkFrame(root,fg_color=self.panel,corner_radius=12);panel.pack(fill='both',expand=True,pady=5)
        self._text(panel,'PREMIUM CLOUD 5.0',21,self.accent,bold=True).pack(anchor='w',padx=22,pady=15)
        self._text(panel,'Opcjonalne: wymaga własnego wdrożonego Cloudflare Worker + D1. Kody YVD3 działają offline bez zmian.',12,self.muted).pack(anchor='w',padx=22)
        self._text(panel,'Adres serwera HTTPS',12,self.muted).pack(anchor='w',padx=22,pady=(22,4))
        self._entry(panel,self.cloud_server_var).pack(fill='x',padx=22)
        self._text(panel,'Kod aktywacyjny YVD5-',12,self.muted).pack(anchor='w',padx=22,pady=(15,4))
        self._entry(panel,self.cloud_code_var).pack(fill='x',padx=22)
        row=ctk.CTkFrame(panel,fg_color='transparent');row.pack(anchor='w',padx=22,pady=18)
        self._button(row,'Aktywuj w chmurze',self._cloud_activate,width=205).pack(side='left',padx=5)
        self._button(row,'Sprawdź licencję',self._verify_cloud_async,width=200,secondary=True).pack(side='left',padx=5)
        self.cloud_info=self._text(panel,'Cloud nieaktywny',14,self.accent)
        self.cloud_info.pack(anchor='w',padx=22,pady=10)
        self._text(panel,'Brak połączenia = brak dostępu Cloud Premium. Lokalny podpisany kod Premium działa nadal.\nNie wklejaj tutaj sekretu administratora.',12,self.muted,justify='left').pack(anchor='w',padx=22)

    def _cloud_activate(self):
        try:self.cloud.configure(self.cloud_server_var.get())
        except Exception as exc:messagebox.showerror('Premium Cloud',str(exc));return
        code=self.cloud_code_var.get().strip()
        if not code:messagebox.showwarning('Premium Cloud','Wklej kod YVD5-');return
        def run():
            try:result=self.cloud.activate(code)
            except Exception as exc:result={'active':False,'error':str(exc)[:200]}
            self.events.put(('cloud_result',result))
        threading.Thread(target=run,daemon=True).start()

    def _verify_cloud_async(self):
        if self.closing:return
        def run():self.events.put(('cloud_result',self.cloud.validate()))
        threading.Thread(target=run,daemon=True).start()
        self.after(60000,self._verify_cloud_async)

    def _live_tick(self):
        if self.closing:return
        self.live_label.configure(text=f'LIVE: {self.active_count} pobrań • średnio {self.live_mib:.2f} MiB/s • Infinity Auto: {turbo_fragments("Infinity Auto",self.live_mib)} fragmentów')
        width=max(150,self.live_plot.winfo_width());height=105
        self.live_plot.delete('all')
        series=self.live_samples[-30:]
        if len(series)>=2:
            top=max(1,max(series)*1.15)
            coords=[]
            for i,value in enumerate(series):
                coords.extend([6+i*(width-12)/(len(series)-1), height-8-value/top*(height-17)])
            self.live_plot.create_line(*coords,fill=self.accent,width=2,smooth=True)
        self.after(2500,self._live_tick)

    def _data_center_tab(self, root):
        panel = ctk.CTkScrollableFrame(root, fg_color=self.panel, corner_radius=12)
        panel.pack(fill="both", expand=True, pady=4)
        self._text(panel, "CENTRUM DANYCH I DIAGNOSTYKI 10.0", 20, bold=True).pack(anchor="w", padx=18, pady=(19, 12))
        self._text(panel, "Kopia obejmuje ustawienia, historię i kolejkę. Nie obejmuje licencji Premium ani prywatnych kluczy.",
                   12, self.muted, wraplength=850).pack(anchor="w", padx=18, pady=8)
        row = ctk.CTkFrame(panel, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=14)
        self._button(row, "Eksportuj kopię ZIP", self._export_data_backup, width=210).pack(side="left", padx=(0, 12))
        self._button(row, "Przywróć kopię ZIP", self._import_data_backup, width=210, secondary=True).pack(side="left")
        self._text(panel, "Po przywróceniu danych uruchom aplikację ponownie.", 12, self.muted).pack(anchor="w", padx=18)
        self._button(panel, "Sprawdź stan programu i dysku", self._refresh_data_diagnostics, width=290).pack(anchor="w", padx=18, pady=(25, 14))
        self.diagnostics_label = self._text(panel, "Kliknij przycisk, aby sprawdzić narzędzia i wolne miejsce.",
                                            13, self.text, wraplength=860, justify="left")
        self.diagnostics_label.pack(anchor="w", padx=18, pady=10)

    def _refresh_data_diagnostics(self):
        from core import tool as find_tool
        result = diagnostics(self.home, self.folder_var.get())
        tools = {key: bool(find_tool(key)) for key in ("yt-dlp", "ffmpeg", "ffprobe", "deno")}
        lines = [f"Wolne miejsce: {result['wolne_gb']} GB",
                 "Dane: " + ", ".join(f"{name}: {'OK' if exists else 'brak'}" for name, exists in result['dane'].items()),
                 "Narzędzia: " + ", ".join(f"{name}: {'OK' if exists else 'brak'}" for name, exists in tools.items())]
        self.diagnostics_label.configure(text="\n".join(lines))

    def _export_data_backup(self):
        path = filedialog.asksaveasfilename(title="Zapisz kopię danych", defaultextension=".zip",
                                            filetypes=[("Archiwum ZIP", "*.zip")], initialfile="YVD_backup.zip")
        if not path:return
        self._save_settings()
        self._save_queue()
        try:
            export_backup(self.home, path)
            messagebox.showinfo("Kopia zapisana", f"Zapisano kopię danych: {path}")
        except (OSError, ValueError, UnicodeError) as exc:
            messagebox.showerror("Kopia danych", str(exc))

    def _import_data_backup(self):
        path=filedialog.askopenfilename(title="Wybierz kopię danych", filetypes=[("Archiwum ZIP", "*.zip")])
        if not path:return
        if not messagebox.askyesno("Przywróć dane", "Zastąpić ustawienia, historię i kolejkę danymi z kopii?\nBieżące wersje zostaną zachowane jako .before-v10."):
            return
        import zipfile
        try:
            imported=import_backup(self.home,path)
            messagebox.showinfo("Przywrócono kopię", "Przywrócono: " + ", ".join(imported) + "\nUruchom ponownie aplikację.")
        except (OSError, ValueError, KeyError, UnicodeError, zipfile.BadZipFile) as exc:
            messagebox.showerror("Błąd przywracania", str(exc))

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

    def _statistics_tab(self, root):
        panel = ctk.CTkFrame(root, fg_color=self.panel, corner_radius=12)
        panel.pack(fill="both", expand=True, pady=4)
        self._text(panel, "STATYSTYKI POBIERANIA 5.0", 21, bold=True).pack(anchor="w", padx=22, pady=(24, 12))
        self.stats_total = self._text(panel, "", 17, self.accent, bold=True, anchor="w")
        self.stats_total.pack(fill="x", padx=22, pady=7)
        self.stats_space = self._text(panel, "", 15, self.text, anchor="w")
        self.stats_space.pack(fill="x", padx=22, pady=7)
        self.stats_types = self._text(panel, "", 14, self.muted, anchor="w", wraplength=850)
        self.stats_types.pack(fill="x", padx=22, pady=7)
        self.live_label = self._text(panel, "LIVE: brak aktywnych pobrań", 15, self.accent, anchor="w")
        self.live_label.pack(fill="x", padx=22, pady=8)
        self.live_plot = tk.Canvas(panel, height=105, bg=self.panel2, highlightthickness=0)
        self.live_plot.pack(fill="x",padx=22,pady=(4,12))
        self._text(panel, "Statystyki są lokalne: obliczane z historii i plików istniejących na tym komputerze.\n"
                    "Rozmiar nie uwzględnia skasowanych plików ani zapisów wskazujących folder.",
                   12, self.muted, anchor="w", justify="left").pack(fill="x", padx=22, pady=15)
        self._button(panel, "Odśwież statystyki", self._refresh_dashboard, width=200).pack(anchor="w", padx=22, pady=10)

    def _refresh_dashboard(self):
        result = summarize(self.history.all())
        self.stats_total.configure(text=f"Wpisy w historii: {result['count']}")
        self.stats_space.configure(text=f"Rozmiar istniejących plików: {readable_bytes(result['bytes'])}")
        breakdown = ",  ".join(f"{k}: {v}" for k,v in sorted(result['formats'].items()))
        self.stats_types.configure(text="Formaty: " + (breakdown or "brak") + f"    •    Niedostępne ścieżki: {result['missing']}")

    def _check_app_update_auto(self):
        if self.auto_app_updates_var.get() and not self.closing:
            self._check_app_update(quiet=True)

    def _check_app_update(self, quiet=False):
        if getattr(self, '_app_update_busy', False):
            return
        self._app_update_busy = True
        self.app_update_status.configure(text="Sprawdzam wydania programu…")
        def worker():
            try:
                result = check_release()
                self.events.put(("app_update", result, quiet))
            except Exception as err:
                self.events.put(("app_update_error", str(err)[:180], quiet))
        self.pool.submit(worker)

    def _open_release_page(self):
        import webbrowser
        webbrowser.open(RELEASES_WEB)

    def _download_setup_update(self):
        if not messagebox.askyesno('Auto Update 2.0',
          'Pobrać instalator z oficjalnego GitHub Releases i zweryfikować SHA256?\n'
          'Aplikacja NIE uruchomi instalatora automatycznie.'):
            return
        self.app_update_status.configure(text='Pobieranie i weryfikacja instalatora…')
        def run():
            try:
                location=download_verified_setup(self.home / 'updates')
                self.events.put(('verified_setup',str(location),'ok'))
            except Exception as exc:self.events.put(('verified_setup',str(exc)[:240],'error'))
        threading.Thread(target=run,daemon=True).start()

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
        self._text(frame, "AKTUALIZACJE SAMEJ APLIKACJI", 16, self.accent, bold=True).pack(anchor="w", padx=20, pady=(18, 8))
        self._check(frame, "Automatycznie sprawdzaj nowe wydania na GitHub Releases po uruchomieniu",
                    self.auto_app_updates_var, self._save_settings).pack(anchor="w", padx=20, pady=6)
        upd = ctk.CTkFrame(frame, fg_color="transparent")
        upd.pack(fill="x", padx=18, pady=6)
        self._button(upd, "Sprawdź aktualizację programu", lambda: self._check_app_update(quiet=False), width=260).pack(side="left", padx=4)
        self._button(upd, "Otwórz wydania GitHub", self._open_release_page, secondary=True, width=205).pack(side="left", padx=6)
        self._button(frame, "POBIERZ ZWERYFIKOWANY INSTALATOR (SHA256)", self._download_setup_update, width=420).pack(anchor="w",padx=20,pady=8)
        self.app_update_status = self._text(frame, "Nowe wydania są sprawdzane na GitHub Releases. Instalację zatwierdzasz samodzielnie.",
                                            11, self.muted, wraplength=830, justify="left")
        self.app_update_status.pack(anchor="w", padx=22, pady=(0, 8))
        self._text(frame, "TURBO PRO — PREMIUM", 16, self.accent, bold=True).pack(anchor="w", padx=20, pady=(23, 10))
        self._text(frame, "Standard 4 / Szybki 8 / Turbo 12 / Turbo Pro 16 lub 24 / Infinity Auto 8–32 fragmenty.\n"
                         "Darmowa wersja: 1 film naraz do 1080p. Premium: do 10 filmów naraz.\n"
                         "Przyspieszenie zależy od źródła i łącza — więcej wątków nie zawsze pomaga.",
                   12, self.muted, wraplength=820, justify="left").pack(anchor="w", padx=20)
        self._text(frame, "Pauza zachowuje częściowe pliki .part, gdy format i serwer umożliwiają wznowienie.\n"
                         "Przycinanie i niektóre konwersje używają FFmpeg — mogą potrwać dłużej niż pobranie.\n"
                         "Pobieraj wyłącznie własne lub dozwolone materiały. Bez obchodzenia DRM.",
                   12, self.muted, wraplength=820, justify="left").pack(anchor="w", padx=20, pady=(20, 25))

    def _token_shop_tab(self, root):
        panel=ctk.CTkScrollableFrame(root,fg_color=self.panel)
        panel.pack(fill="both",expand=True,padx=8,pady=8)
        self._text(panel,"🪙 SKLEP TOKENÓW — 12.1",22,self.accent,bold=True).pack(anchor="w",padx=18,pady=(15,8))
        self.token_balance_label=self._text(panel,"",19,self.accent,bold=True)
        self.token_balance_label.pack(anchor="w",padx=18,pady=8)
        self.token_expiry_label=self._text(panel,"",12,self.muted)
        self.token_expiry_label.pack(anchor="w",padx=18,pady=5)
        self._text(panel,"Za ukończone pobranie nowego pliku: 10 tokenów. Maksymalnie 100 dziennie.\nTen sam adres nagradzany jest raz dziennie; błędy, anulowane zadania i pliki już istniejące nie dają tokenów.",12,self.muted,wraplength=800,justify="left").pack(anchor="w",padx=18,pady=12)
        for name,spec in PACKAGES.items():
            line=ctk.CTkFrame(panel,fg_color=self.panel2,corner_radius=10)
            line.pack(fill="x",padx=18,pady=6)
            self._text(line,f"{name}  •  {spec['days']} dni dostępu Premium  •  {spec['tokens']} tokenów",13,bold=True).pack(side="left",padx=15,pady=17)
            self._button(line,"KUP ZA TOKENY",lambda key=name:self._buy_tokens(key),width=160).pack(side="right",padx=12)
        self._text(panel,"Saldo i zakupy przechowywane są w Cloudflare D1. Wymagane jest połączenie HTTPS z Premium Cloud 5.1 + Token Shop 12.1.\nPrzyznanie tokenów zależy od zgłoszenia aplikacji i nie jest kryptograficznym dowodem pobrania; system zawiera limity nadużyć.",11,self.muted,wraplength=840,justify="left").pack(anchor="w",padx=18,pady=20)
        self._button(panel,"ODŚWIEŻ PORTFEL Z CHMURY",self._refresh_wallet_async,width=270).pack(anchor="w",padx=18,pady=5)
        self._refresh_token_shop()

    def _refresh_token_shop(self):
        if not hasattr(self,"token_balance_label"): return
        self.token_balance_label.configure(text=f"🪙 Twoje tokeny: {self.tokens.balance}")
        until=self.tokens.premium_until()
        active=self.tokens.premium()
        self.token_expiry_label.configure(text=("Pakiet tokenowy aktywny do: " + until.astimezone().strftime("%d.%m.%Y %H:%M")) if active else "Brak aktywnego pakietu tokenowego")

    def _refresh_wallet_async(self):
        def run():
            try:
                self.tokens.refresh()
                self.events.put(("wallet_status", "Saldo tokenów zsynchronizowane", False))
            except Exception as exc:
                self.events.put(("wallet_status", "Portfel: " + str(exc)[:140], True))
        self.pool.submit(run)

    def _wallet_heartbeat(self):
        if self.closing:return
        self._refresh_wallet_async()
        self.after(60_000, self._wallet_heartbeat)

    def _award_tokens(self,ticket):
        def run():
            try:
                result=self.tokens.complete(ticket)
                message="🪙 +10 tokenów" if result.get('awarded')==10 else result.get('reason','Nie przyznano tokenów')
                self.events.put(("wallet_status",message,False))
            except Exception as exc:
                self.events.put(("wallet_status","Nie udało się potwierdzić tokenów: "+str(exc)[:110],True))
        self.pool.submit(run)

    def _buy_tokens(self,name):
        spec=PACKAGES[name]
        if not messagebox.askyesno("Sklep tokenów",f"Kupić {name}: {spec['days']} dni za {spec['tokens']} tokenów?\nZakup zostanie zapisany na Cloudflare?"):
            return
        def run():
            try:
                expiry=self.tokens.buy(name)
                self.events.put(("wallet_purchase", "Pakiet aktywny do "+expiry.astimezone().strftime("%d.%m.%Y %H:%M"),False))
            except Exception as exc:
                self.events.put(("wallet_purchase",str(exc)[:200],True))
        self.pool.submit(run)

    def _premium_tab(self, root):
        frame = ctk.CTkFrame(root, fg_color=self.panel, corner_radius=13)
        frame.pack(fill="x", padx=8, pady=8)
        self._text(frame, "💎  PREMIUM ACCESS 10.1 — AKTYWACJA KODEM", 21, bold=True).pack(anchor="w", padx=21, pady=(23, 7))
        self.premium_info = self._text(frame, "", 13, self.accent, anchor="w")
        self.premium_info.pack(fill="x", padx=21, pady=(10, 3))
        self.premium_clock = self._text(frame, "", 18, self.accent, bold=True, anchor="w")
        self.premium_clock.pack(fill="x", padx=21, pady=(3, 6))
        self.premium_expiry = self._text(frame, "", 12, self.muted, anchor="w")
        self.premium_expiry.pack(fill="x", padx=21, pady=(0, 12))
        self._text(frame, "Odblokowuje: 4K/8K, Turbo Infinity, playlisty, 2–10 pobrań, Video Studio,\n"
                          "harmonogram, rozszerzone statystyki i motywy.", 12, self.muted,
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
        self._text(frame, "FREE: MP4 do 1080p, MP3, 1 zadanie, historia i kopie danych.\n"
            "PREMIUM: 4K/8K, playlisty, 10 zadań, Turbo, Studio, harmonogram, motywy.\n"
            "Ważność: 1/7/30/90/365 dni, bezterminowo albo własny czas.",
            12, self.muted, justify="left").pack(anchor="w",padx=21,pady=(0,15))
        self._refresh_premium_ui()

    def _refresh_premium_ui(self):
        details = self.license.status()
        state, data = details["state"], details["payload"]
        expires = details["expires_at"]
        if state == "active":
            owner = str(data.get("owner") or "Użytkownik")[:70]
            remaining = details["remaining"]
            self.premium_info.configure(text=f"✅ PREMIUM AKTYWNE  •  {owner}", text_color=self.accent)
            self.premium_clock.configure(text="⏳  POZOSTAŁO: " + format_remaining(remaining), text_color=self.accent)
            if expires is None:
                self.premium_expiry.configure(text="Ważność: na zawsze — kod nie ma daty wygaśnięcia.")
                self.premium_header.configure(text="💎 PREMIUM BEZTERMINOWO", text_color=self.accent)
            else:
                self.premium_expiry.configure(text="Ważne do: " + expires.astimezone().strftime("%d.%m.%Y • %H:%M:%S (czas lokalny)"))
                if remaining >= 86400:
                    compact = f"{remaining // 86400} d {remaining % 86400 // 3600} h"
                else:
                    compact = f"{remaining // 3600} h {remaining % 3600 // 60} min"
                color = self.error if remaining <= 86400 else self.accent
                self.premium_header.configure(text="💎 PREMIUM: " + compact, text_color=color)
                self.premium_clock.configure(text_color=color)
        elif state == "expired":
            self.premium_info.configure(text="⌛ PREMIUM WYGASŁO — aktywuj nowy kod.", text_color=self.error)
            self.premium_clock.configure(text="Pozostały czas: 0 sek.", text_color=self.error)
            self.premium_expiry.configure(text="Kod wygasł: " + expires.astimezone().strftime("%d.%m.%Y • %H:%M:%S (czas lokalny)") if expires else "")
            self.premium_header.configure(text="⌛ PREMIUM WYGASŁO", text_color=self.error)
        else:
            self.premium_info.configure(text="🪙 PREMIUM Z PAKIETU TOKENÓW" if self.tokens.premium() else "🔒 WERSJA DARMOWA — wpisz kod, aby aktywować Premium.", text_color=self.accent if self.tokens.premium() else self.muted)
            self.premium_clock.configure(text=("Ważne do: " + self.tokens.premium_until().astimezone().strftime("%d.%m.%Y %H:%M")) if self.tokens.premium() else "Pozostały czas: —", text_color=self.muted)
            self.premium_expiry.configure(text="" if state == "free" else "Nieprawidłowy zapis licencji. Aktywuj poprawny kod.")
            self.premium_header.configure(text="🪙 TOKEN PREMIUM" if self.tokens.premium() else "FREE", text_color=self.accent if self.tokens.premium() else self.muted)
        if not self._has_premium() and self.theme_var.get() != "Ciemny":
            self.theme_var.set("Ciemny")
            self.after(10, lambda: self._change_theme("Ciemny"))
        if not self._has_premium() and self.max_parallel > FREE_MAX_PARALLEL:
            # Premium expires automatically, including while the program is open.
            # Existing downloads may finish, but no new Premium tasks may start.
            self.max_parallel = FREE_MAX_PARALLEL
            self.parallel_var.set("1")
            self._save_settings()

    def _tick_premium(self):
        if self.closing:
            return
        self._refresh_premium_ui()
        if self.cloud.premium() and not self.license.premium():
            time_label='Bezterminowo'
            if self.cloud_expires_at:
                try:
                    expiration=dt.datetime.fromisoformat(self.cloud_expires_at.replace('Z','+00:00'))
                    seconds=max(0,int((expiration-dt.datetime.now(dt.timezone.utc)).total_seconds()))
                    time_label=f'{seconds//86400} d {seconds%86400//3600} h {seconds%3600//60} min'
                except (ValueError,TypeError):time_label='do sprawdzenia online'
            self.premium_info.configure(text='✅ PREMIUM CLOUD AKTYWNE',text_color=self.accent)
            self.premium_clock.configure(text='⏳ POZOSTAŁO: '+time_label,text_color=self.accent)
            self.premium_header.configure(text='💎 CLOUD: '+time_label,text_color=self.accent)
        self.after(1000, self._tick_premium)

    def _activate_license(self):
        code = self.license_box.get("1.0", "end").strip()
        try:
            self.license.activate(code)
        except (ValueError, OSError) as exc:
            messagebox.showerror("Kod Premium", str(exc))
            return
        self.license_box.delete("1.0", "end")
        self._parallel_changed(self.parallel_var.get())
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
        if self.notify_var.get() and not self._has_premium():
            self.notify_var.set(False)
            messagebox.showinfo("Premium", "Powiadomienia Windows są dostępne po aktywacji Premium.")
        self._settings_changed()

    def _change_theme(self, value):
        if value != "Ciemny" and not self._has_premium():
            self.theme_var.set("Ciemny")
            messagebox.showinfo("Premium", "Jasny i neonowy motyw wymagają Premium.")
            return
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
            wanted = 1
        premium = self._has_premium()
        if wanted > FREE_MAX_PARALLEL and not premium:
            self.parallel_var.set("1")
            wanted = 1
            messagebox.showinfo("Premium", "2–10 równoległych filmów wymaga aktywnego Premium.")
        self.max_parallel = max(1, min(PREMIUM_MAX_PARALLEL if premium else FREE_MAX_PARALLEL, wanted))
        self._settings_changed()

    def _save_settings(self):
        save_json(self.settings_file, {
            "folder": self.folder_var.get(), "kind": self.kind_var.get(),
            "quality": self.quality_var.get(), "speed": self.speed_var.get(),
            "parallel": self.parallel_var.get(), "playlist": self.playlist_var.get(),
            "subtitles": self.subs_var.get(), "languages": self.languages_var.get(),
            "auto_update": self.auto_update_var.get(), "auto_app_updates": self.auto_app_updates_var.get(), "notify": self.notify_var.get(),
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

    def _selection(self, *, kind, quality, fragments, parallel=1, playlist=False,
                   playlist_items="", skip_duplicates=False, schedule_at="",
                   trim_start="", trim_end="", premium_mode=False):
        return DownloadSelection(kind=kind, quality=quality, fragments=fragments,
            parallel=int(parallel), playlist=playlist, playlist_items=playlist_items,
            skip_duplicates=skip_duplicates, schedule_at=schedule_at,
            trim_start=trim_start, trim_end=trim_end, premium_mode=premium_mode)

    def _premium_required(self, kind, fragments, start, end, parallel) -> bool:
        # Legacy helper kept for compatibility; full task policy is below.
        return bool(kind in PREMIUM_KINDS or fragments > 12 or start or end or parallel > 1)

    def _task_selection(self, task):
        return self._selection(kind=task.kind,quality=task.quality,fragments=task.fragments,
            parallel=1,playlist=task.playlist,playlist_items=task.playlist_items,
            skip_duplicates=task.skip_duplicates,schedule_at=task.schedule_at,
            trim_start=task.trim_start,trim_end=task.trim_end,premium_mode=task.premium_mode)

    def _queue_downloads(self):
        try:
            urls = parse_urls(self.urlbox.get("1.0", "end"))
            dest = Path(self.folder_var.get()).expanduser()
            dest.mkdir(parents=True, exist_ok=True)
            kind, speed = self.kind_var.get(), self.speed_var.get()
            fragments = turbo_fragments(speed, self.live_mib) if speed == "Infinity Auto" else SPEED_PROFILES[speed]
            start, end = self.trim_start_var.get().strip(), self.trim_end_var.get().strip()
            if start or end:
                normalize_trim_range(start, end)
            items = playlist_indices(self.playlist_items_var.get())
            when = schedule_date(self.schedule_var.get()) if self.schedule_var.get().strip() else ""
            premium = self._has_premium()
            parallel = int(self.parallel_var.get())
            if not premium and len(urls) > 1:
                raise PermissionError("W wersji FREE dodaj jeden film naraz. Pakiety adresów wymagają Premium.")
            drafts = []
            for url in urls:
                is_playlist = is_playlist_url(url)
                if is_playlist and not premium:
                    raise PermissionError("Całe playlisty wymagają aktywnego Premium.")
                selection=self._selection(kind=kind,quality=self.quality_var.get(),fragments=fragments,
                    parallel=parallel,playlist=is_playlist,playlist_items=items,
                    skip_duplicates=self.skip_duplicates_var.get(),schedule_at=when,
                    trim_start=start,trim_end=end,premium_mode=speed == "Infinity Auto")
                require_access(selection,premium)
                if not tool("yt-dlp.exe") and not tool("yt-dlp"):
                    raise FileNotFoundError("Brak yt-dlp.exe. Rozpakuj CAŁY artefakt EXE, wraz z narzędziami.")
                task = DownloadTask(id=uuid.uuid4().hex,url=url,folder=dest,
                    kind=kind,quality=self.quality_var.get(),playlist=is_playlist,
                    subtitles=self.subs_var.get(),languages=self.languages_var.get(),
                    fragments=fragments,trim_start=start,trim_end=end,playlist_items=items,
                    skip_duplicates=self.skip_duplicates_var.get(),premium_mode=speed == "Infinity Auto",
                    schedule_at=when,title=url)
                make_download_command(task.url,task.folder,task.kind,task.quality,
                    playlist=task.playlist,subtitles=task.subtitles,languages=task.languages,
                    fragments=task.fragments,trim_start=start,trim_end=end,
                    playlist_items=items,skip_duplicates=task.skip_duplicates)
                drafts.append(task)
        except (ValueError, OSError, KeyError, FileNotFoundError, PermissionError) as exc:
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
        if paid_reason(self._task_selection(task)) and not self._has_premium():
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
        allowed_parallel = min(self.max_parallel, PREMIUM_MAX_PARALLEL if self._has_premium() else FREE_MAX_PARALLEL)
        while self.active_count < allowed_parallel:
            task = next((self.tasks[k] for k in self.order if self.tasks[k].status == "W kolejce" and not self.tasks[k].started and is_due(self.tasks[k].schedule_at)), None)
            if task is None:
                break
            if paid_reason(self._task_selection(task)) and not self._has_premium():
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
        ticket = None
        try:ticket = self.tokens.start(task.url)
        except (OSError, ValueError):pass
        logs = []
        had_file = False
        current_title = task.title
        state, message = "Błąd", ""
        try:
            cmd = make_download_command(task.url, task.folder, task.kind, task.quality,
                                        playlist=task.playlist, subtitles=task.subtitles,
                                        languages=task.languages, fragments=task.fragments,
                                        trim_start=task.trim_start, trim_end=task.trim_end, playlist_items=task.playlist_items, skip_duplicates=task.skip_duplicates)
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
            self.events.put(("final", task.id, state, message, had_file, ticket))

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
        if not (self._has_premium() and self.notify_var.get() and sys.platform == "win32"):
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
                elif kind == "app_update":
                    self._app_update_busy = False
                    result, quiet = ev[1], ev[2]
                    if result['newer']:
                        self.app_update_status.configure(text=f"Nowa wersja {result['tag']} dostępna na GitHub Releases.", text_color=self.accent)
                        if not quiet and messagebox.askyesno("Aktualizacja aplikacji", "Dostępne jest nowe wydanie. Otworzyć oficjalną stronę pobierania?\nInstalacja wymaga Twojego potwierdzenia."):
                            self._open_release_page()
                    else:
                        self.app_update_status.configure(text="Masz aktualną wersję 12.1 lub brak nowszego wydania.", text_color=self.muted)
                        if not quiet:
                            messagebox.showinfo("Aktualizacja aplikacji", "Brak nowszego wydania GitHub Releases.")
                elif kind == "app_update_error":
                    self._app_update_busy = False
                    self.app_update_status.configure(text="Nie udało się sprawdzić wydań: " + ev[1], text_color=self.error)
                    if not ev[2]:
                        messagebox.showwarning("Aktualizacja aplikacji", "Sprawdzenie nie powiodło się: " + ev[1])
                elif kind == "verified_setup":
                    result,level=ev[1],ev[2]
                    self.app_update_status.configure(text=("Zweryfikowano: " if level=="ok" else "Błąd: ")+result,text_color=self.accent if level=="ok" else self.error)
                    if level=="ok":
                        import os
                        if sys.platform=="win32": os.startfile(str(Path(result).parent))
                elif kind == "playlist_preview":
                    self.playlist_output.delete("1.0","end");self.playlist_output.insert("1.0",ev[1])
                elif kind == "studio_done":
                    self.studio_info.configure(text=ev[1][:220])
                elif kind == "wallet_status":
                    self._refresh_token_shop()
                    self._status(ev[1])
                elif kind == "wallet_purchase":
                    self._refresh_token_shop()
                    self._refresh_premium_ui()
                    (messagebox.showerror if ev[2] else messagebox.showinfo)("Sklep tokenów",ev[1])
                elif kind == "cloud_result":
                    details=ev[1]
                    if details.get("active"):
                        self.cloud_code_var.set("")
                        self.cloud_expires_at=details.get("expires_at")
                    else:
                        self.cloud_expires_at=None
                    self.cloud_info.configure(text=(("PREMIUM CLOUD AKTYWNE • do "+str(details.get("expires_at") or "bezterminowo")) if details.get("active") else "Premium Cloud nieaktywne: "+str(details.get("error","brak licencji")))[:200])
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
                        sample=readable_speed(task.speed)
                        if sample>0:
                            self.live_samples.append(sample)
                            self.live_samples=self.live_samples[-30:]
                            self.live_mib=sum(self.live_samples)/len(self.live_samples)
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
                        if task.status == "Zakończono" and len(ev) > 4 and ev[4]:
                            self._award_tokens(ev[5]) if len(ev)>5 and ev[5] else None
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
            self._refresh_dashboard()

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
            self._refresh_dashboard()

    def _refresh_stats(self):
        active = sum(1 for t in self.tasks.values() if t.status == "Pobieranie")
        completed = sum(1 for t in self.tasks.values() if t.status == "Zakończono")
        self.counter.configure(text=f"Pobieranie: {active}  •  Ukończone: {completed}  •  Kolejka: {len(self.tasks)}")

    def _status(self, message):
        self.footer_status.configure(text=str(message)[:200])

    def _close(self):
        if self.universal_busy or any(t.status == "Pobieranie" for t in self.tasks.values()):
            if not messagebox.askyesno("Zamykanie", "Pobieranie trwa. Wstrzymać zadania i zamknąć program?"):
                return
        self.closing = True
        self._universal_cancel()
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
