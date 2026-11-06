# YOUTUBE VIDEO DOWNLOADER 13.0 — AUTO UPDATE CENTER 4.0

Projekt Windows 10/11 x64. Zachowano kod 12.1.2: Token Shop, Cloudflare D1, licencje i Admin Center.

Nowości: zakładka AUTO UPDATE 13.0, pełne wersjonowanie, sprawdzanie GitHub Releases,
historia stabilnych wydań, opis zmian, pobieranie instalatora z postępem i anulowaniem,
weryfikacja SHA256, instalacja po potwierdzeniu użytkownika.

**Jak wdrożyć przez przeglądarkę GitHub:**
1. Rozpakuj ZIP. Prześlij pliki w głównym katalogu na gałąź `main`, zachowując foldery.
2. Jeżeli folder `.github` się nie przesłał: utwórz na GitHub plik `.github/workflows/build-13-0.yml`
   i wklej zawartość z paczki.
3. Commit changes.
4. GitHub Actions → OFFICIAL YOUTUBE VIDEO DOWNLOADER 13.0 - Setup Portable Release → Run workflow.
5. `publish_release: false` do czasu testów na Windows.
6. Pobierz artefakty Setup/Portable i przetestuj zakładkę AUTO UPDATE 13.0.
7. Po testach ręcznie opublikuj `v13.0.0` (nigdy nie nadpisuj obecnej 12.1.2).

**Istotne:** pakiet NIE jest podpisany certyfikatem wydawcy; SHA256 nie zastępuje podpisu.
Aktualizator nie wykonuje plików bez zgody użytkownika; GitHub release musi zawierać setup i SHA256.
Wersja Portable pobiera instalator Setup dla przyszłych aktualizacji, ale może wymagać ręcznej instalacji.
Weryfikacja SHA256 chroni spójność pobranego pliku, lecz nie gwarantuje bezpieczeństwa skompromitowanego wydawcy.

Wykonanie testów składni i jednostkowych NIE oznacza przetestowania GUI na Windows.
