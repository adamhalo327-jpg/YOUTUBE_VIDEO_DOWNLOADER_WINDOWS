# YOUTUBE VIDEO DOWNLOADER 1.0 — Windows

Aplikacja okienkowa do pobierania filmów YouTube, do których masz prawa lub zgodę.

## Funkcje

- Wklejanie adresów zwykłych filmów, Shorts i filmów z adresów `youtu.be`.
- Sprawdzenie tytułu filmu.
- MP4 z wyborem jakości (360p, 480p, 720p, 1080p, 1440p, 2160p, najlepsza dostępna).
- MP3 (ekstrakcja i konwersja dźwięku), wybór folderu, pasek postępu, przerwanie.
- Interfejs po polsku. Pobieranie pojedynczego filmu — bez playlist.

**Uwaga:** dostępne jakości i formaty zależą od konkretnego filmu i YouTube. Wybór 4K
nie tworzy jakości 4K, gdy źródło jej nie udostępnia. Niektóre formaty mogą wymagać
scalenia osobnego dźwięku oraz obrazu. Filmy wymagające logowania, płatne, chronione
lub ograniczone mogą nie działać. Program nie obchodzi DRM.

## Budowa EXE przez GitHub Actions (bez Python i Android Studio na Twoim PC)

1. Utwórz repozytorium na GitHub (może być prywatne), np. `YOUTUBE-VIDEO-DOWNLOADER`.
2. Pobierz ZIP projektu, rozpakuj go i skopiuj **wszystkie pliki i foldery z wnętrza**
   rozpakowanej paczki do głównego katalogu repozytorium. Nie umieszczaj dodatkowego
   folderu nadrzędnego. Zachowaj ukryty katalog `.github` i strukturę poniżej.
3. Prawidłowa struktura repozytorium:

   ```text
   YOUTUBE-VIDEO-DOWNLOADER/
   ├── app.py
   ├── README_PL.md
   ├── tests/
   │   └── test_app.py
   └── .github/
       └── workflows/
           └── build-windows.yml
   ```

4. W GitHub Desktop wybierz **Commit to main** i **Push origin**.
5. Otwórz GitHub → repozytorium → **Actions** → **Build YouTube Downloader EXE** →
   **Run workflow (Uruchom przepływ pracy)**.
6. Po pomyślnym ukończeniu, otwórz to uruchomienie. Na dole w **Artifacts (Artefakty)**
   wybierz `YOUTUBE_VIDEO_DOWNLOADER_WINDOWS`.
7. Rozpakuj pobrany ZIP. Uruchom `YOUTUBE_VIDEO_DOWNLOADER.exe` **z tego folderu**.
   Nie przenoś samego EXE — pliki `yt-dlp.exe`, `ffmpeg.exe`, `ffprobe.exe` i `deno.exe`
   muszą pozostać obok niego. Pierwsze uruchomienie może wymagać zgody Windows
   (plik nie jest podpisany certyfikatem wydawcy).

Workflow w trakcie kompilacji pobiera najnowsze wersje yt-dlp, Deno oraz FFmpeg
z ich oficjalnych repozytoriów, a następnie dodaje je do paczki. Dla samej aplikacji
nie jest wymagane konto YouTube ani żaden klucz API.

## Uruchomienie bez kompilacji

Jeśli masz Python 3.11+ i zainstalowany Tkinter, umieść w folderze obok `app.py`
programy `yt-dlp.exe`, `ffmpeg.exe`, `ffprobe.exe`, `deno.exe` i uruchom:

```powershell
python app.py
```

Lub użyj narzędzi zainstalowanych w PATH.

## Rozwiązywanie problemów

- **Brak pliku yt-dlp.exe**: rozpakuj cały artefakt ZIP, nie samo EXE.
- **Brak MP3**: potrzebny FFmpeg (workflow dodaje go automatycznie).
- **Błąd pobierania 403 / format nie jest dostępny**: YouTube może zmieniać działanie
  serwisu lub nakładać ograniczenia. Spróbuj zaktualizować yt-dlp, uruchamiając
  ponownie workflow. Nie jest zapewnione pobieranie wszystkich materiałów.
- **Pusty folder lub brak dźwięku**: sprawdź, czy pobieranie zakończyło się sukcesem
  i czy w folderze aplikacji jest `ffmpeg.exe`.
- **Nie widzisz Actions**: sprawdź, czy `.github/workflows/build-windows.yml` jest
  w głównym katalogu repozytorium i został wypchnięty na gałąź domyślną.

## Licencje i warunki

Aplikacja jest przykładowym kodem do użytku własnego. Korzysta z osobnych narzędzi
stron trzecich: yt-dlp (Unlicense i licencje zależności), Deno (MIT) i FFmpeg
(w wybranej kompilacji GPL; warunki zależą od builda i jego komponentów).
Przy publicznym udostępnianiu skompilowanego pakietu należy spełnić odpowiednie
warunki licencji i udostępnienia kodu źródłowego FFmpeg oraz innych zależności.
Źródła: https://github.com/yt-dlp/yt-dlp , https://github.com/denoland/deno ,
https://github.com/BtbN/FFmpeg-Builds .

Pobieraj tylko własne filmy, treści udostępnione do pobrania lub materiały, do
których masz stosowne upoważnienie. Pobieranie innych treści może naruszać prawa
oraz warunki YouTube: https://www.youtube.com/t/terms .
