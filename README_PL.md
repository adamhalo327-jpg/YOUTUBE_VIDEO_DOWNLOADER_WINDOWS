# YOUTUBE VIDEO DOWNLOADER 3.1 — PRO EDITION + PREMIUM TIMER

**Windows 10/11, kompilacja EXE przez GitHub Actions bez Android Studio ani lokalnego Pythona.** Kontynuacja 3.0 PRO, 2.0 ULTRA i 1.0. Pobieraj jedynie materiały, do których masz prawa lub zgodę. Aplikacja nie obchodzi DRM; warunki YouTube mogą ograniczać pobieranie.

## Nowość: okresy Premium i licznik ważności

**W panelu właściciela (`YVD_PREMIUM_OWNER.exe`)** możesz wygenerować indywidualne kody:

- 1 dzień (24 godziny), 7, 30, 90, 365 dni,
- **bezterminowo / na zawsze**,
- **własna długość** — podajesz dodatnią liczbę dni, godzin i minut, np. 15 dni 3 godziny 45 minut lub 50 minut.

Po wygenerowaniu kodu jego ważność jest liczona **od chwili wygenerowania**, a nie od pierwszego użycia. Dlatego nie generuj kodów z dużym wyprzedzeniem, jeśli odbiorca ma dostać pełny okres. Nowe kody mają dokładną godzinę wygaśnięcia w UTC; program przelicza ją na lokalny czas użytkownika.

**W normalnej aplikacji** obok informacji o stanie Premium widoczny jest na żywo licznik:

> ⏳ POZOSTAŁO: 29 dni  23 godz.  59 min  59 sek.

W zakładce Premium znajdziesz nazwę odbiorcy, dokładny czas pozostały do wygaśnięcia, datę i godzinę zakończenia. Skrócony status Premium pojawia się też w górnej części okna. Licznik aktualizuje się co sekundę. Kod na zawsze pokazuje **BEZTERMINOWO — na zawsze**. Po wygaśnięciu pojawia się **PREMIUM WYGASŁO**, program przełącza się na bezpłatne funkcje, ogranicza równoległe zadania do trzech i blokuje uruchamianie nowych zadań Premium. Pobierania już rozpoczęte mogą się zakończyć.

**Zachowana zgodność:** istniejące podpisane kody `YVD3-...` z 3.0 nadal działają. Starsze kody z datą (bez godziny) są ważne do końca wskazanego dnia według wcześniejszego modelu; w wersji 3.1 dokładny licznik jest dla nich przybliżeniem opartym na zakończeniu dnia w UTC. Nie trzeba wymieniać oryginalnego klucza prywatnego właściciela.

## Wszystkie dotychczasowe funkcje

- Pobieranie filmów i playlist YouTube, podgląd tytułu i miniatury.
- MP4/MP3, najlepsza dostępna jakość, napisy i 1–3 zadania jednocześnie (bezpłatnie).
- Turbo fragmentów, kolejka z przesuwaniem/ponawianiem, pauza/wznawianie i historia z wyszukiwarką.
- Motywy: ciemny / jasny / neonowy; weryfikowane aktualizacje silnika yt-dlp.
- **Premium:** do 5 pobrań naraz, Turbo Pro 16/24 fragmenty, przycinanie, konwersja MKV/WEBM/WAV i powiadomienia Windows.

## Instalacja przez GitHub w przeglądarce

1. Rozpakuj `YOUTUBE_VIDEO_DOWNLOADER_3_1_PREMIUM_TIMER_GITHUB_ACTIONS.zip` na komputerze.
2. Otwórz https://github.com/adamhalo327-jpg/YOUTUBE_VIDEO_DOWNLOADER_WINDOWS i zakładkę **Code**.
3. Wybierz **Add file → Upload files** i prześlij *zawartość* rozpakowanego folderu (nie sam ZIP). Zatwierdź **Commit changes**. Zastąp stare pliki, zachowując `.github/workflows` i `tests`.
4. Jeśli folder `.github` nie przejdzie przez przeglądarkę: użyj **Add file → Create new file**, wpisz `.github/workflows/build-windows.yml` i wklej zawartość tego pliku z ZIP.
5. Sprawdź obecność `app.py`, `gui.py`, `core.py`, `licensing.py`, `requirements.txt`, `tools/issue_premium_code.py`, `tools/premium_generator_gui.py`, `tests/test_premium_timer.py`, `.github/workflows/build-windows.yml`.
6. Otwórz zakładkę **Actions → Build YouTube Downloader 3.1 PREMIUM TIMER EXE → Run workflow**, o ile budowanie nie uruchomiło się samo.
7. Po zielonym **Success** pobierz **DWA OSOBNE ARTEFAKTY**:
   - `YOUTUBE_VIDEO_DOWNLOADER_3_1_PREMIUM_WINDOWS`: program dla użytkowników (pełny folder z EXE, `_internal`, `yt-dlp.exe`, `ffmpeg.exe`, `ffprobe.exe`, `deno.exe`).
   - `YVD_3_1_PREMIUM_OWNER_WINDOWS`: panel właściciela (`YVD_PREMIUM_OWNER.exe`) służący do generowania kodów.
