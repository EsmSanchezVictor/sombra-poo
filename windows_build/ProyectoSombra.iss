#ifndef ProjectRoot
  #error Compile con tools/build_windows.py --installer para proporcionar ProjectRoot.
#endif
#define AppName "Proyecto Sombra"
#define AppVersion "35.6.43.6"

[Setup]
AppId={{66E574A9-BDFA-4E23-A4CE-F5B1D6412E44}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName=Proyecto Sombra v35.6-etapa4.3.6
DefaultDirName={localappdata}\Programs\ProyectoSombra
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir={#ProjectRoot}\release
OutputBaseFilename=ProyectoSombra_Setup_35.6_etapa4.3.6_x64
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\ProyectoSombra.exe
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; Flags: unchecked

[Files]
Source: "{#ProjectRoot}\dist\ProyectoSombra\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Proyecto Sombra"; Filename: "{app}\ProyectoSombra.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\Proyecto Sombra"; Filename: "{app}\ProyectoSombra.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\ProyectoSombra.exe"; Description: "Abrir Proyecto Sombra"; Flags: nowait postinstall skipifsilent

; No se eliminan preferencias, usuarios ni proyectos de APPDATA al desinstalar.
