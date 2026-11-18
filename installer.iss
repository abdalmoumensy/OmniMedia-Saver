[Setup]
AppId={{8F9E7A2C-5C31-4D8E-9A12-4F6B8D3E1A90}
AppName=OmniMedia Saver
AppVersion=2.0.0
AppPublisher=OmniMedia Open Source
DefaultDirName={autopf}\OmniMedia Saver
DefaultGroupName=OmniMedia Saver
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
SetupIconFile=app_icon.ico
UninstallDisplayIcon={app}\OmniMediaSaver.exe
OutputDir=dist_installer
OutputBaseFilename=OmniMedia-Saver-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\OmniMediaSaver\OmniMediaSaver.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\OmniMediaSaver\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\OmniMedia Saver"; Filename: "{app}\OmniMediaSaver.exe"
Name: "{autodesktop}\OmniMedia Saver"; Filename: "{app}\OmniMediaSaver.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\OmniMediaSaver.exe"; Description: "{cm:LaunchProgram,OmniMedia Saver}"; Flags: nowait postinstall skipifsilent
