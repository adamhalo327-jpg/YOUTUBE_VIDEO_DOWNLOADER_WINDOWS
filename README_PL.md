# YOUTUBE VIDEO DOWNLOADER 12.0 — UNIVERSAL DOWNLOADER

## Nowości
- Nowa zakładka **Universal 12.0** (17 grup platform) z automatycznym rozpoznawaniem serwisu.
- Obsługa YouTube/Shorts, TikTok, Instagram/Reels, Facebook, Twitch, Vimeo, Dailymotion, X/Twitter, Reddit, SoundCloud, Bandcamp, Mixcloud, Internet Archive, wybranych instancji PeerTube, Rumble, Kick, Pinterest.
- MP4, MKV, WebM oraz MP3, M4A, FLAC, WAV, Opus; jakość od 360p do 8K jeśli źródło ją udostępnia.
- Podgląd metadanych, miniatury i napisy, wybrane fragmenty, kolekcje/playlisty; przycisk Anuluj.
- Ochrona FREE/PREMIUM: FREE jeden MP4 do 1080p lub MP3, pozostałe opcje wymagają aktywnej licencji.

Zachowano zakładki i funkcje wersji 10.1, aktywację Premium Cloud 5.1, narzędzia administracyjne, ikonę oraz instalator Windows.

## Wdrożenie
1. Rozpakuj cały projekt, skopiuj pliki do głównego folderu repozytorium GitHub, zachowując ścieżki `assets/YVD_ICON.ico` i `.github/workflows/build-12-0.yml`.
2. Na GitHub: Actions → Build YOUTUBE VIDEO DOWNLOADER 12.0 → Run workflow → main.
3. Pobierz artefakty YVD_12_0_INSTALLER_WINDOWS i YVD_12_0_PORTABLE_WINDOWS.
4. Zainstaluj i przetestuj działanie na Windows przed publikacją GitHub Release.

Serwisy mogą zmieniać API, nie każdy materiał jest dostępny; część funkcji wymaga ffmpeg i aktualnego yt-dlp. Wspieramy pobieranie wyłącznie treści własnych lub dozwolonych, bez obchodzenia DRM. Do nowych serwisów nie udostępniamy importu cookies, aby chronić dane logowania.


## Bezpieczny sklep tokenów 12.1
Najpierw wdróż migrację D1 i nowego Workera zgodnie z `INSTRUKCJA_BEZPIECZNE_TOKENY.md`. Dotychczasowe kody Premium Cloud pozostają zgodne. Lokalny portfel tokenów nie przyznaje uprawnień.
