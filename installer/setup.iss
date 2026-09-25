#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{6E1B7C52-3F1A-4B0E-9D5A-2C8A7F0B4E11}
AppName=Transcritor de Áudio
AppVersion={#AppVersion}
DefaultDirName={autopf}\Transcritor de Áudio
DefaultGroupName=Transcritor de Áudio
OutputDir=..\dist-installer
OutputBaseFilename=TranscritorDeAudio-Setup-{#AppVersion}
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\TranscritorDeAudio.exe
Compression=lzma2/fast
SolidCompression=no
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
WizardStyle=modern

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; GroupDescription: "Atalhos:"

[Files]
Source: "..\dist\TranscritorDeAudio\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\Transcritor de Áudio"; Filename: "{app}\TranscritorDeAudio.exe"
Name: "{autodesktop}\Transcritor de Áudio"; Filename: "{app}\TranscritorDeAudio.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\TranscritorDeAudio.exe"; Description: "Abrir o Transcritor de Áudio"; Flags: nowait postinstall skipifsilent
