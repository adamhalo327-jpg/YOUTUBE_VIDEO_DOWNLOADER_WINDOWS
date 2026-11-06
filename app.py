"""YouTube Video Downloader 1.0 — desktop GUI for downloads you are authorized to make.

Requires standalone yt-dlp.exe; for high-quality merging and MP3 also ffmpeg.exe;
Deno is needed by modern yt-dlp for YouTube JS challenges. The GitHub Actions
workflow bundles all three Windows tools in the EXE distribution folder.
"""

from __future__ import annotations

import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from urllib.parse import parse_qs, urlparse


APP_TITLE = "YOUTUBE VIDEO DOWNLOADER"
APP_VERSION = "1.0"
BACKGROUND = "#0b1220"
PANEL = "#111d30"
INPUT = "#192942"
TEXT = "#edf4ff"
MUTED = "#9daec4"
ACCENT = "#13c8b2"
DANGER = "#ff7272"

VALID_HOSTS = {
    "youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com",
    "youtu.be", "www.youtu.be", "youtube-nocookie.com", "www.youtube-nocookie.com",
}
QUALITY_OPTIONS = (
    "Najlepsza dostępna", "2160p (4K)", "1440p (2K)",
    "1080p (Full HD)", "720p (HD)", "480p", "360p",
)


def valid_video_url(value: str) -> bool:
    """Only accept individual YouTube video URL forms, not arbitrary remote sites."""
    try:
        url = urlparse(value.strip())
        if url.scheme not in ("https", "http") or (url.hostname or "").lower() not in VALID_HOSTS:
            return False
        if url.username or url.password or url.port not in (None, 80, 443):
            return False
        parts = [part for part in url.path.split("/") if part]
        host = (url.hostname or "").lower()
        if host.endswith("youtu.be"):
            return bool(parts and parts[0])
        if not parts:
            return False
        if parts[0] == "watch":
            return bool(parse_qs(url.query).get("v", [""])[0])
        return parts[0] in {"shorts", "live", "embed", "v"} and len(parts) >= 2
    except (ValueError, AttributeError):
        return False


def app_root() -> Path:
    return Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent


def tool(name: str) -> str | None:
    bundled = app_root() / name
    if bundled.is_file():
        return str(bundled)
    return shutil.which(name)


def yt_base_command() -> list[str]:
    executable = tool("yt-dlp.exe") or tool("yt-dlp")
    if not executable:
        raise FileNotFoundError("Nie znaleziono yt-dlp.exe obok programu ani w PATH. Użyj paczki EXE z GitHub Actions.")
    cmd = [executable, "--ignore-config", "--no-playlist", "--no-warnings", "--windows-filenames"]
    ffmpeg = tool("ffmpeg.exe") or tool("ffmpeg")
    if ffmpeg:
        cmd.extend(["--ffmpeg-location", str(Path(ffmpeg).parent)])
    deno = tool("deno.exe") or tool("deno")
    if deno:
        cmd.extend(["--js-runtimes", "deno:" + deno])
    # Standalone yt-dlp includes EJS components. A fallback would require network
    # fetching new helper scripts; it is intentionally not enabled here.
    return cmd


def make_download_command(url: str, dest: Path, kind: str, quality: str) -> list[str]:
    if not valid_video_url(url):
        raise ValueError("Wklej prawidłowy link do pojedynczego filmu YouTube.")
    if kind not in {"MP4 (wideo)", "MP3 (audio)"}:
        raise ValueError("Nieznany format wyjściowy.")
    if quality not in QUALITY_OPTIONS:
        raise ValueError("Nieznana jakość.")
    cmd = yt_base_command()
    cmd += [
        "--newline", "--progress", "--progress-template",
        "download:PROGRESS:%(progress._percent_str)s|%(progress._speed_str)s|%(progress._eta_str)s",
        "--paths", str(dest),
        "-o", "%(title).180B [%(id)s].%(ext)s",
        "--no-overwrites",
    ]
    if kind == "MP3 (audio)":
        if not (tool("ffmpeg.exe") or tool("ffmpeg")):
            raise FileNotFoundError("Dla MP3 wymagany jest ffmpeg.exe. Użyj paczki EXE z GitHub Actions.")
        cmd += ["-f", "bestaudio/best", "--extract-audio", "--audio-format", "mp3", "--audio-quality", "0"]
    else:
        if quality == "Najlepsza dostępna":
            fmt = "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b"
        else:
            max_height = int(re.search(r"\d+", quality).group(0))
            fmt = (f"bv*[height<={max_height}][ext=mp4]+ba[ext=m4a]/"
                   f"b[height<={max_height}][ext=mp4]/"
                   f"bv*[height<={max_height}]+ba/b[height<={max_height}]")
        cmd += ["-f", fmt, "--merge-output-format", "mp4"]
    cmd += ["--", url.strip()]
    return cmd


