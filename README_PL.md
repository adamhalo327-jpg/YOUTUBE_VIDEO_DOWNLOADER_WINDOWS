# YOUTUBE VIDEO DOWNLOADER 5.0 — INFINITY EDITION

Kompletny projekt Windows. Rozszerza wersję 4.1. **Przy pobieraniu używaj materiałów, do których masz prawa lub zezwolenie.** Nie obchodzi DRM.

## Co zawiera 5.0?

- **Turbo Infinity:** profil `Infinity Auto` dostosowuje 8 / 16 / 32 równoległych fragmentów do ostatnich pomiarów prędkości. Premium. Nie gwarantuje przyspieszenia każdego źródła.
- **Admin Center 5.0:** osobny Windows EXE do wydawania, przedłużania, przeglądania i unieważniania **kodów Cloud YVD5**. Wymaga wdrożonego Worker + D1 i sekretu administratora. Działa tylko online.
- **Premium Cloud:** opcjonalne licencje online YVD5, identyfikator urządzenia, ważność weryfikowana na serwerze. Stare podpisane kody **YVD3** nadal są sprawdzane lokalnie bez zmian, z dotychczasowym licznikiem. Nie dołączono prywatnego klucza do ZIP.
- **Smart Playlists:** podgląd do 200 pozycji, wybór numerów `1,3,5-10`, opcjonalne pomijanie wcześniej pobranych pozycji dla tego folderu i formatu.
- **Video Studio:** konwersja i przycinanie lokalnych materiałów przez FFmpeg. Łączenie MP4 metodą `-c copy` (pliki muszą mieć zgodne kodeki/parametry).
- **Harmonogram:** opóźnia rozpoczęcie dodanych zadań do lokalnego czasu `RRRR-MM-DD GG:MM`, działa gdy aplikacja jest uruchomiona. Nie budzi zamkniętego komputera.
- **Live Statistics:** bieżąca szacowana średnia MiB/s na podstawie komunikatów yt-dlp oraz liczniki i historia lokalna.
- **Infinity UI:** ciemny styl wersji 4.1 z dodatkowymi zakładkami. Pasek systemowy: wyłącznie `YOUTUBE VIDEO DOWNLOADER`.
- **Auto Update 2.0:** program sprawdza wydania GitHub; można pobrać nowy Setup.exe po potwierdzeniu, jeśli w Release opublikowano także `YVD_SETUP_SHA256.txt`. Program porównuje SHA256 i NIE uruchamia instalatora sam. Przy braku sumy udostępnia oficjalną stronę wydania.
- **Windows Installer 5.0:** Portable ZIP + per-user Setup.exe (Inno Setup), osobne EXE paneli.

Wszystkie funkcje 4.1 (MP4/MP3, kolejka, pauza, historia, napisy, konwersje, motywy, Premium offline, panel generatora) zachowane na poziomie źródeł. Zapisy użytkownika pozostają w `%LOCALAPPDATA%\YouTubeVideoDownloader`.

## GitHub w przeglądarce — kompilacja Windows

1. ZACHOWAJ kopię działającej wersji 4.1. Pobierz i rozpakuj ZIP 5.0.
2. Otwórz `https://github.com/adamhalo327-jpg/YOUTUBE_VIDEO_DOWNLOADER_WINDOWS` → **Code → Add file → Upload files** i prześlij zawartość rozpakowanego folderu, nie ZIP.
3. Ponieważ przeglądarka GitHub może nie przesłać ukrytego `.github`, osobno wybierz **Add file → Create new file**, nazwij `.github/workflows/build-5-0.yml`, wklej zawartość pliku z ZIP i **Commit changes** na `main`.
4. Otwórz **Actions → Build YOUTUBE VIDEO DOWNLOADER 5.0 - Portable + Setup + Admin → Run workflow**. Nie używaj "Re-run" starej kompilacji.
5. Po **Success** pobierz artefakty:
   - `YVD_5_0_PORTABLE_WINDOWS` → kompletny folder aplikacji z `_internal` i narzędziami.
   - `YVD_5_0_INSTALLER_WINDOWS` → `YOUTUBE_VIDEO_DOWNLOADER_5_0_SETUP.exe` + `YVD_SETUP_SHA256.txt`.
   - `YVD_5_0_PREMIUM_OWNER_WINDOWS` → stary offline generator YVD3.
   - `YVD_5_0_ADMIN_CENTER_WINDOWS` → nowy online admin YVD5.
