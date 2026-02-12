; TaskFlow v6.0 Inno Setup Script

[Setup]
AppName=TaskFlow
AppVersion=6.0
AppPublisher=Dyvorn
AppPublisherURL=https://github.com/Dyvorn/TaskFlow
AppSupportURL=https://github.com/Dyvorn/TaskFlow/issues
; Install to user's local programs folder (no admin rights needed)
DefaultDirName={userpf}\TaskFlow
DefaultGroupName=TaskFlow
OutputDir=release
OutputBaseFilename=TaskFlow_v6_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; Icon for the setup executable itself
SetupIconFile=icon.ico
; Icon for Add/Remove programs
UninstallDisplayIcon={app}\TaskFlow.exe
; User level privileges
PrivilegesRequired=lowest

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "dist\TaskFlow.exe"; DestDir: "{app}"; Flags: ignoreversion
; Add any other assets like icons or documentation here if needed
; Example: Source: "assets\*"; DestDir: "{app}\assets"; Flags: recursesubdirs

[Icons]
Name: "{group}\TaskFlow"; Filename: "{app}\TaskFlow.exe"
Name: "{group}\TaskFlow (Hub Only)"; Filename: "{app}\TaskFlow.exe"; Parameters: "--no-widget"
Name: "{group}\Uninstall TaskFlow"; Filename: "{uninstallexe}"
; Optional: Desktop icon
Name: "{userdesktop}\TaskFlow"; Filename: "{app}\TaskFlow.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startup"; Description: "Launch TaskFlow on system startup"; GroupDescription: "Startup:";

[Run]
Filename: "{app}\TaskFlow.exe"; Description: "{cm:LaunchProgram,TaskFlow}"; Flags: nowait postinstall skipifsilent

[InstallDelete]
Type: files; Name: "{app}\TaskFlow.exe.old"

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    if IsTaskSelected('startup') then
      RegWriteStringValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Run', 'TaskFlow', '"' + ExpandConstant('{app}\TaskFlow.exe') + '"');
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
    RegDeleteValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Run', 'TaskFlow');
end;