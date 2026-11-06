"""Standalone OFFLINE owner tool; only loads the private PEM selected by owner.

Build as a separate EXE. No PEM is packaged with this software.
"""
from __future__ import annotations

import datetime as dt
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from issue_premium_code import issue, load_key, PRESET_DAYS
from owner_registry import record_issue, read_registry, export_csv

BG = "#0C1324"
PANEL = "#17243C"
TEXT = "#E8F3FF"
MUTED = "#ABBDDC"
ACCENT = "#23D3C5"


class OwnerPanel(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ULTRA DOWNLOADER — PANEL WŁAŚCICIELA PREMIUM")
        self.geometry("800x790")
        self.minsize(670, 670)
        self.configure(bg=BG)

        self.pem_path = tk.StringVar()
        self.customer_name = tk.StringVar(value="Klient")
        self.option = tk.StringVar(value="30")
        self.custom_days = tk.StringVar(value="14")
        self.custom_hours = tk.StringVar(value="0")
        self.custom_minutes = tk.StringVar(value="0")
        self.expires_preview = tk.StringVar()
        self.code = ""

        tk.Label(self, text="💎  GENERATOR KODÓW PREMIUM", bg=BG, fg=TEXT,
                 font=("Segoe UI", 20, "bold")).pack(anchor="w", padx=25, pady=(22, 5))
        tk.Label(self, text="Tylko dla właściciela — kody podpisywane prywatnym kluczem PEM.",
                 bg=BG, fg=MUTED, font=("Segoe UI", 11)).pack(anchor="w", padx=26)

        content = tk.Frame(self, bg=PANEL, padx=18, pady=14)
        content.pack(fill="both", expand=True, padx=22, pady=20)
        self._label(content, "1. Prywatny klucz właściciela (.pem)")
        krow = tk.Frame(content, bg=PANEL)
        krow.pack(fill="x", pady=(4, 12))
        self._entry(krow, self.pem_path).pack(side="left", fill="x", expand=True)
        tk.Button(krow, text="Wybierz PEM", command=self._choose_key, bg=ACCENT,
                  fg=BG, relief="flat", padx=10, font=("Segoe UI", 10, "bold")).pack(side="left", padx=(10, 0))
        self._label(content, "2. Nazwa odbiorcy")
        self._entry(content, self.customer_name).pack(fill="x", pady=(4, 14))

        self._label(content, "3. Wybierz okres ważności")
        period_frame = tk.Frame(content, bg=PANEL)
        period_frame.pack(fill="x", pady=(5, 5))
        for ix, (value, caption) in enumerate([("1", "1 dzień"), ("7", "7 dni"),
                 ("30", "30 dni"), ("90", "90 dni"), ("365", "365 dni"),
                 ("0", "Bezterminowo"), ("custom", "Własny czas")]):
            button = tk.Radiobutton(period_frame, text=caption, variable=self.option, value=value,
                                   command=self._refresh_preview, bg=PANEL, fg=TEXT,
                                   activebackground=PANEL, activeforeground=ACCENT,
                                   selectcolor=BG, font=("Segoe UI", 11))
            button.grid(row=ix//3, column=ix%3, sticky="w", padx=(0, 22), pady=4)

        self._label(content, "Własny czas — liczba dni / godzin / minut (bez limitu gotowych wariantów)", small=True)
        custom = tk.Frame(content, bg=PANEL)
        custom.pack(fill="x", pady=(5, 12))
        for caption, var in (("Dni", self.custom_days), ("Godziny", self.custom_hours),
                             ("Minuty", self.custom_minutes)):
            box = tk.Frame(custom, bg=PANEL)
            box.pack(side="left", padx=(0, 14))
            tk.Label(box, text=caption, bg=PANEL, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w")
            ent = self._entry(box, var, width=13)
            ent.pack()
            ent.bind("<KeyRelease>", lambda _event: self._refresh_preview())
        tk.Label(content, textvariable=self.expires_preview, bg=PANEL, fg=ACCENT,
                 font=("Segoe UI", 11, "bold"), anchor="w", wraplength=660,
                 justify="left").pack(fill="x", pady=(2, 14))

        tk.Button(content, text="WYGENERUJ PODPISANY KOD PREMIUM", command=self._generate,
                  bg=ACCENT, fg=BG, font=("Segoe UI", 12, "bold"), relief="flat",
                  padx=12, pady=10, cursor="hand2").pack(fill="x", pady=(0, 12))
        self.result = tk.Text(content, bg=BG, fg=TEXT, height=4, wrap="char", borderwidth=0,
                              font=("Consolas", 10), insertbackground=ACCENT)
        self.result.pack(fill="x")
        actions = tk.Frame(content, bg=PANEL)
        actions.pack(fill="x", pady=(10, 0))
        tk.Button(actions, text="Kopiuj kod", command=self._copy, bg=ACCENT,
                  fg=BG, relief="flat", padx=16).pack(side="left")
        tk.Button(actions, text="Zapisz kod do TXT", command=self._save, bg="#324561",
                  fg=TEXT, relief="flat", padx=16).pack(side="left", padx=10)
        tk.Button(actions, text="Rejestr wydanych kodów", command=self._show_registry,
                  bg="#324561", fg=TEXT, relief="flat", padx=12).pack(side="left", padx=8)
        self._refresh_preview()

    def _label(self, parent, value, small=False):
        tk.Label(parent, text=value, bg=PANEL, fg=MUTED if small else TEXT,
                 font=("Segoe UI", 10 if small else 11, "bold"), anchor="w").pack(anchor="w")

    def _entry(self, parent, var, width=None):
        return tk.Entry(parent, textvariable=var, bg=BG, fg=TEXT,
                        insertbackground=ACCENT, relief="flat", font=("Segoe UI", 12),
                        width=width, highlightthickness=1, highlightbackground="#435674")

    def _choose_key(self):
        path = filedialog.askopenfilename(title="Wskaż oryginalny prywatny klucz właściciela",
                                          filetypes=[("Klucz PEM", "*.pem"), ("Wszystkie pliki", "*.*")])
        if path:
            self.pem_path.set(path)

    def _duration(self):
        value = self.option.get()
        if value != "custom":
            return (int(value), 0, 0)
        try:
            values = tuple(int(x.get()) for x in (self.custom_days, self.custom_hours, self.custom_minutes))
        except ValueError as exc:
            raise ValueError("Własny czas musi zawierać liczby całkowite.") from exc
        if any(x < 0 for x in values) or not any(values):
            raise ValueError("Własny czas musi być dodatni; do kodu bezterminowego wybierz Bezterminowo.")
        return values

    def _refresh_preview(self):
        try:
            days, hours, minutes = self._duration()
            if not any((days, hours, minutes)):
                msg = "Ważność: bezterminowo (na zawsze)."
            else:
                expires = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=days, hours=hours, minutes=minutes)
                msg = "Ważność od wystawienia: " + expires.astimezone().strftime("do %d.%m.%Y, godz. %H:%M:%S (%Z)")
        except (OverflowError, ValueError) as exc:
            msg = "Błędny okres ważności: " + str(exc)
        self.expires_preview.set(msg)

    def _generate(self):
        try:
            days, hours, minutes = self._duration()
            code = issue(load_key(Path(self.pem_path.get())), name=self.customer_name.get(),
                         days=days, hours=hours, minutes=minutes)
        except (ValueError, OSError, TypeError) as exc:
            messagebox.showerror("Nie można utworzyć kodu", str(exc))
            return
        self.code = code
        try:
            expiry = None if not any((days, hours, minutes)) else (dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=days, hours=hours, minutes=minutes)).isoformat()
            record_issue(code, self.customer_name.get(), expiry)
        except (OSError, ValueError) as exc:
            messagebox.showwarning("Rejestr", "Kod utworzony, ale nie udało się zapisać historii: " + str(exc))
        self.result.delete("1.0", "end")
        self.result.insert("1.0", code)
        messagebox.showinfo("Premium", "Kod Premium został wygenerowany i podpisany.")

    def _show_registry(self):
        window = tk.Toplevel(self)
        window.title("PREMIUM — HISTORIA WYDANYCH KODÓW")
        window.geometry("860x510")
        window.configure(bg=BG)
        tk.Label(window, text="LOKALNY REJESTR KODÓW PREMIUM", font=("Segoe UI", 16, "bold"),
                 bg=BG, fg=ACCENT).pack(anchor="w", padx=15, pady=12)
        tk.Label(window, text="To rejestr kodów utworzonych na tym komputerze. Nie pokazuje użycia na innych komputerach.",
                 bg=BG, fg=MUTED).pack(anchor="w", padx=15)
        holder = tk.Frame(window)
        holder.pack(fill="both", expand=True, padx=15, pady=12)
        cols = ('name', 'issued_at', 'expires_at', 'fingerprint')
        table = ttk.Treeview(holder, columns=cols, show='headings')
        for key, label, width in [('name','Odbiorca',170),('issued_at','Wystawiono',210),('expires_at','Wygasa',220),('fingerprint','Identyfikator',150)]:
            table.heading(key, text=label)
            table.column(key, width=width)
        table.pack(fill='both', expand=True)
        try:
            for record in read_registry():
                table.insert('', 'end', values=tuple(record.get(k, '') for k in cols))
        except (OSError, ValueError) as error:
            messagebox.showerror('Rejestr', str(error), parent=window)
        def export():
            target = filedialog.asksaveasfilename(parent=window, defaultextension='.csv', filetypes=[('CSV','*.csv')])
            if target:
                try:
                    export_csv(target)
                    messagebox.showinfo('Eksport', 'Zapisano rejestr CSV.', parent=window)
                except (OSError, ValueError) as error:
                    messagebox.showerror('Eksport', str(error), parent=window)
        tk.Button(window, text='Eksportuj CSV', command=export, bg=ACCENT, fg=BG).pack(pady=(0, 12))

    def _copy(self):
        if not self.code:
            messagebox.showinfo("Premium", "Najpierw wygeneruj kod.")
            return
        self.clipboard_clear()
        self.clipboard_append(self.code)
        self.update()
        messagebox.showinfo("Premium", "Kod skopiowany do schowka.")

    def _save(self):
        if not self.code:
            messagebox.showinfo("Premium", "Najpierw wygeneruj kod.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".txt", initialfile="kod-premium.txt",
                                            filetypes=[("Tekst", "*.txt")])
        if not path:
            return
        try:
            Path(path).write_text(self.code + "\n", encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("Zapis kodu", str(exc))
            return
        messagebox.showinfo("Premium", "Zapisano kod aktywacyjny.")


if __name__ == "__main__":
    OwnerPanel().mainloop()
