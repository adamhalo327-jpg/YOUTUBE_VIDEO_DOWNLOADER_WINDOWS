# YOUTUBE VIDEO DOWNLOADER 3.0 — PRO EDITION

**Windows 10/11, GitHub Actions EXE.** Pobieraj wyłącznie materiały, do których masz prawa lub zgodę. Narzędzie nie omija DRM. Dostępność jakości, napisów i prędkość zależą od serwisu i materiału; warunki korzystania z YouTube mogą ograniczać pobieranie.

## Funkcje

Wszystko z wersji 2.0: linki do filmów, Shorts i playlist, podgląd miniatury i tytułu, MP4 / MP3, najlepsza jakość, napisy pl,en, historia, aktualizacje silnika yt-dlp zweryfikowane SHA256, praca 1–3 filmów równocześnie, Turbo do 12 fragmentów.

Nowości 3.0: ręczne przesuwanie pozycji ↑ ↓, ponowienie nieudanych zadań, pauza i wznowienie częściowych pobrań, zapisywana po restarcie kolejka, przeszukiwanie historii, motywy ciemny/jasny/neonowy, konwersja MKV/WEBM/WAV, przycinanie od/do, powiadomienia Windows oraz TURBO PRO 16/24 fragmenty i do 5 jednoczesnych filmów.

**Premium z kodem:** darmowa wersja zachowuje funkcje 2.0 plus kolejkę, pauzę, wyszukiwarkę i motywy. Kod Premium odblokowuje Turbo Pro, 4–5 pobrań naraz, przycinanie, nowe formaty MKV/WEBM/WAV oraz powiadomienia Windows.

## Instalacja przez GitHub w przeglądarce

1. Rozpakuj `YOUTUBE_VIDEO_DOWNLOADER_3_0_PRO_GITHUB.zip` na komputerze.
2. Wejdź do swojego repozytorium na https://github.com/adamhalo327-jpg/YOUTUBE_VIDEO_DOWNLOADER_WINDOWS (jeśli nadal używasz tego repozytorium).
3. Zakładka **Code → Add file → Upload files**. Przeciągnij **zawartość** rozpakowanego ZIP, zachowując strukturę folderów. Zatwierdź **Commit changes**. Nie wysyłaj samego ZIP do repozytorium — GitHub go nie rozpakowuje.
4. Jeżeli folder `.github` nie jest przesłany: wejdź w **Add file → Create new file** i jako nazwę wpisz `.github/workflows/build-windows.yml`, a do edytora wklej zawartość pliku z ZIP.
5. Sprawdź obecność: `app.py`, `gui.py`, `core.py`, `licensing.py`, `requirements.txt`, `.github/workflows/build-windows.yml`, `tests/*.py`.
6. W GitHub Actions wybierz **Build YouTube Downloader 3.0 PRO EXE**. Uruchom **Run workflow** (jeśli brak automatycznej kompilacji).
7. Po zielonym **Success** pobierz w sekcji **Artifacts** archiwum `YOUTUBE_VIDEO_DOWNLOADER_3_0_PRO_WINDOWS`. Rozpakuj cały folder i uruchom `YOUTUBE_VIDEO_DOWNLOADER_3_0_PRO.exe`.

**Uwaga:** pliki `yt-dlp.exe`, `ffmpeg.exe`, `ffprobe.exe` i `deno.exe` są pobierane przez workflow, więc nie musisz instalować ręcznie Pythona ani FFmpeg. Nie wyjmuj EXE z folderu z narzędziami i podfolderem `_internal`. Kompilacja wymaga Internetu.

## Aktywacja Premium

Otwórz zakładkę **Premium** → wklej pełny **YVD3-...** → **AKTYWUJ PREMIUM**. Kod ma cyfrowy podpis Ed25519; nie da się tworzyć poprawnych kodów bez klucza prywatnego. Działa offline przy aktywacji, bez logowania. Może mieć datę wygaśnięcia lub być bezterminowy. Kod przechowywany jest lokalnie w `%LOCALAPPDATA%\YouTubeVideoDownloader\premium-license.json`.

