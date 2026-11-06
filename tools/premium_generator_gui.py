
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from issue_premium_code import load_key, issue

app = tk.Tk()
app.title('YOUTUBE VIDEO DOWNLOADER — PANEL PREMIUM')
app.geometry('720x490')
app.configure(bg='#10192b')

key_path = tk.StringVar()
customer = tk.StringVar(value='Klient')
period = tk.StringVar(value='30')
days = tk.StringVar(value='14')
hours = tk.StringVar(value='0')
minutes = tk.StringVar(value='0')

frame = tk.Frame(app, bg='#10192b', padx=22, pady=18)
frame.pack(fill='both', expand=True)

def label(text):
    tk.Label(
        frame, text=text, bg='#10192b',
        fg='white', anchor='w'
    ).pack(fill='x', pady=(8, 2))

def entry(value):
    e = tk.Entry(
        frame, textvariable=value, font=('Segoe UI', 11)
    )
    e.pack(fill='x')
    return e

tk.Label(
    frame, text='PANEL WŁAŚCICIELA PREMIUM 3.1',
    bg='#10192b', fg='#2ee4cf',
    font=('Segoe UI', 17, 'bold')
).pack(anchor='w')

label('Prywatny klucz PEM — nie dodawaj go do GitHub')
row = tk.Frame(frame, bg='#10192b')
row.pack(fill='x')
tk.Entry(
    row, textvariable=key_path
).pack(side='left', fill='x', expand=True)

tk.Button(
    row, text='Wybierz PEM',
    command=lambda: key_path.set(
        filedialog.askopenfilename(
            filetypes=[('Klucz PEM', '*.pem')]
        )
    )
).pack(side='left', padx=8)

label('Nazwa odbiorcy')
entry(customer)

label('Czas ważności')
options = [
    '1', '7', '30', '90', '365',
    'Bezterminowo', 'Własny czas'
]
ttk.Combobox(
    frame, textvariable=period,
    values=options, state='readonly'
).pack(fill='x')

label('Własny czas — dni, godziny, minuty')
time_row = tk.Frame(frame, bg='#10192b')
time_row.pack(fill='x')

for title, variable in [
    ('Dni', days), ('Godziny', hours),
    ('Minuty', minutes)
]:
    tk.Label(
        time_row, text=title,
        bg='#10192b', fg='white'
    ).pack(side='left')
    tk.Entry(
        time_row, textvariable=variable, width=7
    ).pack(side='left', padx=(5, 20))

output = tk.Text(frame, height=4, wrap='char')

def generate():
    try:
        if period.get() == 'Bezterminowo':
            d, h, m = 0, 0, 0
        elif period.get() == 'Własny czas':
            d, h, m = (
                int(days.get()),
                int(hours.get()),
                int(minutes.get())
            )
            if d + h + m <= 0:
                raise ValueError('Podaj dodatni czas.')
        else:
            d, h, m = int(period.get()), 0, 0

        code = issue(
            load_key(key_path.get()),
            customer.get(), d, h, m
        )
        output.delete('1.0', 'end')
        output.insert('1.0', code)
    except (ValueError, OSError, TypeError) as err:
        messagebox.showerror(
            'Błąd generowania kodu', str(err)
        )

def copy_code():
    value = output.get('1.0', 'end').strip()
    if value:
        app.clipboard_clear()
        app.clipboard_append(value)

tk.Button(
    frame, text='WYGENERUJ KOD PREMIUM',
    command=generate,
    bg='#2ee4cf',
    font=('Segoe UI', 11, 'bold')
).pack(fill='x', pady=10)

output.pack(fill='x')
tk.Button(
    frame, text='KOPIUJ KOD',
    command=copy_code
).pack(anchor='e', pady=6)

app.mainloop()