8. Wyodrębnij wszystkie pliki ZIP. Uruchom program `YOUTUBE_VIDEO_DOWNLOADER_3_1_PREMIUM.exe` na Windows.

Artefakt aplikacji jest **paczka folderowa**, nie pojedynczym plikiem EXE — nie wyjmuj EXE z rozpakowanego folderu.

## Jak wydawać kody Premium bez programowania

1. Otwórz **`YVD_PREMIUM_OWNER.exe`** (osobny artefakt).
2. Wybierz **swój ORYGINALNY klucz prywatny** `YVD_3_0_WLASCICIEL_KLUCZ_PRYWATNY.pem` na dysku. Ten plik został dostarczony osobno przy wersji 3.0; **nie jest w tym ZIP ani w żadnym EXE**.
3. Wpisz nazwę odbiorcy.
4. Wybierz **1 / 7 / 30 / 90 / 365 dni**, **Bezterminowo**, albo **Własny czas** i uzupełnij liczbę dni/godzin/minut.
5. Kliknij **WYGENERUJ PODPISANY KOD PREMIUM** → **Kopiuj kod** lub **Zapisz kod do TXT**.
6. Odbiorca otwiera główny program → **Premium** → wkleja **cały kod `YVD3-...`** → **AKTYWUJ PREMIUM**.
7. Licznik zacznie pokazywać pozostały czas, aktualizując się co sekundę.

**Ważne:** prywatnego PEM **nigdy nie dodawaj do repozytorium GitHub**, artefaktu EXE, ZIP dla klientów ani wiadomości do klientów. Odbiorcom przekazujesz wyłącznie kod. Panel właściciela sprawdza, czy wskazany PEM odpowiada temu samemu kluczowi publicznemu, który jest w aplikacji. Dla kodów na zawsze możesz używać wielokrotnie tego samego PEM. Każdy wygenerowany kod ma własny identyfikator i podpis Ed25519.

### Alternatywa: generator przez wiersz polecenia (Python)

```powershell
python -m pip install cryptography
python tools/issue_premium_code.py --key "C:\BezpiecznyFolder\YVD_3_0_WLASCICIEL_KLUCZ_PRYWATNY.pem" --name "Klient" --days 30
python tools/issue_premium_code.py --key "C:\BezpiecznyFolder\YVD_3_0_WLASCICIEL_KLUCZ_PRYWATNY.pem" --name "VIP" --days 0
python tools/issue_premium_code.py --key "C:\BezpiecznyFolder\YVD_3_0_WLASCICIEL_KLUCZ_PRYWATNY.pem" --name "Klient" --days 16 --hours 4 --minutes 10
```

`--days 0` oznacza bezterminowo, gdy `--hours 0 --minutes 0`.

## Bezpieczeństwo i ograniczenia

- Licencje i ich wygaśnięcie są sprawdzane **lokalnie** podpisem Ed25519. Nie ma serwera licencyjnego. Aktualna godzina pochodzi z systemu Windows; **manipulacja zegarem systemowym może wpłynąć na licznik i sprawdzanie ważności**. Pełna odporność wymagałaby weryfikacji online.
- Kody można przekazywać między komputerami; nie ma przypisywania do urządzenia ani centralnego unieważniania. Dla sprzedaży komercyjnej warto w przyszłości dodać serwer licencji, aktywacje na konto i bezpieczny czas serwera.
- Dane i historia nadal są przechowywane lokalnie w `%LOCALAPPDATA%\YouTubeVideoDownloader\` (w tym `premium-license.json`), więc aktualizacja zachowuje dane wersji 3.0.
- Turbo może zwiększyć prędkość, ale nie gwarantuje przyspieszenia. Źródło, łącze, dostępne formaty, FFmpeg i aktualizacje yt-dlp mają wpływ na wynik.

## Testy

`python -m unittest discover -s tests -v` — 40 testów kodu i zgodności 1.0–3.0. Środowisko testowe bez GUI nie weryfikuje wizualnego działania gotowych EXE; po kompilacji należy uruchomić obydwa na Windows i sprawdzić aktywację na podstawie testowego kodu o krótkiej ważności.
