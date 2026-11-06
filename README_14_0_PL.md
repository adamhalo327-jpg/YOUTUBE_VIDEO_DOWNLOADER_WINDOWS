# YOUTUBE VIDEO DOWNLOADER 14.0 — TOKEN SHOP: MISJE I PAKIETY

## Co nowego
- PLUS: 250 tokenów / 3 dni Premium.
- LEGEND: 3000 tokenów / 90 dni Premium.
- STARTER / PRO / ULTRA bez zmian.
- Misja dzienna: 3 prawidłowo nagrodzone pobrania w dobie UTC = +20 tokenów.
- Misja tygodniowa: 15 prawidłowo nagrodzonych pobrań od poniedziałku UTC = +80 tokenów.
- Serwer kontroluje postęp; odbiór nagrody ma ograniczenie jeden raz na okres.
- Saldo, portfel, historia starszych zakupów i PREMIUM CLOUD są zachowane.

## KRYTYCZNA KOLEJNOŚĆ WDROŻENIA
1. Zrób kopię zapasową bazy D1 yvd-premium-db.
2. Otwórz Cloudflare > D1 > yvd-premium-db > Console i uruchom `cloud_worker/token_shop_14_0_migration.sql`.
3. W Cloudflare Workers edytuj TYLKO worker `yvd-premium-cloud` i podmień jego skrypt na `cloud_worker/src/worker.js`. Nie zmieniaj `ADMIN_TOKEN`, DB ani domeny.
4. Przetestuj /health (GET), saldo portfela i stare pakiety, zanim zbudujesz aplikację.
5. Wgraj kod aplikacji do repozytorium GitHub z zachowaniem folderów. Workflow `.github/workflows/build-14-0.yml` tworzy Setup/Portable.
6. Po kompilacji przetestuj 14.0 na Windows przed wydaniem i publikacją strony.

**Nie wykonuj aktualizacji Workera przed migracją D1.** Jeśli nie masz backupu D1, nie wdrażaj aktualizacji.

## Ograniczenia bezpieczeństwa
Nagrody bazują na istniejących wpisach token_ledger (`kind=reward`), a te opierają się na sygnale niezweryfikowanego klienta. Nie jest to system kryptograficznie odporny na fałszywe pobrania.
