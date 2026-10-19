#define NomApp "Photos de classe"
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{B7C3E0A4-5D1F-4E6B-9A21-3F8C6D2E7A10}
AppName={#NomApp}
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\PhotoClasse
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=sortie_installateur
OutputBaseFilename=PhotoClasse_Setup
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
UninstallDisplayIcon={app}\PhotoClasse.exe
WizardStyle=modern

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Files]
Source: "dist\PhotoClasse\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{userprograms}\{#NomApp}"; Filename: "{app}\PhotoClasse.exe"
Name: "{userdesktop}\{#NomApp}"; Filename: "{app}\PhotoClasse.exe"

[Run]
Filename: "{app}\PhotoClasse.exe"; Description: "Lancer {#NomApp}"; Flags: nowait postinstall
