; NovelTrad v4 Inno Setup installer
;
; The version is injected by `build.py` via the NOVELTRAD_VERSION env
; variable (which is also written to dist/NovelTrad/VERSION). The
; [Code] block reads it at compile time so the installer filename
; and the AppVersion always match the running app.
;
; Code signing: if the SIGNTOOL_PFX env var is set, the SignTool
; directive is added to both Sign and SignOnce. Otherwise the
; installer is built unsigned (developer machines).

#if GetEnv("NOVELTRAD_VERSION") == ""
  #define NOVELTRAD_VERSION "0.0.0"
#else
  #define NOVELTRAD_VERSION GetEnv("NOVELTRAD_VERSION")
#endif

#ifndef MyAppId
  #define MyAppId "{{6F1A2C5E-4B9B-4D2A-9F3D-1A7B5C6D8E20}"
#endif

#ifndef MyAppName
  #define MyAppName "NovelTrad"
#endif

#ifndef MyAppPublisher
  #define MyAppPublisher "NovelTrad Team"
#endif

#define SignTool \
  (GetEnv("SIGNTOOL_PFX") != "" ? \
    "signtool sign /f $q%SIGNTOOL_PFX%$q /p %SIGNTOOL_PFX_PASSWORD% /tr http://timestamp.digicert.com /td sha256 /fd sha256 $f" : \
    "")

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#NOVELTRAD_VERSION}
AppPublisher={#MyAppPublisher}
AppPublisherURL=https://github.com/Balrog57/noveltrad
AppSupportURL=https://github.com/Balrog57/noveltrad/issues
AppUpdatesURL=https://github.com/Balrog57/noveltrad/releases
DefaultDirName={localappdata}\Programs\NovelTrad
DefaultGroupName=NovelTrad
OutputDir=.
OutputBaseFilename=Setup_NovelTrad-v{#NOVELTRAD_VERSION}
Compression=lzma
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
MinVersion=10.0
AppMutex=NovelTrad-singleton-instance
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\NovelTrad.exe
UninstallDisplayName={#MyAppName}
WizardStyle=modern
SetupLogging=yes
SignedUninstaller={#GetEnv("SIGNTOOL_PFX") != "" ? "yes" : "no"}
#if GetEnv("SIGNTOOL_PFX") != ""
SignTool={#SignTool}
Sign=Setup
#endif

[Files]
Source: "dist\NovelTrad\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Icons]
Name: "{group}\NovelTrad"; Filename: "{app}\NovelTrad.exe"
Name: "{userdesktop}\NovelTrad"; Filename: "{app}\NovelTrad.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Run]
Filename: "{app}\NovelTrad.exe"; Description: "Launch NovelTrad"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Keep room for future cleanup hooks; intentionally empty for v1.

[Code]
var
  DependencyPage: TOutputMsgWizardPage;

procedure KillRunningInstance();
var
  RetCode: Integer;
begin
  // Stop a running NovelTrad.exe before the installer overwrites the
  // binary. We try `/F /IM` first; if the process is not running the
  // command exits with a non-zero code which is intentionally ignored.
  if Exec('taskkill.exe', '/F /IM NovelTrad.exe', '',
         SW_HIDE, ewNoWait, RetCode) then
  begin
    Sleep(500);
  end;
end;

function AppLanguageCode(): String;
begin
  if ActiveLanguage = 'french' then
    Result := 'fr'
  else
    Result := 'en';
end;

procedure WriteInitialLanguage();
var
  AppDataDir: String;
  ConfigPath: String;
  LangPath: String;
begin
  AppDataDir := ExpandConstant('{userappdata}\NovelTrad');
  ConfigPath := AppDataDir + '\config.json';
  LangPath := AppDataDir + '\installer_language.txt';
  if not DirExists(AppDataDir) then
    ForceDirectories(AppDataDir);

  if not FileExists(ConfigPath) then
    SaveStringToFile(LangPath, AppLanguageCode(), False);
end;

procedure InitializeWizard;
begin
  DependencyPage := CreateOutputMsgPage(
    wpSelectTasks,
    'External translation tools',
    'NovelTrad is installed locally. Large AI models are configured after launch.',
    'NovelTrad includes the desktop app, backend, PyQt6, CTranslate2 runtime, EPUB/TXT/DOCX/SRT handlers, and packaging dependencies.' + #13#10#13#10 +
    'For the best hybrid workflow, install or configure after launch:' + #13#10 +
    '- Ollama, or an OpenAI-compatible endpoint, for lexicon/QA/polishing agents.' + #13#10 +
    '- A local CTranslate2 NLLB model directory for fast draft translation.' + #13#10 +
    '- Optional LanguageTool/Java only if you want the external grammar backend.' + #13#10#13#10 +
    'The first-run wizard will guide these settings. The app can still open without them and will report missing tools clearly.'
  );
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then
    KillRunningInstance();
  if CurStep = ssPostInstall then
    WriteInitialLanguage();
end;
