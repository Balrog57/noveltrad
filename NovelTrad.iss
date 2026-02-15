[Setup]
AppName=NovelTrad
AppVersion=1.0
DefaultDirName={autopf}\NovelTrad
DefaultGroupName=NovelTrad
OutputDir=.
OutputBaseFilename=Setup_NovelTrad
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64

[Files]
Source: "dist\NovelTrad\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\NovelTrad"; Filename: "{app}\NovelTrad.exe"
Name: "{commondesktop}\NovelTrad"; Filename: "{app}\NovelTrad.exe"

[Run]
Filename: "{app}\NovelTrad.exe"; Description: "Launch NovelTrad"; Flags: nowait postinstall skipifsilent
