# YOUTUBE VIDEO DOWNLOADER 10.1 — nowa oficjalna ikona

Oficjalna ikona **bez numeru 10.1 i bez napisu PREMIUM ACCESS**.

## Co zostało zmienione
- `assets/YVD_ICON.png`: podgląd PNG z przezroczystym tłem.
- `assets/YVD_ICON.ico`: wielorozdzielcza ikona Windows (16–256 px).
- `gui.py`: ustawia ikonę okna aplikacji.
- `.github/workflows/build-10-1.yml`: `PyInstaller --icon` dla EXE oraz `--add-data` dla GUI.
- `installer/YOUTUBE_VIDEO_DOWNLOADER.iss`: ikona instalatora Setup i skrótów.
- Workflow generuje podczas budowy plik ISS zgodny z wersją 10.1 i z tą ikoną.

## Jak wdrożyć
1. Rozpakuj cały ZIP i umieść pliki w repozytorium GitHub w tych samych folderach (szczególnie `.github/workflows` i `assets`).
2. W zakładce Actions uruchom `Build YOUTUBE VIDEO DOWNLOADER 10.1 - Portable + Setup + Admin`.
3. Po Success pobierz artefakty `YVD_10_1_INSTALLER_WINDOWS` i `YVD_10_1_PORTABLE_WINDOWS`.
4. Zainstaluj ponownie Setup.exe. Jeśli Windows pokazuje starą ikonę, odśwież skrót lub uruchom ponownie Eksplorator Windows.

Wersja Premium Access i pozostałe funkcje pobierania są zachowane. Ikona nie zawiera numeru ani oznaczenia Premium.
