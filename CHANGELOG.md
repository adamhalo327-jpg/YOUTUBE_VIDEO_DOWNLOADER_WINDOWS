# 12.1 TOKEN SHOP
- Trzy pakiety kupowane za tokeny z pobierania.
- Dzienny limit 100 tokenów, antyduplikacja URL, portfel lokalny.
- Zachowanie funkcji 12.0 i Premium Cloud.

# 12.0 — UNIVERSAL DOWNLOADER
- Nowy moduł universal_downloader.py i zakładka Universal 12.0.
- 17 grup platform, 8 formatów, podgląd, opcje napisów i przycinania.
- Oddzielne żądania yt-dlp, bez wykonywania poleceń przez powłokę.
- Osobny proces pobierania, anulowanie, log i aktualny status.
- Zachowanie danych 10.1, kluczy i Premium Cloud; oryginalny tryb YouTube bez zmian.
- Nowy GitHub Actions build-12-0.yml z ikoną YVD_ICON.ico.

## 12.1 SECURE TOKEN SHOP
- D1 authoritatively stores token balances and purchases; no local minting.
- One-time download tickets, caps and idempotent debits, expiry on server.
- Cloudflare Worker 5.1 endpoints unchanged, new /wallet/* endpoints.
