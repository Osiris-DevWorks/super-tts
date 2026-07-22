; Inno Setup script for Super TTS.
;
; Single source of truth for the version number is VERSION.TXT at the repo
; root. Update that file (or run scripts\build\build_exe.py --increment ...)
; and re-run the build — every version-stamped field below is derived from it.
#define VersionFile FileOpen(AddBackslash(SourcePath) + "VERSION.TXT")
#define AppVer Trim(FileRead(VersionFile))
#expr FileClose(VersionFile)
#undef VersionFile

; Note: this installer intentionally does NOT prompt for the Discord token
; or the database URL. Configuration happens entirely inside the GUI's
; Settings tab on first launch — it's the one place users set credentials.
; The bundled DEFAULT_DATABASE_URL the GUI pre-fills lives in
; gui/settings.py (as DEFAULT_DATABASE_URL); rotate it by rebuilding and
; redistributing the installer.

[Setup]
; Generated GUID — do NOT reuse one from a sibling project. Inno uses this
; to identify the app for upgrade detection in the registry.
AppId={{F7A4D9C1-3B6E-4A2D-9C5F-8E1B7D0A2F4C}
AppName=Super TTS
AppVersion={#AppVer}
AppPublisher=Osiris DevWorks, LLC
DefaultDirName={localappdata}\Osiris DevWorks\Super TTS
DefaultGroupName=Super TTS
OutputDir=dist
OutputBaseFilename=Super-TTS-{#AppVer}-Setup
Compression=lzma
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
; lowest = no admin prompt, since {localappdata} is user-writable.
PrivilegesRequired=lowest
; Optional icon — bundle one at assets\super-tts.ico to enable.
;SetupIconFile=assets\super-tts.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[InstallDelete]
; Wipe the install dir before laying down the new build to avoid leftover
; files from a prior version. The user's .env (in %APPDATA%) and the
; downloaded Supertonic model cache (in %USERPROFILE%\.cache) are NOT under
; {app}, so they survive untouched across upgrades.
Type: filesandordirs; Name: "{app}\*"

[Files]
Source: "dist\Super-TTS-v{#AppVer}\*"; DestDir: "{app}"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Super TTS"; Filename: "{app}\Super-TTS-v{#AppVer}.exe"
Name: "{group}\{cm:UninstallProgram,Super TTS}"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\Super-TTS-v{#AppVer}.exe"; \
    Description: "Launch Super TTS"; \
    Flags: nowait postinstall skipifsilent
