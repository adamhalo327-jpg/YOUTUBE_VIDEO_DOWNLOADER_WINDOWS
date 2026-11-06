# TOKEN SHOP 12.1 — Cloud Secure Edition

**Portfel i zakupy są w Cloudflare D1** (nie w pliku lokalnym). Wersja lokalna `tokens-v12-1.json` nie jest importowana: była edytowalna i nie można bezpiecznie uznać jej salda.

## Ceny
- STARTER: 100 tokenów / 1 dzień
- PRO: 500 tokenów / 7 dni
- ULTRA: 1500 tokenów / 30 dni
- Nagroda: 10 tokenów za zgłoszone ukończone pobranie, maksymalnie 100 dziennie / portfel oraz 300 / adres sieciowy (hash IP). Ten sam URL: raz na dzień / portfel.

## Bezpieczeństwo i ograniczenia
Serwer nalicza punkty i księguje zakupy w D1. Identyfikator portfela jest tokenem dostępu przechowywanym lokalnie; nie zawiera salda. Nie można sobie dopisać tokenów przez edycję JSON. Stare licencje 5.0/5.1 nadal działają.

**Ograniczenie:** niezaufany klient nie jest w stanie udowodnić, że pobrał film; atakujący może zgłaszać fałszywe ukończenia i tworzyć dodatkowe portfele. Limity i idempotencja ograniczają, ale nie eliminują nadużyć. Nie traktuj tokenów jako pieniędzy, nie sprzedawaj ich ani nie używaj w niezabezpieczonym programie lojalnościowym. Produkcyjne rozwiązanie wymaga kont użytkowników, dodatkowej weryfikacji oraz monitoringu nadużyć.

## Wdrożenie
1. Zrób kopię Workera 5.1 i zapisz bookmark D1.
2. Wykonaj `cloud_worker/token_shop_12_1_migration.sql` w istniejącej bazie `yvd-premium-db`. Nie usuwaj tabeli `licenses`.
3. Podmień kod Workera Premium Cloud 5.1 zawartością `cloud_worker/src/worker.js` (zachowaj `DB`, `ADMIN_TOKEN`, `RATE_LIMIT_SALT`).
4. Sprawdź `/health`, `/admin/stats`, dotychczasową licencję Premium Cloud.
5. Zbuduj aplikację Windows przez `.github/workflows/build-12-1.yml` z `publish_release: false`. W zakładce Cloud ustaw adres Workera.
6. Sprawdź nowy portfel, zakończ pobranie i kup pakiet.

Jeśli Worker zostanie cofnięty do 5.1, stare licencje działają, a sklep tokenów czasowo staje się niedostępny.
