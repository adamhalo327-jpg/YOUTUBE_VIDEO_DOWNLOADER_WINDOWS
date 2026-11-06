# YOUTUBE VIDEO DOWNLOADER 4.0 — ULTIMATE EDITION

**Aktualizacja 13: Windows Portable + instalator Setup.exe.** Zachowuje funkcje wersji 3.1.1, ciemny wyglad, zakladki, Premium i licznik waznosci, historie i kolejke, narzedzia yt-dlp/FFmpeg/Deno, MP4/MP3, playlisty, napisy, Turbo Pro i konwersje. W pasku tytulu Windows jest wylacznie **YOUTUBE VIDEO DOWNLOADER**. W aplikacji widnieje **ULTIMATE EDITION 4.0**.

## Dwie wersje Windows

- **Portable ZIP**: `YOUTUBE_VIDEO_DOWNLOADER_4_0_PORTABLE.zip`. Rozpakuj **caly folder** `YOUTUBE_VIDEO_DOWNLOADER`; uruchom w nim `YOUTUBE_VIDEO_DOWNLOADER.exe`. Nie przenos samego EXE — obok musi byc `_internal` i narzedzia `.exe`. Nie wymaga instalowania Pythona i nie wprowadza instalatora.
- **Installer**: `YOUTUBE_VIDEO_DOWNLOADER_4_0_SETUP.exe`. Zainstaluj bez uprawnien administratora do `%LOCALAPPDATA%\Programs\YouTube Video Downloader`. Instalator tworzy skrot w menu Start, opcjonalnie skrot na Pulpicie, wpis do odinstalowania w Windows. Przy pierwszej instalacji uruchom `Setup.exe`; przy kolejnej mozesz zainstalowac 4.0 ponownie w tym samym katalogu.

**Wersje sa funkcjonalnie takie same.** Portable nie oznacza przenoszenia danych konta: tak jak w 3.1.1 historia, kolejka, ustawienia i Premium pozostaja w `%LOCALAPPDATA%\YouTubeVideoDownloader`. To zapewnia zachowanie stanu przy aktualizacji i przelaczaniu Portable/Installer. Przy odinstalowaniu dane uzytkownika pozostaja na dysku.

## Aktualizacja przez GitHub w przegladarce

1. Zachowaj kopie poprzedniej, dzialajacej wersji 3.1.1. Nie zamieniaj prywatnego klucza Premium.
2. Rozpakuj ZIP z kodem 4.0 na komputerze. Na GitHub `https://github.com/adamhalo327-jpg/YOUTUBE_VIDEO_DOWNLOADER_WINDOWS` → **Code → Add file → Upload files**. Przeslij zawartosc ZIP, zachowujac strukture katalogow (`installer/`, `tools/`, `tests/`).
3. Jesli ukryty `.github` nie pojawi sie podczas przesylania, otworz `.github/workflows/build-windows.yml` w GitHub i wklej zawartosc odpowiedniego pliku z ZIP. Nie wklejaj samego ZIP do repozytorium.
4. Wykonaj **Commit changes**. W **Actions** wybierz `Build YOUTUBE VIDEO DOWNLOADER 4.0 - Portable + Setup`, a nastepnie **Run workflow**, jesli kompilacja nie wystartowala automatycznie.
5. Po **Success** otworz uruchomienie i pobierz **Artifacts**:
   - `YVD_4_0_PORTABLE_WINDOWS` — wewnatrz jest ZIP Portable,
   - `YVD_4_0_INSTALLER_WINDOWS` — wewnatrz jest `YOUTUBE_VIDEO_DOWNLOADER_4_0_SETUP.exe`,
   - `YVD_4_0_PREMIUM_OWNER_WINDOWS` — osobny `YVD_PREMIUM_OWNER.exe` do generowania kodow.
6. GitHub pakuje artefakt jako wlasny ZIP, dlatego po pobraniu artefaktu Portable rozpakuj **zewnetrzny ZIP**, a nastepnie **wewnetrzny ZIP Portable**.

## Uwaga o Premium i prywatnym kluczu

Uzywamy tego samego klucza publicznego w `licensing.py`, co w 3.1.1 — istniejace kody nadal sa sprawdzane. Wersja 4.0 nie ma nowego formatu kodow ani nowych ograniczen Premium. Panel `YVD_PREMIUM_OWNER.exe` jest osobny; generowanie kodow wymaga wskazania istniejacego, prywatnego klucza PEM na swoim komputerze. **NIE przesylaj pliku PEM do GitHub ani nie umieszczaj go w dystrybucji.**

## Przyczyny typowych problemow

- `Failed to load Python DLL python312.dll` — nie uruchamiaj EXE bez `_internal`, rozpakuj cala paczke; w razie potrzeby sprawdz biblioteki Visual C++ Runtime oraz antywirusa.
- `Script file tools/premium_generator_gui.py does not exist` — folder `tools/` nie zostal przeslany do repozytorium, musi zawierac `premium_generator_gui.py` i `issue_premium_code.py`.
- `No event triggers defined in on` — sprawdz dokladna sekcje `on:` w `.github/workflows/build-windows.yml`. Nie zamieniaj jej na tekst z cudzyslowami ani nie usuwaj wciec w dalszej czesci YAML.
- Ostrzezenie Windows SmartScreen o nieznanym wydawcy moze sie pojawic: pliki nie sa podpisane certyfikatem Authenticode. Nie wyłączaj ochrony systemu; sprawdz pobrany artefakt i źrodło.

## Licencje narzedzi

Zobacz `THIRD_PARTY_NOTICES.md`. Pobieraj tylko filmy, do ktorych masz prawa lub pozwolenie i przestrzegaj warunkow YouTube.

## Testy

`python -m unittest discover -s tests -v` — testy rdzenia, Premium i dystrybucji. Testy bez Windows nie potwierdzaja udanej kompilacji instalatora, dzialania GUI ani uruchamiania pobierania. Te czynnosci trzeba sprawdzic po zbudowaniu na GitHub Actions.
