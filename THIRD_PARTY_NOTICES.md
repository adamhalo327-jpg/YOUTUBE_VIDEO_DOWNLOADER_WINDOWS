# Uzyte narzedzia zewnetrzne

Ta aplikacja jest osobnym frontendem. W procesie GitHub Actions pobierane sa:

- **yt-dlp.exe**: https://github.com/yt-dlp/yt-dlp — Unlicense; kompilator pobiera aktualne oficjalne wydanie i sprawdza SHA256 wg pliku opublikowanego wraz z tym wydaniem.
- **FFmpeg/ffprobe**: https://github.com/BtbN/FFmpeg-Builds — wariant LGPL. Zaleznosci, licencje i wymagania redystrybucji: https://ffmpeg.org/legal.html. Nie modyfikujemy binariow. W przypadku dystrybucji nalezy sprawdzic warunki/licencje w zaleznosci od konkretnej wersji.
- **Deno**: https://github.com/denoland/deno — MIT.
- **Python i biblioteki GUI**: oddzielne licencje dostepne w repozytoriach pakietow.
- **Inno Setup**: https://jrsoftware.org/isinfo.php — sluzy tylko do budowania instalatora, nie jest dolaczany jako program.

Dostepnosc pobierania materialow i mozliwosc ich zapisu zalezy od uprawnien do danego utworu, warunkow platformy i prawa.
