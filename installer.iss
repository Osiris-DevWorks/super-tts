; Inno Setup script for Super TTS.
;
; Single source of truth for the version number is VERSION.TXT at the repo
; root. Update that file (or run scripts\build\build_exe.py --increment ...)
; and re-run the build — every version-stamped field below is derived from it.
#define VersionFile FileOpen(AddBackslash(SourcePath) + "VERSION.TXT")
#define AppVer Trim(FileRead(VersionFile))
#expr FileClose(VersionFile)
#undef VersionFile

; Railway public proxy URL for the shared PostgreSQL database. Every end-user
; installation talks to this URL. Get it from the Railway dashboard:
;   Project -> Postgres service -> Variables -> DATABASE_PUBLIC_URL.
; (You may need to enable "TCP Proxy" / public networking on the Postgres
; service first.) Rotating credentials means rebuild + redistribute the
; installer.
;
; ⚠️  PLACEHOLDER — replace with your real Railway public proxy URL before
;     producing a release build.
#define DATABASE_URL "postgresql://USER:PASSWORD@HOST.proxy.rlwy.net:PORT/railway"

[Setup]
; Generated GUID — do NOT reuse one from a sibling project. Inno uses this
; to identify the app for upgrade detection in the registry.
AppId={{F7A4D9C1-3B6E-4A2D-9C5F-8E1B7D0A2F4C}
AppName=Super TTS
AppVersion={#AppVer}
AppPublisher=Osiris DevWorks
DefaultDirName={localappdata}\Osiris DevWorks\Super TTS
DefaultGroupName=Super TTS
OutputDir=dist
OutputBaseFilename=Super-TTS-{#AppVer}-Setup
Compression=lzma
SolidCompression=yes
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
WizardStyle=modern
; lowest = no admin prompt, since {localappdata} is user-writable. Smart
; Citizen requires admin for unrelated reasons (registry writes outside HKCU);
; this bot doesn't.
PrivilegesRequired=lowest
; Optional icon — bundle one at assets\super-tts.ico to enable.
;SetupIconFile=assets\super-tts.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[InstallDelete]
; Wipe the install dir before laying down the new build to avoid leftover
; files from a prior version. The user's .env (in %APPDATA%) and the
; downloaded Supertonic model cache (in %USERPROFILE%\.cache) are NOT under
; {app}, so they survive untouched.
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

[Code]
var
  TokenPage: TInputQueryWizardPage;

procedure InitializeWizard();
begin
  TokenPage := CreateInputQueryPage(wpSelectDir,
    'Discord Bot Token',
    'Paste the bot token from the Discord Developer Portal',
    'Create your own bot at https://discord.com/developers/applications, ' +
    'enable the Message Content, Server Members, and Voice States intents, ' +
    'copy the bot token, and paste it below. The token is stored only on ' +
    'this PC at %APPDATA%\Osiris DevWorks\Super TTS\.env.');
  TokenPage.Add('Discord Token:', True);
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  EnvDir: String;
  EnvPath: String;
  Body: String;
begin
  if CurStep = ssPostInstall then
  begin
    EnvDir  := ExpandConstant('{userappdata}\Osiris DevWorks\Super TTS');
    EnvPath := EnvDir + '\.env';
    ForceDirectories(EnvDir);
    { Preserve an existing .env so reinstalls don't blow away a token the
      user previously pasted. They can always edit the file by hand. }
    if not FileExists(EnvPath) then
    begin
      Body := 'DISCORD_TOKEN=' + TokenPage.Values[0] + #13#10 +
              'DATABASE_URL={#DATABASE_URL}' + #13#10 +
              'LOG_LEVEL=INFO' + #13#10;
      SaveStringToFile(EnvPath, Body, False);
      Log('Wrote initial .env to ' + EnvPath);
    end
    else
    begin
      Log('Existing .env preserved at ' + EnvPath);
    end;
  end;
end;
