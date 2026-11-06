"""YOUTUBE VIDEO DOWNLOADER 2.0 — ULTRA DOWNLOADER (Windows desktop).

9 additions: playlists, preview, parallel jobs, auto quality, history, modern UI,
verified engine updater, subtitles, and parallel fragments for long videos.
Only download content you have a right to save.
"""
from __future__ import annotations

import io
import json
import os
import queue
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image, ImageOps

from core import (
    APP_TITLE, APP_VERSION, History, KINDS, QUALITY_OPTIONS, SPEED_PROFILES,
    fetch_thumbnail, is_playlist_url, load_json, make_download_command as _make_download_command,
    metadata_command, parse_progress, parse_urls, save_json, tool,
    update_engine, user_data_dir, valid_youtube_url, valid_video_url, yt_base_command as _yt_base_command,
)

# Keep version 1.0's public helper functions available for existing tests and integrations.
def yt_base_command():
    return _yt_base_command()

def make_download_command(url, dest, kind, quality, **kwargs):
    return _make_download_command(url, dest, kind, quality,
                                  _tool=tool, _base_command=yt_base_command, **kwargs)


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

BG = "#090E1B"
PANEL = "#121B2D"
PANEL2 = "#19253C"
BORDER = "#293951"
TEXT = "#EAF3FF"
MUTED = "#9DACCA"
TEAL = "#23D3C5"
TEAL_HOVER = "#17A89D"
RED = "#F47A86"
FONT = "Segoe UI"


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
    title: str = "Oczekiwanie na rozpoczęcie..."
    status: str = "W kolejce"
    percent: float = 0.0
    speed: str = ""
    eta: str = ""
    files: int = 0
    cancelled: bool = False
    process: subprocess.Popen | None = field(default=None, repr=False)