6. Instalator Setup.exe jest tworzony w GitHub Actions, nie znajduje się w ZIP źródłowym. Workflow sam generuje `.iss` (nie musisz tworzyć folderu `installer` ręcznie).

Jeżeli w repozytorium pozostają stare workflow 4.1, mogą kompilować się równolegle po push. Nie wpływa to na nowy workflow 5.0, ale można je wyłączyć ręcznie.

## Premium Cloud — WDROŻENIE NIE JEST AUTOMATYCZNE

Cloud jest **opcjonalny i nie działa bez wdrożenia**. W katalogu `cloud_worker` znajduje się kod serwera Cloudflare Workers i schemat D1.

1. Zaloguj się do Cloudflare, utwórz bazę **D1** `yvd-premium-db`.
2. Wykonaj SQL z `cloud_worker/schema.sql` na bazie D1.
3. Utwórz Worker i wgraj zawartość `cloud_worker/src/worker.js` (moduł ES).
4. W ustawieniach Workera dodaj binding **D1** o nazwie dokładnie `DB` wskazujący na bazę.
5. Dodaj **sekret** `ADMIN_TOKEN`, mocny losowy token (co najmniej 32 znaki), jako **Worker Secret**, NIE jako zmienną w plikach źródłowych, NIE jako GitHub Secret repozytorium. Nigdy nie umieszczaj go w kodzie aplikacji klienta.
6. Wdróż Worker na `https://...workers.dev`. Endpoint `/health` powinien zwrócić JSON `ok:true`.
7. Uruchom `YVD_ADMIN_CENTER.exe`, wpisz adres Workera HTTPS i sekret, generuj kody YVD5. W aplikacji użytkownika otwórz kartę `Cloud`, wpisz adres HTTPS oraz kod YVD5.

Worker pozwala na jeden zapisany identyfikator urządzenia na kod, wspiera cofnięcie ważności, przedłużenie i listę bez pełnych kodów. Wymaga bezpiecznego przechowywania sekretu i dodatkowych limitów żądań w Cloudflare przed publicznym udostępnieniem. **To nie jest rozwiązanie odporne na modyfikowanie klienta lub identyfikatora urządzenia przez zaawansowanego użytkownika.**

Aktualne aktywacje Cloud wymagają połączenia z serwerem. Brak internetu/serwera blokuje online Premium; stare lokalne podpisane licencje działają nadal.

## Auto Update 2.0 / GitHub Releases

Do nowego GitHub Release (np. tag `v5.1.0`) dodaj oba pliki z artefaktu instalatora: `YOUTUBE_VIDEO_DOWNLOADER_5_1_SETUP.exe` i `YVD_SETUP_SHA256.txt` z linią `SHA256  nazwa_pliku`. Nazwa musi zgadzać się z nazwą pliku EXE. Wtedy program pobierze instalator do `%LOCALAPPDATA%\YouTubeVideoDownloader\updates`, porówna SHA256 i otworzy jego folder. Uruchomienie i instalacja są ręczne. Wersja 5.0 sama nie tworzy publikacji GitHub Release.

## Bezpieczeństwo i ograniczenia

- Żaden prywatny klucz PEM ani sekret administratora nie trafia do ZIP / programu.
- Plik z kodem Cloud/tokenem znajduje się lokalnie w koncie Windows. Publiczne urządzenia wymagają dodatkowej ochrony konta.
- Nie testowano jeszcze kompilacji na prawdziwym Windows ani działania z realnym YouTube / Worker D1. Testy automatyczne są jednostkowe.
- Instalator nie jest podpisany certyfikatem wydawcy; Windows SmartScreen może ostrzegać.
- Prawa do filmów i warunki platformy nadal obowiązują.
