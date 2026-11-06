; YOUTUBE VIDEO DOWNLOADER 12.1 PREMIUM ACCESS
; Per-user installation, no admin rights; includes all PyInstaller bundled files.
#define AppName "YOUTUBE VIDEO DOWNLOADER"
#define AppVersion "12.1"
#define AppExe "YOUTUBE_VIDEO_DOWNLOADER.exe"

[Setup]
AppId={{61B99C23-C0B6-46AE-9DF1-14BF2E4FBAC9}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=YOUTUBE VIDEO DOWNLOADER
DefaultDirName={localappdata}\Programs\YouTube Video Downloader
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64
WizardStyle=modern
Compression=lzma2
SolidCompression=yes
OutputDir=..\release
OutputBaseFilename=YOUTUBE_VIDEO_DOWNLOADER_12_1_SETUP
SetupIconFile=..\assets\YVD_ICON.ico
UninstallDisplayIcon={app}\{#AppExe}
CloseApplications=yes
RestartApplications=no
SetupLogging=yes

[Languages]
Name: "polish"; MessagesFile: "compiler:Languages\Polish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Utwórz skrót na pulpicie"; GroupDescription: "Dodatkowe skróty:"; Flags: unchecked

[Files]
Source: "..\dist\YOUTUBE_VIDEO_DOWNLOADER\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\assets\YVD_ICON.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{userprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"; IconFilename: "{app}\YVD_ICON.ico"
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "Uruchom {#AppName}"; Flags: nowait postinstall skipifsilent

; Do not remove %LOCALAPPDATA%\YouTubeVideoDownloader on uninstall:
; it contains user settings, queue, history and premium license state.
