"""Entry point for the Windows desktop app.
The download-command helpers are importable without GUI dependencies so old tests work.
"""
from core import (
    make_download_command as _make_download_command,
    tool,
    valid_video_url,
    valid_youtube_url,
    yt_base_command as _yt_base_command,
)


def yt_base_command():
    return _yt_base_command()


def make_download_command(url, dest, kind, quality, **kwargs):
    return _make_download_command(url, dest, kind, quality, _tool=tool,
                                  _base_command=yt_base_command, **kwargs)


def main():
    from gui import UltraDownloader
    UltraDownloader().mainloop()


if __name__ == "__main__":
    main()
