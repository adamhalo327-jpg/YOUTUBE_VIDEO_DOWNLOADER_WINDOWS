# YOUTUBE VIDEO DOWNLOADER 10.1 — OFFICIAL UPDATE

Ta paczka zawiera **pelny projekt 10.1** z oficjalna ikona i workflow, ktory
naprawia brak `assets/YVD_ICON.ico` AUTOMATYCZNIE podczas GitHub Actions.
Nie musisz osobno tworzyc folderu `assets` w repozytorium.

## NAJPROSTSZA NAPRAWA W PRZEGLADARCE (tylko jeden plik)
1. Rozpakuj ZIP na komputerze.
2. Otworz repozytorium -> Code -> `.github/workflows/build-10-1.yml`.
3. Kliknij ikone olowka (Edit this file), zaznacz caly stary kod (`Ctrl+A`).
4. Wklej caly kod z `.github/workflows/build-10-1.yml` z tej paczki.
5. Commit changes na `main`.
6. Actions -> `OFFICIAL YOUTUBE VIDEO DOWNLOADER 10.1 - Setup Portable Release`.
7. Run workflow -> main -> `publish_release: false` -> Run workflow.
8. Gdy zielony Success: w Summary pobierz artefakty
   `YVD_10_1_INSTALLER_WINDOWS` oraz `YVD_10_1_PORTABLE_WINDOWS`.

## PUBLIKACJA OFICJALNEGO WYDANIA
Dopiero po sprawdzeniu Setup.exe i Portable uruchom workflow ponownie,
wybierajac `publish_release: true`.
Wtedy po poprawnej kompilacji zostanie utworzone GitHub Release `v10.1.0`.
Publicznosc wydania zalezy od ustawien repozytorium (Public/Private).
Jesli tag v10.1.0 istnieje, workflow przerwie publikacje zamiast nadpisac wydanie.

## UWAGA
- W repo musza juz istniec pliki zrodlowe 10.1: `app.py`, `gui.py`, `core.py` itd.
  Jesli ich brakuje, dodaj caly projekt przez GitHub Desktop.
- Zatwierdzona ikona (bez napisow 10.1 i PREMIUM ACCESS) jest dolaczona do ZIP.
- Przy brakujacym pliku assets/YVD_ICON.ico workflow sam odtworzy ikone
  z osadzonego, pomniejszonego wariantu zatwierdzonej grafiki.
- Nie dodawaj prywatnych kluczy ani ADMIN_TOKEN do GitHub.
- Aktywacja Premium Cloud wymaga dzialajacego serwera Cloudflare.
