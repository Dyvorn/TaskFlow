[Setup]
; Basic Application Information
AppId={D81329C6-89AB-4567-1234-CDEF01234567}
AppName=TaskFlow
AppVersion=1.0
AppPublisher=Lennard Finn Penzler

; Install to the user's local application data folder so the app can save its JSON file without admin rights
DefaultDirName={userappdata}\TaskFlow
DisableProgramGroupPage=yes

; Output the installer to the current project folder
OutputDir=.
OutputBaseFilename=TaskFlow_Setup_v1.0
Compression=lzma
SolidCompression=yes
WizardStyle=modern

; Ensure the user doesn't need Admin rights to install (since we install to user folder)
PrivilegesRequired=lowest

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; IMPORTANT: This assumes you ran PyInstaller and the 'dist' folder is in the same directory as this script
Source: "dist\TaskFlow\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\TaskFlow"; Filename: "{app}\TaskFlow.exe"
Name: "{autodesktop}\TaskFlow"; Filename: "{app}\TaskFlow.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\TaskFlow.exe"; Description: "{cm:LaunchProgram,TaskFlow}"; Flags: nowait postinstall skipifsilent