# YOUTUBE VIDEO DOWNLOADER 2.0 — ULTRA DOWNLOADER (Windows)

Aktualizacja działającego programu 1.0, zachowuje pobieranie MP4/MP3, jakości do 4K, wybór folderu, podgląd postępu i anulowanie.

## 9 funkcji wersji 2.0

1. **Całe playlisty**: wklej `youtube.com/playlist?list=...` lub `watch?v=...&list=...`, zaznacz opcję playlisty.
2. **Miniatura + tytuł**: wklej link, kliknij **Podgląd**. Dla playlist podgląd sprawdza maksymalnie 30 pierwszych pozycji.
3. **Kilka filmów naraz**: wklej wiele linków (jeden w linii) i kliknij **Dodaj do pobierania**; jednocześnie mogą pracować 1, 2 lub 3 zadania.
4. **Najlepsza jakość automatycznie**: ustaw „Najlepsza dostępna”, jeśli chcesz maksymalną jakość udostępnioną przez serwis; można ustawić ograniczenie 360p–4K.
5. **Historia**: zakładka Historia przechowuje ukończone pobrania, w tym elementy playlist, w `%LOCALAPPDATA%\YouTubeVideoDownloader\history.json`.
6. **Nowoczesny interfejs**: ciemny motyw, kolejka, pasek postępu, osobne zakładki historii i ustawień.
7. **Automatyczna aktualizacja yt-dlp**: program raz na dobę sprawdza oficjalne wydanie na GitHub; plik jest weryfikowany SHA256 przed zastąpieniem. Można wyłączyć lub uruchomić ręcznie. To aktualizuje *silnik yt-dlp*, nie aplikację, Deno ani FFmpeg.
8. **Napisy**: zaznacz napisy, wybierz języki, np. `pl,en`. Zapisuje dostępne napisy / napisy automatyczne do `.srt` obok wideo. Niedostępne języki nie są tworzone sztucznie.
9. **Szybsze długie filmy**: profile Standard (4 fragmenty), Szybki (8 fragmentów), Turbo (12 fragmentów) — przyspieszenie możliwe dla formatów podzielonych na fragmenty. Efekt zależy od internetu, serwera i limitów YouTube. Jednoczesne pobieranie kilku filmów może obciążać łącze.

**Nie wszystkie formaty, materiały, napisy i jakości są zawsze dostępne. Nie ma gwarancji konkretnej prędkości ani obsługi filmów chronionych, płatnych lub wymagających autoryzacji.** Program nie obchodzi DRM.

## Aktualizacja repozytorium z 1.0

W istniejącym repozytorium GitHub (`YOUTUBE_VIDEO_DOWNLOADER_WINDOWS`) dodaj lub zastąp następujące pliki:

```text
YOUTUBE_VIDEO_DOWNLOADER_WINDOWS/
├── app.py                       (zastąp wersję 1.0)
├── core.py                      (nowy)
├── requirements.txt             (nowy)
├── README_PL.md                 (zastąp)
├── tests/
│   └── test_core.py             (nowy)
└── .github/
    └── workflows/
        └── build-windows.yml   (zastąp poprzedni workflow)
```

Możesz pozostawić poprzedni plik `tests/test_app.py` — funkcje testowane w wersji 1.0 zostały utrzymane. **Uwaga**: dla nowych funkcji testy są w `tests/test_core.py`. GitHub Actions sam rozpozna strukturę folderów; sam plik ZIP **nie jest rozpakowywany przez GitHub**. Musisz rozpakować paczkę na PC i skopiować jej *zawartość* do głównego katalogu repozytorium.

### Instalacja przez GitHub Desktop (Windows)

