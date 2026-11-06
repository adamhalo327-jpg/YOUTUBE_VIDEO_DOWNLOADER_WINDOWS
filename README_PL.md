# YOUTUBE VIDEO DOWNLOADER 4.1 — ULTIMATE EDITION

Zachowano działającą bazę 4.0: MP4/MP3, playlisty, podgląd, napisy, kolejkę,
wznawianie, przycinanie, konwersję, Premium, licznik, Portable i Setup.exe.

## Nowe w 4.1

- Zakładka **Statystyki**: liczba wpisów, istniejące rozmiary plików i formaty.
- **Ustawienia > Aktualizacje aplikacji**: automatyczne sprawdzanie oficjalnego wydania GitHub Releases po uruchomieniu; ręczne sprawdzanie i przycisk otwierający oficjalną stronę wydania. Ze względów bezpieczeństwa nie uruchamia niezweryfikowanych pobranych instalatorów automatycznie. Właściciel musi najpierw opublikować nowe wydanie GitHub Release.
- **Panel właściciela**: lokalny rejestr wystawionych kodów i eksport CSV, z datami i odciskiem kodu, bez zapisywania samego kodu. Nie jest to panel aktywacji z innych urządzeń: taki wymaga osobnej usługi online.
- Zachowano nazwę paska Windows: **YOUTUBE VIDEO DOWNLOADER**.

## Instalacja / GitHub

Prześlij całą zawartość ZIP do głównego folderu repozytorium, zachowując foldery
`.github/workflows`, `tools`, `installer`, `tests`. W zakładce Actions wybierz
**Build YOUTUBE VIDEO DOWNLOADER 4.1 - Portable + Setup**. Użyj **Run workflow**.
Po zakończeniu pobierz `YVD_4_1_PORTABLE_WINDOWS`, `YVD_4_1_INSTALLER_WINDOWS`
lub `YVD_4_1_PREMIUM_OWNER_WINDOWS`.

Uwaga: jeśli w repo jest starszy workflow `build-4-0.yml`, jego uruchomienie nadal
będzie budować starą wersję. Nowy workflow: `.github/workflows/build-windows.yml`.

Nie publikuj prywatnego pliku PEM ani kodów Premium w repozytorium.
Pobieraj wyłącznie materiały, do których masz prawa.
