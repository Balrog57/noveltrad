[Setup]
AppName=NovelTrad
AppVersion=4.0.0
AppPublisher=NovelTrad Team
AppPublisherURL=https://github.com/
AppSupportURL=https://github.com/
AppUpdatesURL=https://github.com/
DefaultDirName={localappdata}\Programs\NovelTrad
DefaultGroupName=NovelTrad
OutputDir=.
OutputBaseFilename=Setup_NovelTrad
Compression=lzma
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\NovelTrad.exe
WizardStyle=modern
SetupLogging=yes

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "dist\NovelTrad\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\NovelTrad"; Filename: "{app}\NovelTrad.exe"
Name: "{userdesktop}\NovelTrad"; Filename: "{app}\NovelTrad.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\NovelTrad.exe"; Description: "Launch NovelTrad"; Flags: nowait postinstall skipifsilent

[Code]
var
  DependencyPage: TOutputMsgWizardPage;

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
