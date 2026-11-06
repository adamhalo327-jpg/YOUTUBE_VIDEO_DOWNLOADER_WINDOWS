"""Local media editing with ffmpeg; no shell commands or external uploads."""
from pathlib import Path
import tempfile
import subprocess
import sys
from core import tool, seconds_from_clock

ALLOWED={'.mp4','.mkv','.webm','.mp3','.wav','.mov','.m4a'}
OUTPUTS={'MP4':'.mp4','MKV':'.mkv','WEBM':'.webm','MP3':'.mp3','WAV':'.wav'}

def studio_command(source, destination, kind='MP4', start='', end=''):
    inp,out=Path(source),Path(destination)
    if not inp.is_file() or inp.suffix.lower() not in ALLOWED:
        raise ValueError('Wybierz istniejący plik multimedialny.')
    if inp.resolve()==out.resolve():
        raise ValueError('Nie można nadpisać pliku wejściowego.')
    if kind not in OUTPUTS or out.suffix.lower()!=OUTPUTS[kind]:
        raise ValueError('Nieprawidłowy format pliku wyjściowego.')
    begin=seconds_from_clock(start); finish=seconds_from_clock(end)
    if finish is not None and finish <= (begin or 0):
        raise ValueError('Koniec musi być po początku.')
    ff=tool('ffmpeg.exe') or tool('ffmpeg')
    if not ff:raise FileNotFoundError('Brak ffmpeg.exe w kompletnym folderze programu.')
    cmd=[ff,'-hide_banner','-nostdin','-y']
    if begin is not None:cmd+=['-ss',str(begin)]
    cmd+=['-i',str(inp)]
    if finish is not None:cmd+=['-t',str(finish-(begin or 0))]
    if kind in ('MP3','WAV'):
        cmd+=['-vn','-acodec','libmp3lame' if kind=='MP3' else 'pcm_s16le']
    elif kind=='WEBM':cmd+=['-c:v','libvpx-vp9','-c:a','libopus']
    else:cmd+=['-c:v','libx264','-c:a','aac']
    return cmd+[str(out)]

def run_studio(cmd):
    return subprocess.run(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,
                          text=True,encoding='utf-8',errors='replace',timeout=7200,
                          creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=='win32' else 0)


def concat_mp4(sources, destination):
    """Join compatible MP4 streams losslessly. Input streams must share codec/resolution."""
    files=[Path(v).resolve() for v in sources]
    target=Path(destination).resolve()
    if len(files)<2 or any(not x.is_file() or x.suffix.lower()!='.mp4' for x in files):
        raise ValueError('Wybierz minimum dwa istniejące pliki MP4.')
    if target.suffix.lower()!='.mp4' or target in files:
        raise ValueError('Plik wynikowy musi być nowym plikiem MP4.')
    ff=tool('ffmpeg.exe') or tool('ffmpeg')
    if not ff:raise FileNotFoundError('Brak FFmpeg.')
    with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',suffix='.txt',prefix='yvd-join-',delete=False) as output:
        for source in files:
            escaped=str(source).replace('\\','/').replace("'", "'\\''")
            output.write("file '"+escaped+"'\n")
        list_path=Path(output.name)
    return [ff,'-hide_banner','-nostdin','-y','-f','concat','-safe','0','-i',str(list_path),'-c','copy',str(target)],list_path