class UltraDownloader(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_TITLE} {APP_VERSION}")
        self.geometry("1150x840")
        self.minsize(930, 710)
        self.configure(fg_color=BG)

        self.home = user_data_dir()
        self.home.mkdir(parents=True, exist_ok=True)
        self.history = History()
        self.settings_file = self.home / "settings.json"
        settings = load_json(self.settings_file, {})
        if not isinstance(settings, dict):
            settings = {}
        downloads = Path.home() / "Downloads"
        default_folder = str(downloads if downloads.is_dir() else Path.home())
        self.folder_var = ctk.StringVar(value=str(settings.get("folder", default_folder)))
        self.kind_var = ctk.StringVar(value=str(settings.get("kind", KINDS[0])))
        self.quality_var = ctk.StringVar(value=str(settings.get("quality", QUALITY_OPTIONS[0])))
        self.speed_var = ctk.StringVar(value=str(settings.get("speed", "Szybki")))
        self.parallel_var = ctk.StringVar(value=str(settings.get("parallel", "3")))
        self.playlist_var = ctk.BooleanVar(value=bool(settings.get("playlist", True)))
        self.subs_var = ctk.BooleanVar(value=bool(settings.get("subtitles", False)))
        self.languages_var = ctk.StringVar(value=str(settings.get("languages", "pl,en")))
        self.auto_update_var = ctk.BooleanVar(value=bool(settings.get("auto_update", True)))
        self.events: queue.Queue[tuple] = queue.Queue()
        self.task_views: dict[str, dict] = {}
        self.tasks: dict[str, DownloadTask] = {}
        self.pool = ThreadPoolExecutor(max_workers=3, thread_name_prefix="download")
        self.gate = threading.Condition()
        self.active_count = 0
        self.max_parallel = max(1, min(3, int(self.parallel_var.get()) if self.parallel_var.get() in {"1", "2", "3"} else 3))
        self.closing = False
        self.preview_image = None
        self.preview_request = 0
        self.engine_update_in_progress = False
        self.history_render_pending = False

        self._build_ui()
        self._settings_changed()
        self._render_history()
        self._refresh_stats()
        self.after(100, self._drain_events)
        if self.auto_update_var.get() and sys.platform == "win32":
            self.after(2500, lambda: self._update_engine(force=False))
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _save_settings(self):
        settings = {
            "folder": self.folder_var.get(), "kind": self.kind_var.get(),
            "quality": self.quality_var.get(), "speed": self.speed_var.get(),
            "parallel": self.parallel_var.get(), "playlist": self.playlist_var.get(),
            "subtitles": self.subs_var.get(), "languages": self.languages_var.get(),
            "auto_update": self.auto_update_var.get(),
        }
        save_json(self.settings_file, settings)

    def _text(self, parent, value: str, size=13, color=TEXT, bold=False, **kwargs):
        return ctk.CTkLabel(parent, text=value, text_color=color, font=(FONT, size, "bold" if bold else "normal"), **kwargs)

    def _button(self, parent, text, command, *, secondary=False, width=115, height=37):
        return ctk.CTkButton(
            parent, text=text, command=command, width=width, height=height,
            corner_radius=10, font=(FONT, 12, "bold"),
            fg_color=PANEL2 if secondary else TEAL,
            hover_color=BORDER if secondary else TEAL_HOVER,
            text_color=TEXT if secondary else BG,
        )

    def _field(self, parent, var, width=100):
        return ctk.CTkEntry(parent, textvariable=var, height=39, corner_radius=9,
                            fg_color=BG, border_color=BORDER, text_color=TEXT, width=width)

    def _choice(self, parent, var, options, *, command=None, width=200):
        return ctk.CTkOptionMenu(parent, variable=var, values=list(options), width=width, height=38,
                                 fg_color=PANEL2, button_color="#31435F", button_hover_color=BORDER,
                                 text_color=TEXT, command=command)

    def _build_ui(self):
        header = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        header.pack(fill="x", padx=26, pady=(20, 8))
        self._text(header, "▶  YOUTUBE VIDEO DOWNLOADER", 22, bold=True).pack(side="left")
        self._text(header, "ULTRA 2.0", 13, color=TEAL, bold=True).pack(side="right", padx=15)
        self._text(self, "MP4 / MP3   •   Playlisty   •   4K   •   Turbo   •   Napisy   •   Windows", 12, MUTED).pack(anchor="w", padx=30)

        self.tabs = ctk.CTkTabview(self, fg_color=BG, segmented_button_fg_color=PANEL,
                                  segmented_button_selected_color="#1D766F",
                                  segmented_button_unselected_color=PANEL2,
                                  segmented_button_selected_hover_color=TEAL_HOVER)
        self.tabs.pack(fill="both", expand=True, padx=19, pady=(8, 8))
        for name in ("Pobieranie", "Historia", "Ustawienia"):
            self.tabs.add(name)
        self.tabs.set("Pobieranie")
        self._download_tab(self.tabs.tab("Pobieranie"))
        self._history_tab(self.tabs.tab("Historia"))
        self._settings_tab(self.tabs.tab("Ustawienia"))

        footer = ctk.CTkFrame(self, fg_color=BG)
        footer.pack(fill="x", padx=29, pady=(0, 15))
        self.footer_status = self._text(footer, "Gotowe. Możesz dodać film lub playlistę.", 11, MUTED)
        self.footer_status.pack(side="left")
        self.counter = self._text(footer, "", 11, TEAL)
        self.counter.pack(side="right")

    def _download_tab(self, root):
        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(1, weight=1)
        setup = ctk.CTkFrame(root, fg_color=PANEL, corner_radius=15)
        setup.grid(row=0, column=0, sticky="ew", padx=3, pady=(2, 10))
        setup.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(setup, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 7))
        top.grid_columnconfigure(0, weight=1)
        self._text(top, "WKLEJ LINK LUB KILKA LINKÓW (KAŻDY W NOWEJ LINII)", 11, MUTED, bold=True).grid(row=0, column=0, sticky="w")
        self.urlbox = ctk.CTkTextbox(top, height=65, fg_color=BG, text_color=TEXT,
                                     border_width=1, border_color=BORDER, corner_radius=10)
        self.urlbox.grid(row=1, column=0, sticky="ew", pady=(6, 0), padx=(0, 8))
        side_actions = ctk.CTkFrame(top, fg_color="transparent")
        side_actions.grid(row=1, column=1, sticky="ns")
        self._button(side_actions, "Wklej", self._paste, secondary=True, width=108, height=31).pack(pady=(0, 5))
        self._button(side_actions, "Podgląd", self._preview, secondary=True, width=108, height=31).pack()

        preview = ctk.CTkFrame(setup, fg_color=BG, corner_radius=11, height=95)
        preview.grid(row=1, column=0, sticky="ew", padx=18, pady=2)
        preview.grid_columnconfigure(1, weight=1)
        self.thumb = ctk.CTkLabel(preview, text="▶", font=(FONT, 32, "bold"), width=150, height=85,
                                  fg_color=PANEL2, corner_radius=9, text_color=TEAL)
        self.thumb.grid(row=0, column=0, padx=(7, 13), pady=7)
        self.preview_title = self._text(preview, "Podgląd tytułu i miniatury pojawi się tutaj.", 13, TEXT,
                                        wraplength=660, justify="left", anchor="w")
        self.preview_title.grid(row=0, column=1, sticky="ew", padx=(0, 12))

        options = ctk.CTkFrame(setup, fg_color="transparent")
        options.grid(row=2, column=0, sticky="ew", padx=18, pady=(13, 5))
        for i in range(4):
            options.grid_columnconfigure(i, weight=1)
        for idx, txt in enumerate(("FORMAT", "JAKOŚĆ", "SZYBKOŚĆ FRAGMENTÓW", "RÓWNOLEGŁE FILMY")):
            self._text(options, txt, 10, MUTED, bold=True).grid(row=0, column=idx, sticky="w", padx=(0, 7))
        self._choice(options, self.kind_var, KINDS, width=175, command=lambda v: self._settings_changed()).grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=6)
        self.quality_menu = self._choice(options, self.quality_var, QUALITY_OPTIONS, width=185, command=lambda v: self._settings_changed())
        self.quality_menu.grid(row=1, column=1, sticky="ew", padx=(0, 8), pady=6)
        self._choice(options, self.speed_var, SPEED_PROFILES.keys(), width=175, command=lambda v: self._settings_changed()).grid(row=1, column=2, sticky="ew", padx=(0, 8), pady=6)
        self._choice(options, self.parallel_var, ("1", "2", "3"), width=135, command=self._parallel_changed).grid(row=1, column=3, sticky="ew", pady=6)

        toggles = ctk.CTkFrame(setup, fg_color="transparent")
        toggles.grid(row=3, column=0, sticky="ew", padx=18, pady=(4, 6))
        ctk.CTkCheckBox(toggles, text="Cała playlista (jeśli link zawiera list=)", variable=self.playlist_var,
                        text_color=TEXT, fg_color=TEAL, hover_color=TEAL_HOVER,
                        command=self._settings_changed).pack(side="left", padx=(0, 25))
        ctk.CTkCheckBox(toggles, text="Pobierz napisy (jeśli dostępne)", variable=self.subs_var,
                        text_color=TEXT, fg_color=TEAL, hover_color=TEAL_HOVER,
                        command=self._settings_changed).pack(side="left", padx=(0, 12))
        self._text(toggles, "Języki:", 11, MUTED).pack(side="left")
        self._field(toggles, self.languages_var, width=90).pack(side="left", padx=(7, 0))

        bottom = ctk.CTkFrame(setup, fg_color="transparent")
        bottom.grid(row=4, column=0, sticky="ew", padx=18, pady=(3, 16))
        bottom.grid_columnconfigure(0, weight=1)
        self._field(bottom, self.folder_var).grid(row=0, column=0, sticky="ew", padx=(0, 7))
        self._button(bottom, "Folder...", self._choose_folder, secondary=True, width=93, height=39).grid(row=0, column=1, padx=(0, 7))
        self._button(bottom, "＋  DODAJ DO POBIERANIA", self._queue_downloads, width=210, height=39).grid(row=0, column=2)

        area = ctk.CTkFrame(root, fg_color=PANEL, corner_radius=15)
        area.grid(row=1, column=0, sticky="nsew", padx=3, pady=(0, 1))
        bar = ctk.CTkFrame(area, fg_color="transparent")
        bar.pack(fill="x", padx=15, pady=(10, 3))
        self._text(bar, "KOLEJKA POBIERANIA", 13, bold=True).pack(side="left")
        self._button(bar, "Otwórz folder", self._open_folder, secondary=True, width=128, height=29).pack(side="right")
        self.queue_scroll = ctk.CTkScrollableFrame(area, fg_color="transparent", corner_radius=9)
        self.queue_scroll.pack(fill="both", expand=True, padx=8, pady=(2, 8))
        self.empty_label = self._text(self.queue_scroll, "Brak pobrań. Wklej link i dodaj go do kolejki.", 12, MUTED)
        self.empty_label.pack(pady=30)

    def _history_tab(self, root):
        controls = ctk.CTkFrame(root, fg_color=PANEL, corner_radius=13)
        controls.pack(fill="x", pady=(4, 10))
        self._text(controls, "HISTORIA ZAKOŃCZONYCH POBRAŃ", 15, bold=True).pack(side="left", padx=15, pady=14)
        self._button(controls, "Wyczyść historię", self._clear_history, secondary=True, width=148, height=31).pack(side="right", padx=13)
        self._button(controls, "Odśwież", self._render_history, secondary=True, width=100, height=31).pack(side="right")
        self.history_scroll = ctk.CTkScrollableFrame(root, fg_color=PANEL, corner_radius=14)
        self.history_scroll.pack(fill="both", expand=True)

    def _settings_tab(self, root):
        settings = ctk.CTkFrame(root, fg_color=PANEL, corner_radius=15)
        settings.pack(fill="x", padx=4, pady=4)
        self._text(settings, "USTAWIENIA I AKTUALIZACJE", 19, bold=True).pack(anchor="w", padx=22, pady=(22, 12))
        ctk.CTkCheckBox(settings, text="Automatycznie sprawdzaj aktualizacje yt-dlp (co 24 godziny)",
                        variable=self.auto_update_var, fg_color=TEAL, hover_color=TEAL_HOVER,
                        text_color=TEXT, command=self._settings_changed).pack(anchor="w", padx=22, pady=10)
        self._text(settings, "Aktualizowany jest wyłącznie silnik yt-dlp, nie cała aplikacja ani FFmpeg.", 12, MUTED).pack(anchor="w", padx=22)
        line = ctk.CTkFrame(settings, fg_color="transparent")
        line.pack(fill="x", padx=22, pady=17)
        self._button(line, "Sprawdź aktualizację teraz", self._update_engine, width=240).pack(side="left")
        self.engine_status = self._text(line, "Aktualizacje pobierane wyłącznie z oficjalnego GitHub yt-dlp, sprawdzane SHA256.", 11, MUTED,
                                        wraplength=430, justify="left")
        self.engine_status.pack(side="left", padx=16)

        info = ctk.CTkFrame(root, fg_color=PANEL, corner_radius=15)
        info.pack(fill="x", padx=4, pady=12)
        self._text(info, "PRZYSPIESZENIE DŁUGICH FILMÓW", 16, bold=True).pack(anchor="w", padx=22, pady=(20, 10))
        self._text(info, "Tryb Turbo pobiera do 12 fragmentów jednego filmu równolegle, jeśli serwer udostępnia segmenty.",
                   12, TEXT, wraplength=820, justify="left").pack(anchor="w", padx=22)
        self._text(info, "Dodatkowo możesz pobierać jednocześnie 1–3 filmy. Przy limitach YouTube lub wolnym łączu Turbo może nie przyspieszyć pobierania.",
                   12, MUTED, wraplength=820, justify="left").pack(anchor="w", padx=22, pady=(6, 18))

        legal = ctk.CTkFrame(root, fg_color=PANEL, corner_radius=15)
        legal.pack(fill="x", padx=4)
        self._text(legal, "UŻYTKOWANIE", 16, bold=True).pack(anchor="w", padx=22, pady=(17, 7))
        self._text(legal, "Pobieraj tylko filmy, do których masz prawa lub zgodę. Nie wszystkie filmy, napisy i jakości są dostępne. Program nie obchodzi DRM.",
                   12, MUTED, wraplength=820, justify="left").pack(anchor="w", padx=22, pady=(0, 19))

    def _settings_changed(self):
        if self.kind_var.get() == "MP3 (audio)":
            self.quality_menu.configure(state="disabled")
        else:
            self.quality_menu.configure(state="normal")
        self._save_settings()

    def _parallel_changed(self, value):
        with self.gate:
            self.max_parallel = int(value)
            self.gate.notify_all()
        self._settings_changed()

    def _paste(self):
        try:
            value = self.clipboard_get().strip()
            if not value:
                return
            existing = self.urlbox.get("1.0", "end").strip()
            self.urlbox.delete("1.0", "end")
            self.urlbox.insert("1.0", (existing + "\n" if existing else "") + value)
        except Exception:
            self._status("Nie można wkleić zawartości schowka.")

    def _choose_folder(self):
        folder = filedialog.askdirectory(initialdir=self.folder_var.get() or str(Path.home()))
        if folder:
            self.folder_var.set(folder)
            self._save_settings()

    def _open_folder(self):
        folder = Path(self.folder_var.get())
        if not folder.is_dir():
            messagebox.showerror("Folder", "Wybrany folder nie istnieje.")
            return
        if sys.platform == "win32":
            os.startfile(str(folder))
        else:
            import webbrowser
            webbrowser.open(folder.as_uri())

    def _preview(self):
        value = self.urlbox.get("1.0", "end").strip().splitlines()
        if not value:
            self._status("Wklej link przed sprawdzeniem podglądu.")
            return
        url = value[0].strip()
        if not valid_youtube_url(url):
            messagebox.showerror("Link", "Pierwszy link nie jest poprawnym adresem YouTube.")
            return
        self.preview_request += 1
        request_number = self.preview_request
        self.preview_title.configure(text="⏳ Pobieranie informacji o filmie / playliście...")
        self.thumb.configure(text="▶", image=None)
        self.preview_image = None

        def work():
            try:
                full = metadata_command(url, self.playlist_var.get() and is_playlist_url(url))
                result = subprocess.run(full, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        text=True, encoding="utf-8", errors="replace", timeout=65,
                                        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
                if result.returncode != 0:
                    raise RuntimeError((result.stderr or result.stdout)[-420:] or "Nieznany błąd yt-dlp")
                info = json.loads(result.stdout)
                title = info.get("title") or "Bez tytułu"
                entries = info.get("entries")
                if isinstance(entries, list):
                    count = info.get("playlist_count") or len(entries)
                    title += f"   •   Playlista (liczba pozycji: {count}; podgląd do 30)"
                elif info.get("duration"):
                    secs = int(info["duration"])
                    title += f"   •   {secs // 3600:02d}:{(secs // 60) % 60:02d}:{secs % 60:02d}"
                thumbnail = info.get("thumbnail")
                if not thumbnail and isinstance(info.get("thumbnails"), list):
                    thumbnail = (info["thumbnails"][-1] or {}).get("url") if info["thumbnails"] else None
                raw = None
                if thumbnail:
                    try:
                        raw = fetch_thumbnail(thumbnail)
                    except (OSError, ValueError):
                        pass
                self.events.put(("preview", request_number, title, raw))
            except Exception as exc:
                self.events.put(("preview_error", request_number, str(exc)[:430]))

        threading.Thread(target=work, daemon=True, name="preview").start()

    def _queue_downloads(self):
        try:
            urls = parse_urls(self.urlbox.get("1.0", "end"))
            folder = Path(self.folder_var.get()).expanduser()
            folder.mkdir(parents=True, exist_ok=True)
            if not folder.is_dir():
                raise ValueError("Folder zapisu jest nieprawidłowy.")
            if not tool("yt-dlp.exe") and not tool("yt-dlp"):
                raise FileNotFoundError("Brak yt-dlp.exe. Rozpakuj cały folder EXE z GitHub Actions.")
            if self.kind_var.get() == "MP3 (audio)" and not (tool("ffmpeg.exe") or tool("ffmpeg")):
                raise FileNotFoundError("Dla MP3 wymagany jest ffmpeg.exe z paczki programu.")
            if self.subs_var.get() and not (tool("ffmpeg.exe") or tool("ffmpeg")):
                raise FileNotFoundError("Dla napisów SRT potrzebny jest ffmpeg.exe.")
            drafts = []
            for url in urls:
                task = DownloadTask(
                    id=uuid.uuid4().hex, url=url, folder=folder, kind=self.kind_var.get(),
                    quality=self.quality_var.get(), playlist=self.playlist_var.get() and is_playlist_url(url),
                    subtitles=self.subs_var.get(), languages=self.languages_var.get(),
                    fragments=SPEED_PROFILES[self.speed_var.get()], title=url,
                )
                # Validate all commands before starting any thread.
                make_download_command(task.url, task.folder, task.kind, task.quality,
                                      playlist=task.playlist, subtitles=task.subtitles,
                                      languages=task.languages, fragments=task.fragments)
                drafts.append(task)
        except (OSError, ValueError, FileNotFoundError, KeyError) as exc:
            messagebox.showerror("Nie można dodać pobierania", str(exc))
            return
        self._save_settings()
        self.empty_label.pack_forget()
        for task in drafts:
            self.tasks[task.id] = task
            self._task_row(task)
            self.pool.submit(self._worker, task)
        self._refresh_stats()
        self._status(f"Dodano {len(drafts)} pozycji do kolejki.")

    def _task_row(self, task: DownloadTask):
        outer = ctk.CTkFrame(self.queue_scroll, fg_color=BG, corner_radius=11)
        outer.pack(fill="x", padx=6, pady=5)
        outer.grid_columnconfigure(0, weight=1)
        title = self._text(outer, task.title, 12, TEXT, bold=True, anchor="w", wraplength=680, justify="left")
        title.grid(row=0, column=0, sticky="w", padx=13, pady=(11, 2))
        status = self._text(outer, "W kolejce", 11, MUTED, anchor="w")
        status.grid(row=1, column=0, sticky="w", padx=13, pady=(0, 5))
        progress = ctk.CTkProgressBar(outer, progress_color=TEAL, fg_color=PANEL2, height=9)
        progress.set(0)
        progress.grid(row=2, column=0, sticky="ew", padx=13, pady=(0, 12))
        stop = self._button(outer, "Przerwij", lambda k=task.id: self._cancel(k), secondary=True, width=92, height=32)
        stop.grid(row=0, column=1, rowspan=3, sticky="e", padx=(4, 13))
        self.task_views[task.id] = {"title": title, "status": status, "progress": progress, "stop": stop}

    def _worker(self, task: DownloadTask):
        with self.gate:
            while not self.closing and not task.cancelled and self.active_count >= self.max_parallel:
                self.gate.wait(timeout=0.5)
            if self.closing or task.cancelled:
                self.events.put(("state", task.id, "Przerwano", ""))
                return
            self.active_count += 1
        try:
            self.events.put(("state", task.id, "Pobieranie", ""))
            cmd = make_download_command(task.url, task.folder, task.kind, task.quality,
                                        playlist=task.playlist, subtitles=task.subtitles,
                                        languages=task.languages, fragments=task.fragments)
            if task.cancelled or self.closing:
                self.events.put(("state", task.id, "Przerwano", ""))
                return
            flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, encoding="utf-8", errors="replace", bufsize=1,
                                    creationflags=flags)
            task.process = proc
            if task.cancelled or self.closing:
                proc.terminate()
            recent_logs = []
            had_file = False
            current_title = task.url
            try:
                assert proc.stdout is not None
                for line in proc.stdout:
                    line = line.strip()
                    event = parse_progress(line)
                    if event:
                        if event["type"] == "progress":
                            self.events.put(("progress", task.id, event))
                        elif event["type"] == "item":
                            current_title = event["title"] or current_title
                            self.events.put(("item", task.id, event))
                        elif event["type"] == "file":
                            had_file = True
                            task.files += 1
                            self.history.add({
                                "title": current_title, "path": event["path"], "url": task.url,
                                "kind": task.kind, "playlist": task.playlist,
                            })
                            self.events.put(("file", task.id, event["path"]))
                    elif line and not line.startswith("[download] "):
                        recent_logs.append(line)
                        if len(recent_logs) > 20:
                            recent_logs.pop(0)
                code = proc.wait()
            finally:
                task.process = None
            if task.cancelled:
                self.events.put(("state", task.id, "Przerwano", ""))
            elif code == 0:
                if not had_file:
                    self.history.add({"title": current_title, "path": str(task.folder), "url": task.url,
                                      "kind": task.kind, "playlist": task.playlist})
                self.events.put(("state", task.id, "Zakończono", f"Pobrano: {task.files} plik(ów)" if had_file else "Ukończono / elementy mogły już istnieć"))
            else:
                msg = "\n".join(recent_logs[-4:])[-480:] or f"Kod błędu: {code}"
                self.events.put(("state", task.id, "Błąd", msg))
        except Exception as exc:
            self.events.put(("state", task.id, "Przerwano" if task.cancelled else "Błąd", str(exc)[:480]))
        finally:
            with self.gate:
                self.active_count -= 1
                self.gate.notify_all()

    def _cancel(self, task_id: str):
        task = self.tasks[task_id]
        if task.status in {"Zakończono", "Błąd", "Przerwano"}:
            return
        task.cancelled = True
        proc = task.process
        if proc and proc.poll() is None:
            try:
                proc.terminate()
            except OSError:
                pass
        with self.gate:
            self.gate.notify_all()
        self._status("Anulowano pobieranie. Plik .part można wznowić później.")

    def _update_engine(self, *, force=True):
        if self.engine_update_in_progress:
            return
        self.engine_update_in_progress = True
        self.engine_status.configure(text="Sprawdzanie aktualizacji silnika...")
        def runner():
            try:
                result = update_engine(force=force)
                self.events.put(("engine", result, False))
            except Exception as exc:
                self.events.put(("engine", f"Aktualizacja nieudana: {str(exc)[:180]}. Program używa dotychczasowego silnika.", True))
        threading.Thread(target=runner, daemon=True, name="engine-update").start()

    def _drain_events(self):
        if self.closing:
            return
        try:
            for _ in range(100):
                event = self.events.get_nowait()
                kind = event[0]
                if kind == "preview":
                    _, number, title, raw = event
                    if number != self.preview_request:
                        continue
                    self.preview_title.configure(text=title)
                    if raw:
                        try:
                            image = Image.open(io.BytesIO(raw)).convert("RGB")
                            image = ImageOps.contain(image, (150, 85))
                            self.preview_image = ctk.CTkImage(light_image=image, dark_image=image, size=image.size)
                            self.thumb.configure(image=self.preview_image, text="")
                        except Exception:
                            self.thumb.configure(text="▶", image=None)
                elif kind == "preview_error":
                    if event[1] == self.preview_request:
                        self.preview_title.configure(text=f"Brak podglądu: {event[2]}")
                elif kind in {"state", "progress", "item", "file"}:
                    tid = event[1]
                    if tid not in self.task_views:
                        continue
                    task = self.tasks[tid]
                    w = self.task_views[tid]
                    if kind == "state":
                        task.status = event[2]
                        extra = event[3]
                        label = f"{task.status}  •  {extra}" if extra else task.status
                        w["status"].configure(text=label[:500], text_color=RED if task.status == "Błąd" else (TEAL if task.status == "Zakończono" else MUTED))
                        if task.status == "Zakończono":
                            w["progress"].set(1)
                        if task.status in {"Zakończono", "Błąd", "Przerwano"}:
                            w["stop"].configure(state="disabled")
                        self._refresh_stats()
                    elif kind == "progress":
                        progress = event[2]
                        task.percent = progress["percent"]
                        task.speed, task.eta = progress["speed"], progress["eta"]
                        w["progress"].set(task.percent / 100)
                        w["status"].configure(text=f"{task.percent:.1f}%  •  {task.speed}  •  ETA {task.eta}")
                    elif kind == "item":
                        part = event[2]
                        task.title = part["title"]
                        idx, total = part["index"], part["total"]
                        line = f"{idx}/{total} • {task.title}" if idx not in {"NA", "None"} else task.title
                        w["title"].configure(text=line[:260])
                        w["progress"].set(0)
                    elif kind == "file":
                        if not self.history_render_pending:
                            self.history_render_pending = True
                            self.after(400, self._refresh_history_delayed)
                        self._status(f"Zapisano: {Path(event[2]).name[:95]}")
                elif kind == "engine":
                    self.engine_update_in_progress = False
                    self.engine_status.configure(text=event[1], text_color=RED if event[2] else TEAL)
                    self._status(event[1])
        except queue.Empty:
            pass
        self.after(100, self._drain_events)

    def _refresh_history_delayed(self):
        self.history_render_pending = False
        if not self.closing:
            self._render_history()

    def _render_history(self):
        for child in self.history_scroll.winfo_children():
            child.destroy()
        records = self.history.all()[:300]
        if not records:
            self._text(self.history_scroll, "Historia jest pusta. Ukończone filmy pojawią się tutaj.", 12, MUTED).pack(pady=25)
        for record in records:
            box = ctk.CTkFrame(self.history_scroll, fg_color=BG, corner_radius=10)
            box.pack(fill="x", padx=6, pady=4)
            title = record.get("title") or "Film"
            self._text(box, str(title)[:180], 12, TEXT, bold=True, anchor="w", wraplength=770, justify="left").pack(fill="x", padx=13, pady=(9, 2))
            note = f"{record.get('date', '')}  •  {record.get('kind', '')}  •  {record.get('path', '')}"
            self._text(box, note[:235], 11, MUTED, anchor="w").pack(fill="x", padx=13, pady=(0, 10))

    def _clear_history(self):
        if messagebox.askyesno("Historia", "Usunąć historię w programie? Pobierane pliki pozostaną na dysku."):
            self.history.clear()
            self._render_history()

    def _refresh_stats(self):
        active = sum(1 for t in self.tasks.values() if t.status == "Pobieranie")
        done = sum(1 for t in self.tasks.values() if t.status == "Zakończono")
        self.counter.configure(text=f"Aktywne: {active}   •   Zakończone: {done}   •   Zadania: {len(self.tasks)}")

    def _status(self, text: str):
        self.footer_status.configure(text=text[:160])

    def _close(self):
        running = any(t.status in {"W kolejce", "Pobieranie"} for t in self.tasks.values())
        if running and not messagebox.askyesno("Zamknij program", "Pobieranie jest w toku. Zatrzymać zadania i zamknąć aplikację?"):
            return
        self.closing = True
        for task in self.tasks.values():
            task.cancelled = True
            proc = task.process
            if proc and proc.poll() is None:
                try:
                    proc.terminate()
                except OSError:
                    pass
        with self.gate:
            self.gate.notify_all()
        self.pool.shutdown(wait=False, cancel_futures=True)
        self._save_settings()
        self.destroy()


def main():
    UltraDownloader().mainloop()


if __name__ == "__main__":
    main()