1. Pobierz ZIP 2.0, wybierz **Wyodrębnij wszystkie**.
2. W GitHub Desktop otwórz istniejące repozytorium i **Repository → Show in Explorer**.
3. Skopiuj wszystkie pliki i foldery z rozpakowanej paczki do repozytorium, zgadzając się na zastąpienie starszych plików.
4. Sprawdź, czy `core.py` i `.github\workflows\build-windows.yml` znajdują się w odpowiednich miejscach.
5. Wróć do GitHub Desktop → **Changes** → wpisz `ULTRA DOWNLOADER 2.0` → **Commit to main** → **Push origin**.
6. Wejdź na GitHub → **Actions** → **Build YouTube Downloader 2.0 EXE** → **Run workflow** (lub wybierz automatyczny build wywołany przez Push).
7. Po zielonym **Success**, otwórz wynik run → **Artifacts / Artefakty** → `YOUTUBE_VIDEO_DOWNLOADER_2_0_WINDOWS`.
8. Rozpakuj cały artefakt. Uruchom `YOUTUBE_VIDEO_DOWNLOADER_2_0.exe` **z rozpakowanego folderu**.

**NIE uruchamiaj EXE prosto z ZIP. NIE przenoś samego EXE.** Obok niego muszą zostać yt-dlp.exe, deno.exe, ffmpeg.exe, ffprobe.exe i folder `_internal`.

## Uruchomienie lokalne, bez GitHub Actions

Wymaga Python 3.12+; w folderze z kodem uruchom:

```powershell
python -m pip install -r requirements.txt
python app.py
```

Zainstaluj `yt-dlp.exe`, `ffmpeg.exe`, `ffprobe.exe`, `deno.exe` w tym samym folderze lub w PATH. Wersja z workflow GitHub Actions dołącza te pliki automatycznie.

## Testy

```powershell
python -m unittest discover -s tests -v
```

Testy nie łączą się z YouTube. Testują walidację adresów, budowanie poleceń, archiwum historii, języki napisów, parsowanie postępu, kontrolę SHA256 i profile Turbo.

## Rozwiązywanie problemów

- **Ostrzeżenie Node.js 20**: workflow 2.0 korzysta z akcji Node.js 24 (`checkout@v6`, `setup-python@v6`, `upload-artifact@v6`).
- **Brak yt-dlp.exe**: uruchom program z całym folderem pobranego artefaktu.
- **Nie ma dźwięku / MP3 / napisy nie działają**: sprawdź czy obok EXE leży `ffmpeg.exe`.
- **Film pobiera się powoli**: przetestuj „Szybki” lub „Turbo”. Nie wszystkie źródła udostępniają fragmenty; 3 równoległe filmy mogą spowolnić każde pobieranie.
- **Błąd 403 / format niedostępny**: najpierw spróbuj **Ustawienia → Sprawdź aktualizację teraz**. Nie wszystkie materiały mogą zostać pobrane.
- **Aktualizacja narzędzia nieudana**: program użyje dołączonego yt-dlp.exe. Spróbuj ponownie przy stabilnym połączeniu.
- **Zatrzymane pobieranie**: fragmenty `.part` mogą zostać wznowione po ponownym dodaniu tego samego URL.
- **Nie ma playlisty**: włącz „Cała playlista” i użyj adresu z `list=`.
- **Brak uprawnień**: wybierz folder zapisu w katalogu użytkownika, np. `Pobrane`.
- **SmartScreen / ostrzeżenie Windows**: niepodpisane EXE może być blokowane. Uruchamiaj wyłącznie pliki, którym ufasz.

## Bezpieczeństwo / licencje

- Kod przeznaczony do pobierania wyłącznie własnych / uprawnionych treści; przestrzegaj warunków YouTube: <https://www.youtube.com/t/terms>.
- Silnik pobierania: <https://github.com/yt-dlp/yt-dlp>.
- Środowisko JS: <https://github.com/denoland/deno>.
- FFmpeg: <https://github.com/BtbN/FFmpeg-Builds> — w tym workflow używamy kompilacji **GPL**, więc przy publicznym redystrybuowaniu należy spełnić obowiązki licencyjne FFmpeg i pozostałych komponentów.
- UI: <https://github.com/TomSchimansky/CustomTkinter>.
- Zapis historii i ustawień jest lokalny w profilu użytkownika, nie wysyłamy historii na serwer.
