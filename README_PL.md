# YOUTUBE VIDEO DOWNLOADER 10.1 — PREMIUM ACCESS

Windows 10/11 x64. Aktualizacja 10.0 z dotychczasowym GUI i katalogiem danych użytkownika.

## Wersja darmowa
- Jeden film naraz, MP4 do 1080p lub MP3.
- Podgląd, historia pobrań, kopie ustawień/danych, podstawowe statystyki.
- Motyw ciemny.

## Premium
- Wyższa jakość, 4K/8K (jeśli źródło zapewnia).
- Do 10 jednoczesnych pobrań, Turbo Infinity, playlisty i Smart Playlists.
- Video Studio, harmonogram, konwersja, zaawansowane tryby i motywy.
- Podpisane licencje YVD3- zachowują datę ważności i licznik czasu; kody bezterminowe nadal działają.
- Cloud Premium wymaga własnego serwera Cloudflare Worker + D1.

Funkcje wymagające Premium są blokowane przy wykonaniu, a nie tylko w GUI. Zadania Premium wstrzymane po wygaśnięciu można wznowić po odnowieniu. Działające procesy mogą dokończyć aktualny plik.

## GitHub w przeglądarce
1. Rozpakuj ZIP, skopiuj wszystkie pliki źródłowe do repozytorium, zachowując foldery.
2. W gałęzi main utwórz `.github/workflows/build-10-1.yml` z identyczną zawartością jak plik w ZIP.
3. Przejdź do Actions i uruchom `Build YOUTUBE VIDEO DOWNLOADER 10.1 - Portable + Setup + Admin`.
4. Po Success pobierz ZIP Portable lub Setup.exe oraz opcjonalnie panele administratora.

Ważne: nie dodawaj do GitHub prywatnego klucza PEM ani tajnego tokenu serwera. Używaj tylko pobrań, do których masz prawo.

Stan: przetestowano kod lokalnie; kompilacja Windows wymaga uruchomienia na GitHub Actions.
