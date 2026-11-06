# YOUTUBE VIDEO DOWNLOADER 12.1 — Admin Center: przyznawanie tokenów

## Ważne: bezpieczna kolejność

1. Zachowaj kopię działającego Premium Cloud Worker i bazy D1.
2. Cloudflare Dashboard → D1 → `yvd-premium-db` → Console. Wklej cały plik `cloud_worker/token_admin_grants_12_1_migration.sql`, wykonaj Execute. To tworzy dodatkową tabelę, bez modyfikowania starych.
3. Sprawdź `SELECT name FROM sqlite_master WHERE name='token_admin_grants';`.
4. Cloudflare → Workers & Pages → **dotychczasowy Premium Cloud** (`yvd-premium-cloud`) → Edit code. Wklej nowy kod `cloud_worker/src/worker.js` i Deploy. Nie zmieniaj sekretów `ADMIN_TOKEN` ani `RATE_LIMIT_SALT`, ani D1 binding `DB`.
5. Wgraj nowe pliki aplikacji na GitHub i skompiluj z `.github/workflows/build-12-1.yml`, albo skompiluj Admin Center lokalnie. **Nie publikuj Release, dopóki testy nie przejdą.**
6. W Windows 12.1 zakładka Token Shop → Odśwież portfel → Kopiuj ID portfela. To UUID, NIE sekretny `wallet_token`.
7. Admin Center: HTTPS Workera, ADMIN_TOKEN (wyłącznie w panelu, nie wysyłaj go nikomu), ID portfela → Sprawdź portfel → ilość i powód → Dodaj tokeny, potwierdź.
8. Gracz odświeża portfel, widzi nowe saldo. W Cloudflare wykonaj: `SELECT wallet_id,amount,reason,created_at FROM token_admin_grants ORDER BY created_at DESC LIMIT 10;`.
9. Przetestuj także zakup STARTER z tokenów admina i nieudany zakup przy niewystarczającym saldzie.

### Zabezpieczenia

- Tylko endpoint `/admin/token-grant` z nagłówkiem `Authorization: Bearer ADMIN_TOKEN` może przyznać tokeny.
- Kwota 1–10000, wymagany powód, historia `token_admin_grants` i `admin_audit`.
- Jednorazowy UUID `request_id` chroni przed podwójną realizacją tego samego żądania. Oddzielne żądania mogą przyznawać kolejne tokeny — to celowe uprawnienie administratora.
- Tokeny admina są w **oddzielnej tabeli** i dodawane do salda. Istniejąca tabela `token_ledger` i jej limity pozostają nietknięte.
- To system lojalnościowy beta: klient nie daje niezależnego dowodu ukończenia pobrania. ADMIN_TOKEN musi być tajny.
- Nie edytuj ręcznie `token_ledger`, nie udostępniaj sekretów w repozytorium.

## Uwaga

To projekt źródłowy do wdrożenia. Aktualizacji nie wdrożono automatycznie na Twój serwer ani na GitHub.
