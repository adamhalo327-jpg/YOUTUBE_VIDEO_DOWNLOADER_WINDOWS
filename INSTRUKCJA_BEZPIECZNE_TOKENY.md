# YOUTUBE VIDEO DOWNLOADER 12.1 — BEZPIECZNY SKLEP TOKENÓW

## Kolejność wdrożenia (Cloudflare — istniejący Premium Cloud 5.1)

1. **Kopia:** Zachowaj działający `worker.js` Premium Cloud 5.1 i punkt D1 `/bookmark`. Zrób także kopię plików programu 12.0/10.1. Nie zmieniaj `ADMIN_TOKEN` ani `RATE_LIMIT_SALT`.
2. W panelu Cloudflare otwórz **D1 → yvd-premium-db → Console**. Wykonaj polecenia z `cloud_worker/token_shop_12_1_migration.sql` (można je wkleić po jednym). Są to wyłącznie `CREATE TABLE/INDEX IF NOT EXISTS`, bez usuwania istniejących danych.
3. W D1 wykonaj `SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;`. Powinny być m.in. `licenses`, `security_rate_limits`, `admin_audit`, `token_wallets`, `token_sessions`, `token_ledger`, `token_purchases`.
4. Otwórz **Workers & Pages → yvd-premium-cloud → Edit code**, zastąp kod Workera zawartością `cloud_worker/src/worker.js`, kliknij **Deploy**. Zostaw binding `DB` do istniejącej D1. Na Workerze muszą pozostać sekrety `ADMIN_TOKEN` i `RATE_LIMIT_SALT`.
5. Wejdź na `https://TWÓJ-WORKER.workers.dev/health`; oczekiwane `ok: true` i nazwa `YVD Premium Cloud 5.1 + Token Shop 12.1`.
6. W Admin Center sprawdź **Statystyki** i **Lista licencji**. Przetestuj wcześniej aktywowaną licencję, aby potwierdzić zgodność 5.1.
7. Prześlij pełen kod aplikacji do GitHub (z folderami `.github`, `assets`, `cloud_worker`, `tests`). Uruchom **OFFICIAL YOUTUBE VIDEO DOWNLOADER 12.1 - Setup Portable Release** z `publish_release: false`.
8. Zainstaluj nowy Setup.exe lub rozpakuj Portable. W zakładce **Cloud** wpisz adres działającego Workera. Otwórz **Sklep tokenów**, kliknij **Odśwież portfel z chmury**; powinno pojawić się 0 tokenów.
9. Pobierz **własny lub dozwolony** materiał. Oczekuj +10 tokenów po potwierdzeniu serwera. Sprawdź zabezpieczenie przed duplikatem, limity i zakup STARTER po zebraniu 100 tokenów.
10. Dopiero po udanym teście GUI i serwera przygotuj oficjalny GitHub Release 12.1.

## Zasady
- STARTER 100 tokenów / 1 dzień; PRO 500 / 7 dni; ULTRA 1500 / 30 dni.
- 10 tokenów za zgłoszone ukończenie; limit 100/dzień/portfel i 300/dzień/skrót IP; jeden URL raz dziennie/portfel.
- Serwer wymaga wcześniejszego zgłoszenia startu oraz minimum 2 sekund odstępu; nigdy nie przyznaje nagrody z lokalnego pliku.
- Portfel użytkownika to lokalny sekret dostępu `token-wallet-cloud-v12-1.json`. **Traktuj ten plik jak hasło: nie udostępniaj, nie wrzucaj do GitHub.** Zapis nie zawiera salda. Samo skopiowanie sekretu może umożliwić dostęp do portfela.
- Nie migruj automatycznie starego pliku `tokens-v12-1.json` (jego saldo dało się fałszować).
- W razie problemu przywróć poprzedni kod Workera 5.1. **Nie cofaj odruchowo całej D1** — może to usunąć nowe transakcje. Nowe tabele mogą pozostać.

## Ważna granica bezpieczeństwa
Aplikacja nie ma niezależnego, kryptograficznego dowodu pobrania filmu. Osoba modyfikująca klienta może udawać zakończenie zadania oraz zakładać inne portfele. Ten projekt to **wersja beta z księgą transakcji po stronie serwera i limitami**, nie odporny na oszustwa system finansowy. Do publicznego systemu o wartości ekonomicznej potrzebne są konta użytkowników, mechanizmy antyfraudowe, monitoring i testy obciążeniowe.