class VideoDownloader(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_TITLE} {APP_VERSION}")
        self.configure(bg=BACKGROUND)
        self.geometry("800x650")
        self.minsize(660, 590)
        self.events: queue.Queue = queue.Queue()
        self.active_process: subprocess.Popen | None = None
        self.busy = False
        self.cancelled = False
        self.url_var = tk.StringVar()
        self.kind_var = tk.StringVar(value="MP4 (wideo)")
        self.quality_var = tk.StringVar(value="1080p (Full HD)")
        downloads = Path.home() / "Downloads"
        self.folder_var = tk.StringVar(value=str(downloads if downloads.is_dir() else Path.home()))
        self.status_var = tk.StringVar(value="Gotowe — wklej link do filmu.")
        self.video_var = tk.StringVar(value="Tytuł pojawi się tutaj po sprawdzeniu linku")
        self.progress_var = tk.DoubleVar(value=0)
        self._style()
        self._ui()
        self.kind_var.trace_add("write", self._update_format_state)
        self.after(120, self._drain_events)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TCombobox", fieldbackground=INPUT, background=INPUT, foreground=TEXT,
                        arrowcolor=TEXT, bordercolor="#31445e", lightcolor=INPUT, darkcolor=INPUT,
                        padding=9)
        style.map("TCombobox", fieldbackground=[("readonly", INPUT)],
                  foreground=[("readonly", TEXT)], selectbackground=[("readonly", INPUT)],
                  selectforeground=[("readonly", TEXT)])
        style.configure("Mint.Horizontal.TProgressbar", troughcolor=INPUT, background=ACCENT,
                        bordercolor=INPUT, lightcolor=ACCENT, darkcolor=ACCENT, thickness=15)

    def _ui(self) -> None:
        top = tk.Frame(self, bg=BACKGROUND)
        top.pack(fill="x", padx=31, pady=(24, 12))
        tk.Label(top, text="▶", fg=ACCENT, bg=BACKGROUND, font=("Segoe UI", 27, "bold")).pack(side="left", padx=(0, 10))
        heading = tk.Frame(top, bg=BACKGROUND)
        heading.pack(side="left")
        tk.Label(heading, text=APP_TITLE, bg=BACKGROUND, fg=TEXT,
                 font=("Segoe UI", 19, "bold")).pack(anchor="w")
        tk.Label(heading, text="MP4  •  MP3  •  HD / 4K  •  Windows", bg=BACKGROUND, fg=MUTED,
                 font=("Segoe UI", 10)).pack(anchor="w", pady=(1, 0))
        tk.Label(top, text="v1.0", bg=PANEL, fg=ACCENT, font=("Segoe UI", 10), padx=9,
                 pady=5).pack(side="right")

        card = tk.Frame(self, bg=PANEL, padx=23, pady=19)
        card.pack(fill="both", expand=True, padx=30, pady=(3, 16))
        self._label(card, "LINK DO FILMU")
        url_line = tk.Frame(card, bg=PANEL)
        url_line.pack(fill="x", pady=(6, 8))
        self.url_entry = tk.Entry(url_line, textvariable=self.url_var, bg=INPUT, fg=TEXT,
                                  insertbackground=TEXT, relief="flat", bd=0, font=("Segoe UI", 11))
        self.url_entry.pack(side="left", fill="x", expand=True, ipady=12, padx=(0, 9))
        self._button(url_line, "Wklej", self._paste, secondary=True).pack(side="left", padx=(0, 7))
        self.check_btn = self._button(url_line, "Sprawdź", self._check_video, secondary=True)
        self.check_btn.pack(side="left")

        tk.Label(card, textvariable=self.video_var, bg=PANEL, fg=MUTED, anchor="w",
                 font=("Segoe UI", 10), wraplength=690, justify="left").pack(fill="x", pady=(0, 17))
        row = tk.Frame(card, bg=PANEL)
        row.pack(fill="x")
        left = tk.Frame(row, bg=PANEL)
        left.pack(side="left", fill="x", expand=True, padx=(0, 10))
        right = tk.Frame(row, bg=PANEL)
        right.pack(side="left", fill="x", expand=True)
        self._label(left, "FORMAT")
        self.kind_box = ttk.Combobox(left, textvariable=self.kind_var, state="readonly",
                                      values=["MP4 (wideo)", "MP3 (audio)"])
        self.kind_box.pack(fill="x", pady=(6, 16))
        self._label(right, "JAKOŚĆ WIDEO")
        self.quality_box = ttk.Combobox(right, textvariable=self.quality_var, state="readonly",
                                         values=QUALITY_OPTIONS)
        self.quality_box.pack(fill="x", pady=(6, 16))

        self._label(card, "FOLDER ZAPISU")
        path_line = tk.Frame(card, bg=PANEL)
        path_line.pack(fill="x", pady=(6, 18))
        self.folder_entry = tk.Entry(path_line, textvariable=self.folder_var, bg=INPUT, fg=TEXT,
                                     insertbackground=TEXT, relief="flat", bd=0, font=("Segoe UI", 10))
        self.folder_entry.pack(side="left", fill="x", expand=True, ipady=11, padx=(0, 9))
        self.folder_btn = self._button(path_line, "Wybierz...", self._choose_folder, secondary=True)
        self.folder_btn.pack(side="left")

        self.download_btn = self._button(card, "⬇  POBIERZ", self._download)
        self.download_btn.pack(fill="x", ipady=5)

        status_line = tk.Frame(card, bg=PANEL)
        status_line.pack(fill="x", pady=(17, 6))
        tk.Label(status_line, textvariable=self.status_var, bg=PANEL, fg=TEXT,
                 anchor="w", font=("Segoe UI", 10)).pack(side="left", fill="x", expand=True)
        self.stop_btn = self._button(status_line, "Przerwij", self._stop, secondary=True)
        self.stop_btn.pack(side="right", padx=(8, 0))
        self.stop_btn.configure(state="disabled")
        self.progress = ttk.Progressbar(card, variable=self.progress_var, maximum=100,
                                        style="Mint.Horizontal.TProgressbar")
        self.progress.pack(fill="x", pady=(5, 14))

        bottom = tk.Frame(card, bg=PANEL)
        bottom.pack(fill="x")
        self.open_btn = self._button(bottom, "Otwórz folder", self._open_folder, secondary=True)
        self.open_btn.pack(side="left")
        tk.Label(bottom, text="Tylko materiały, do których masz prawa lub zgodę.",
                 bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(side="right")
        self.url_entry.focus_set()

    @staticmethod
    def _label(parent: tk.Widget, text: str) -> None:
        tk.Label(parent, text=text, bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 9, "bold"), anchor="w").pack(fill="x")

    @staticmethod
    def _button(parent: tk.Widget, text: str, command, secondary=False) -> tk.Button:
        bg = INPUT if secondary else ACCENT
        fg = TEXT if secondary else "#031b1b"
        return tk.Button(parent, text=text, command=command, bg=bg, fg=fg,
                         activebackground="#284360" if secondary else "#36e3ce",
                         activeforeground=TEXT if secondary else "#031b1b",
                         relief="flat", bd=0, font=("Segoe UI", 10, "bold"),
                         padx=14, pady=10, cursor="hand2",
                         disabledforeground="#657688")

    def _update_format_state(self, *_args) -> None:
        if not self.busy:
            self.quality_box.configure(state="disabled" if self.kind_var.get() == "MP3 (audio)" else "readonly")

    def _paste(self) -> None:
        try:
            self.url_var.set(self.clipboard_get().strip())
        except tk.TclError:
            self.status_var.set("Schowek jest pusty.")

    def _choose_folder(self) -> None:
        folder = filedialog.askdirectory(initialdir=self.folder_var.get() or str(Path.home()))
        if folder:
            self.folder_var.set(folder)

    def _open_folder(self) -> None:
        folder = Path(self.folder_var.get()).expanduser()
        if not folder.is_dir():
            messagebox.showerror("Błąd", "Folder nie istnieje.")
            return
        if sys.platform == "win32":
            os.startfile(str(folder))
        else:
            subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(folder)])

    def _set_busy(self, busy: bool) -> None:
        self.busy = busy
        state = "disabled" if busy else "normal"
        self.check_btn.configure(state=state)
        self.download_btn.configure(state=state)
        self.folder_btn.configure(state=state)
        self.stop_btn.configure(state="normal" if busy else "disabled")
        self.kind_box.configure(state="disabled" if busy else "readonly")
        self.quality_box.configure(state="disabled" if busy or self.kind_var.get() == "MP3 (audio)" else "readonly")

    def _begin_job(self) -> bool:
        if self.busy:
            return False
        if not valid_video_url(self.url_var.get()):
            messagebox.showerror("Nieprawidłowy link", "Wklej link do pojedynczego filmu YouTube, np. https://youtu.be/...")
            return False
        self.cancelled = False
        self._set_busy(True)
        return True

    def _check_video(self) -> None:
        if not self._begin_job():
            return
        self.status_var.set("Sprawdzanie informacji o filmie...")
        self.video_var.set("Pobieranie tytułu...")
        threading.Thread(target=self._preview_worker, args=(self.url_var.get().strip(),), daemon=True).start()

    def _preview_worker(self, url: str) -> None:
        try:
            command = yt_base_command() + ["--skip-download", "--print", "%(title)s", "--", url]
            if self.cancelled:
                self.events.put(("cancelled", None))
                return
            proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    text=True, encoding="utf-8", errors="replace",
                                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            self.active_process = proc
            try:
                stdout, stderr = proc.communicate(timeout=90)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate()
                raise TimeoutError("Sprawdzanie filmu trwało zbyt długo.")
            if self.cancelled:
                self.events.put(("cancelled", None))
                return
            if proc.returncode:
                raise RuntimeError(self._meaningful_error(stderr or stdout))
            title = next((line.strip() for line in stdout.splitlines() if line.strip()), "Film YouTube")
            self.events.put(("preview", title))
        except Exception as exc:
            self.events.put(("cancelled" if self.cancelled else "error", None if self.cancelled else str(exc)))
        finally:
            self.active_process = None
            self.events.put(("end_preview", None))

    def _download(self) -> None:
        if not self._begin_job():
            return
        try:
            folder = Path(self.folder_var.get().strip()).expanduser()
            folder.mkdir(parents=True, exist_ok=True)
            if not folder.is_dir():
                raise ValueError("Wybierz poprawny folder.")
            cmd = make_download_command(self.url_var.get().strip(), folder,
                                        self.kind_var.get(), self.quality_var.get())
        except Exception as exc:
            self._set_busy(False)
            messagebox.showerror("Błąd", str(exc))
            return
        self.progress_var.set(0)
        self.status_var.set("Rozpoczynanie pobierania...")
        threading.Thread(target=self._download_worker, args=(cmd,), daemon=True).start()

    def _download_worker(self, cmd: list[str]) -> None:
        tail: list[str] = []
        try:
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            self.active_process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace", bufsize=1,
                env=env, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            assert self.active_process.stdout is not None
            for line in self.active_process.stdout:
                line = line.strip()
                if not line:
                    continue
                tail.append(line)
                tail = tail[-15:]
                if line.startswith("PROGRESS:"):
                    data = line.split("|", 2)
                    match = re.search(r"([0-9]+(?:\.[0-9]+)?)%", data[0])
                    if match:
                        percent = float(match.group(1))
                        speed = data[1].strip() if len(data) > 1 else ""
                        eta = data[2].strip() if len(data) > 2 else ""
                        self.events.put(("progress", (percent, speed, eta)))
                elif "[Merger]" in line or "[ExtractAudio]" in line or "[VideoRemuxer]" in line:
                    self.events.put(("status", "Przetwarzanie końcowego pliku..."))
                elif line.startswith("ERROR:"):
                    self.events.put(("status", "Wystąpił błąd pobierania."))
            code = self.active_process.wait()
            if self.cancelled:
                self.events.put(("cancelled", None))
            elif code == 0:
                self.events.put(("success", None))
            else:
                self.events.put(("error", self._meaningful_error("\n".join(tail))))
        except Exception as exc:
            self.events.put(("cancelled" if self.cancelled else "error", None if self.cancelled else str(exc)))
        finally:
            self.active_process = None
            self.events.put(("end_download", None))

    @staticmethod
    def _meaningful_error(stderr: str) -> str:
        errors = [line.strip() for line in stderr.splitlines() if "ERROR:" in line]
        return "\n".join(errors[-3:])[:850] if errors else (stderr.strip()[-650:] or "Nieznany błąd. Sprawdź link i połączenie internetowe.")

    def _stop(self) -> None:
        if not self.busy:
            return
        self.cancelled = True
        self.status_var.set("Przerywanie pobierania...")
        proc = self.active_process
        if proc and proc.poll() is None:
            try:
                proc.terminate()
            except OSError:
                pass

    def _drain_events(self) -> None:
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "preview":
                    self.video_var.set(str(payload))
                    self.status_var.set("Film rozpoznany. Możesz rozpocząć pobieranie.")
                elif kind == "progress":
                    percent, speed, eta = payload
                    self.progress_var.set(min(100, max(0, percent)))
                    self.status_var.set(f"Pobieranie: {percent:.1f}%   •   {speed}   •   pozostało {eta}")
                elif kind == "status":
                    self.status_var.set(str(payload))
                elif kind == "success":
                    self.progress_var.set(100)
                    self.status_var.set("Gotowe! Plik zapisano w wybranym folderze.")
                elif kind == "cancelled":
                    self.status_var.set("Pobieranie przerwane. Niepełny plik może pozostać w folderze.")
                elif kind == "error":
                    self.status_var.set("Nie udało się pobrać filmu.")
                    messagebox.showerror("Błąd pobierania", str(payload) + "\n\nNiektóre filmy mogą być niedostępne lub ograniczone.")
                elif kind in {"end_preview", "end_download"}:
                    self._set_busy(False)
        except queue.Empty:
            pass
        self.after(120, self._drain_events)

    def _on_close(self) -> None:
        self._stop()
        self.destroy()


if __name__ == "__main__":
    VideoDownloader().mainloop()
