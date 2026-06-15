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
  #define MyAppId "{{6F1A2C5E-4B9B-4D2A-9F3D-1A7B5C6D8E20}}"
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
AppVerName={#MyAppName} {#NOVELTRAD_VERSION}
AppPublisher={#MyAppPublisher}
AppPublisherURL=https://github.com/Balrog57/noveltrad
AppSupportURL=https://github.com/Balrog57/noveltrad/issues
AppUpdatesURL=https://github.com/Balrog57/noveltrad/releases
DefaultDirName={localappdata}\Programs\NovelTrad
DefaultGroupName=NovelTrad
OutputDir=.
OutputBaseFilename=Setup_NovelTrad-v{#NOVELTRAD_VERSION}
Compression=lzma2/ultra64
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
MinVersion=10.0
AppMutex=NovelTrad-singleton-instance
DisableProgramGroupPage=yes
SetupIconFile=assets\noveltrad-icon.ico
UninstallDisplayIcon={app}\NovelTrad.exe
UninstallDisplayName={#MyAppName}
WizardStyle=modern
WizardSizePercent=100,100
SetupLogging=yes
SignedUninstaller={#GetEnv("SIGNTOOL_PFX") != "" ? "yes" : "no"}
#ifdef SignTool
SignTool={#SignTool}
Sign=Setup
#endif
; Register app for file associations
ChangesAssociations=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "associate_epub"; Description: "Associer les fichiers .epub"; GroupDescription: "Associations de fichiers:"; Flags: unchecked
Name: "associate_txt"; Description: "Associer les fichiers .txt"; GroupDescription: "Associations de fichiers:"; Flags: unchecked
Name: "associate_srt"; Description: "Associer les fichiers .srt"; GroupDescription: "Associations de fichiers:"; Flags: unchecked
Name: "associate_docx"; Description: "Associer les fichiers .docx"; GroupDescription: "Associations de fichiers:"; Flags: unchecked

[Files]
Source: "dist\NovelTrad\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "assets\noveltrad-icon.ico"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "assets\noveltrad-logo-256.png"; DestDir: "{app}\assets"; Flags: ignoreversion

[Icons]
Name: "{group}\NovelTrad"; Filename: "{app}\NovelTrad.exe"; WorkingDir: "{app}"
Name: "{group}\{cm:UninstallProgram,NovelTrad}"; Filename: "{uninstallexe}"; WorkingDir: "{app}"
Name: "{userdesktop}\NovelTrad"; Filename: "{app}\NovelTrad.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Registry]
; File associations (per-user — no admin needed)
Root: HKCU; Subkey: "Software\Classes\.epub"; ValueType: string; ValueName: ""; ValueData: "NovelTrad.EPUB"; Tasks: associate_epub; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\NovelTrad.EPUB"; ValueType: string; ValueName: ""; ValueData: "NovelTrad EPUB Document"; Tasks: associate_epub; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\NovelTrad.EPUB\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\NovelTrad.exe,0"; Tasks: associate_epub
Root: HKCU; Subkey: "Software\Classes\NovelTrad.EPUB\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\NovelTrad.exe"" ""%1"""; Tasks: associate_epub

Root: HKCU; Subkey: "Software\Classes\.txt"; ValueType: string; ValueName: ""; ValueData: "NovelTrad.TXT"; Tasks: associate_txt; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\NovelTrad.TXT"; ValueType: string; ValueName: ""; ValueData: "NovelTrad Text Document"; Tasks: associate_txt; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\NovelTrad.TXT\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\NovelTrad.exe,0"; Tasks: associate_txt
Root: HKCU; Subkey: "Software\Classes\NovelTrad.TXT\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\NovelTrad.exe"" ""%1"""; Tasks: associate_txt

Root: HKCU; Subkey: "Software\Classes\.srt"; ValueType: string; ValueName: ""; ValueData: "NovelTrad.SRT"; Tasks: associate_srt; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\NovelTrad.SRT"; ValueType: string; ValueName: ""; ValueData: "NovelTrad SRT Subtitles"; Tasks: associate_srt; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\NovelTrad.SRT\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\NovelTrad.exe,0"; Tasks: associate_srt
Root: HKCU; Subkey: "Software\Classes\NovelTrad.SRT\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\NovelTrad.exe"" ""%1"""; Tasks: associate_srt

Root: HKCU; Subkey: "Software\Classes\.docx"; ValueType: string; ValueName: ""; ValueData: "NovelTrad.DOCX"; Tasks: associate_docx; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\NovelTrad.DOCX"; ValueType: string; ValueName: ""; ValueData: "NovelTrad Word Document"; Tasks: associate_docx; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\NovelTrad.DOCX\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\NovelTrad.exe,0"; Tasks: associate_docx
Root: HKCU; Subkey: "Software\Classes\NovelTrad.DOCX\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\NovelTrad.exe"" ""%1"""; Tasks: associate_docx

[Run]
Filename: "{app}\NovelTrad.exe"; Description: "{cm:LaunchProgram,NovelTrad}"; Flags: nowait postinstall skipifsilent unchecked

[UninstallDelete]
Type: files; Name: "{userappdata}\NovelTrad\config.json"
Type: dirifempty; Name: "{userappdata}\NovelTrad"

[Code]
var
  DependencyPage: TOutputMsgWizardPage;

procedure KillRunningInstance();
var
  RetCode: Integer;
begin
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

function str_replace(S, Old, New: String): String;
var
  I: Integer;
begin
  Result := S;
  I := Pos(Old, Result);
  if I > 0 then
  begin
    Delete(Result, I, Length(Old));
    Insert(New, Result, I);
  end;
end;

procedure InitializeWizard;
var
  VersionStr: String;
  Msg: String;
begin
  VersionStr := ExpandConstant('{#NOVELTRAD_VERSION}');
  if VersionStr = '0.0.0' then
    VersionStr := '';

  if ActiveLanguage = 'french' then
  begin
    if VersionStr <> '' then
      Msg := 'NovelTrad v' + VersionStr + ' — Traducteur de romans multi-agent' + #13#10 +
             'Traduction de livres (EPUB, TXT, DOCX, SRT) par pipeline IA à 11 étapes.' + #13#10#13#10 +
             'L''application inclut :' + #13#10 +
             '  • Moteur de traduction local (NLLB / LLM)' + #13#10 +
             '  • Correcteur grammatical français (Grammalecte)' + #13#10 +
             '  • Glossaire automatique et vérification de cohérence' + #13#10 +
             '  • Assistant de relecture avec boucle réflexive' + #13#10 +
             '  • Export EPUB, TXT, DOCX, SRT' + #13#10#13#10 +
             'Configurez Ollama ou un endpoint OpenAI après l''installation pour les agents LLM.' + #13#10 +
             'L''assistant de premier démarrage vous guidera.'
    else
      Msg := 'NovelTrad — Traducteur de romans multi-agent' + #13#10 +
             'Traduction de livres (EPUB, TXT, DOCX, SRT) par pipeline IA à 11 étapes.' + #13#10#13#10 +
             'L''application inclut un moteur de traduction local, Grammalecte, ' +
             'glossaire automatique et export multi-format.' + #13#10#13#10 +
             'Configurez Ollama ou un endpoint OpenAI après l''installation pour les agents LLM.';
  end
  else
  begin
    if VersionStr <> '' then
      Msg := 'NovelTrad v' + VersionStr + ' — Multi-agent Novel Translator' + #13#10 +
             'Book translation (EPUB, TXT, DOCX, SRT) via an 11-stage AI pipeline.' + #13#10#13#10 +
             'Includes:' + #13#10 +
             '  • Local translation engine (NLLB / LLM)' + #13#10 +
             '  • French grammar checker (Grammalecte)' + #13#10 +
             '  • Automatic glossary & consistency checking' + #13#10 +
             '  • Reviewer assistant with reflexive loop' + #13#10 +
             '  • EPUB, TXT, DOCX, SRT export' + #13#10#13#10 +
             'Configure Ollama or an OpenAI-compatible endpoint after install for LLM agents.' + #13#10 +
             'The first-run wizard will walk you through the setup.'
    else
      Msg := 'NovelTrad — Multi-agent Novel Translator' + #13#10 +
             'Book translation (EPUB, TXT, DOCX, SRT) via an 11-stage AI pipeline.' + #13#10#13#10 +
             'Includes local translation engine, Grammalecte, automatic glossary, ' +
             'and multi-format export.' + #13#10#13#10 +
             'Configure Ollama or an OpenAI-compatible endpoint after install for LLM agents.';
  end;

  DependencyPage := CreateOutputMsgPage(
    wpSelectTasks,
    ExpandConstant('{cm:WelcomeLabel2}'),
    'NovelTrad',
    Msg
  );
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then
    KillRunningInstance();
  if CurStep = ssPostInstall then
    WriteInitialLanguage();
end;

function GetCustomSetupExitCode: Integer;
begin
  Result := 0;
end;