**Dla właściciela:** osobno od ZIP otrzymujesz plik `YVD_3_0_WLASCICIEL_KLUCZ_PRYWATNY.pem` oraz pierwszy osobisty kod. Zachowaj PEM prywatnie, nigdy nie wgrywaj go do GitHub ani nie dołączaj do artefaktu EXE. Repozytorium zawiera wyłącznie klucz **publiczny**. Nowe kody można wystawiać na komputerze z Pythonem i pakietem `cryptography`:

```powershell
python -m pip install cryptography
python tools/issue_premium_code.py --key "C:\BezpiecznyFolder\YVD_3_0_WLASCICIEL_KLUCZ_PRYWATNY.pem" --name "Klient" --days 365
```

Użyj `--days 0` dla kodu bezterminowego. Bez osobnego serwera nie ma centralnego cofania kodów ani przypisywania kodu do konkretnego komputera; kod może zostać skopiowany przez odbiorcę.

## Jak korzystać

- **Wznawianie**: kliknij Pauza przy zadaniu, następnie Wznów. Program próbuje użyć `.part` (yt-dlp `--continue --part`). Po ponownym otwarciu programu zadania pozostają w stanie Wstrzymano. Uwaga: nie każde źródło/format pozwala na pobieranie od miejsca przerwania; nie przenoś częściowych plików.
- **Kolejka**: `↑` / `↓` dla pozycji oczekujących, `Wznów` dla wstrzymanych/nieudanych, `Usuń` dla zadań zbędnych.
- **Przycinanie**: wpisz Od i Do jako `MM:SS` albo `HH:MM:SS`, np. Od `01:20`, Do `02:10`. Wymaga FFmpeg i Premium. Przycinanie po klatkach kluczowych lub z wymuszaniem klatek może spowalniać przetwarzanie. Przy playlistach zastosuje taki sam przedział do każdego filmu.
- **Konwersja**: wybierz MKV, WEBM lub WAV w FORMAT. Konwersja do WEBM może być wielokrotnie wolniejsza, ponieważ FFmpeg musi ponownie kodować obraz i dźwięk. MP4 i MP3 pozostają dostępne bez Premium.
- **Turbo Pro**: szybciej tylko, jeśli serwer dostarcza niezależne fragmenty. 24 równoległe fragmenty nie oznaczają 24× większej prędkości i mogą zwiększać obciążenie.
- **Napisy**: opcja pobiera dostępne języki lub automatyczne napisy, jeśli YouTube je udostępnia. Nie dla każdego filmu są napisy.
- **Historia**: tytuł, URL, rodzaj pliku i ścieżka; filtr działa lokalnie, dane nie są wysyłane na serwer aplikacji.
- **Aktualizacje silnika**: w ustawieniach pobierane jest `yt-dlp.exe` z oficjalnego wydania yt-dlp i weryfikowana jest suma SHA256. FFmpeg, Deno i sama aplikacja nie są aktualizowane automatycznie.

## Gdzie przechowywane są dane?

`%LOCALAPPDATA%\YouTubeVideoDownloader\` zawiera historię, ustawienia, zapamiętaną kolejkę, licencję i nowszy zweryfikowany silnik. Twoje pobrane filmy są w folderze wskazanym w programie. Dane z 2.0 zachowują się: ta sama lokalizacja `history.json` i `settings.json`, nowa kolejka trafia do `queue-v3.json`.

## Testy i ograniczenia

Przed budowaniem EXE workflow instaluje biblioteki i uruchamia `python -m unittest discover -s tests -v`. GUI nie działa na maszynie testowej bez ekranu, więc należy także sprawdzić gotowy EXE na Windows. Pliki `yt-dlp`/`FFmpeg` wymagają aktualizacji przy zmianach YouTube. Żadna metoda nie zapewnia pobierania plików z DRM.
