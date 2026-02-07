; Script generated for TaskFlow v5.0
; Matches the dark aesthetic of the application.

#define MyAppName "TaskFlow"
#define MyAppVersion "5.0"
#define MyAppPublisher "Dyvorn"
#define MyAppURL "https://github.com/Dyvorn/TaskFlow"
#define MyAppExeName "TaskFlow.exe"

[Setup]
; NOTE: The value of AppId uniquely identifies this application. Do not use the same AppId value in installers for other applications.
AppId={{8F423871-09C6-4679-8432-1234567890AB}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
; Install for current user by default (no admin needed)
PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename=TaskFlow_Setup_v{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern

; Uninstall settings
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startup"; Description: "Start TaskFlow with Windows"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; NOTE: Run build_for_iss.bat first to generate the dist/TaskFlow folder!
Source: "dist\TaskFlow\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\TaskFlow\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#MyAppName}"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: startup

[Code]
// Custom styling to match TaskFlow's Dark & Gold theme

procedure InitializeWizard;
var
  DarkBG, CardBG, Gold, TextWhite, TextGray: TColor;
begin
  // Define Colors (Delphi TColor is $00BBGGRR)
  DarkBG := $1e1c1c;   // #1c1c1e
  CardBG := $2e2c2c;   // #2c2c2e
  Gold := $24bffb;     // #fbbf24
  TextWhite := $ffffff;
  TextGray := $938e8e; // #8e8e93

  // Apply Dark Theme to Wizard Form
  WizardForm.Color := DarkBG;
  WizardForm.WelcomePage.Color := DarkBG;
  WizardForm.InnerPage.Color := DarkBG;
  WizardForm.FinishedPage.Color := DarkBG;
  WizardForm.LicensePage.Color := DarkBG;
  WizardForm.SelectDirPage.Color := DarkBG;
  WizardForm.SelectComponentsPage.Color := DarkBG;
  WizardForm.SelectTasksPage.Color := DarkBG;
  WizardForm.ReadyPage.Color := DarkBG;
  WizardForm.InstallingPage.Color := DarkBG;
  
  // Text Colors
  WizardForm.WelcomeLabel1.Font.Color := Gold;
  WizardForm.WelcomeLabel1.Color := DarkBG;
  
  WizardForm.WelcomeLabel2.Font.Color := TextWhite;
  WizardForm.WelcomeLabel2.Color := DarkBG;
  
  WizardForm.PageNameLabel.Font.Color := Gold;
  WizardForm.PageNameLabel.Color := DarkBG;
  
  WizardForm.PageDescriptionLabel.Font.Color := TextWhite;
  WizardForm.PageDescriptionLabel.Color := DarkBG;
  
  WizardForm.FinishedHeadingLabel.Font.Color := Gold;
  WizardForm.FinishedHeadingLabel.Color := DarkBG;
  
  WizardForm.FinishedLabel.Font.Color := TextWhite;
  WizardForm.FinishedLabel.Color := DarkBG;
  
  // Input Fields
  WizardForm.DirEdit.Color := CardBG;
  WizardForm.DirEdit.Font.Color := TextWhite;
  
  // Hide bevels for a cleaner, flat look
  WizardForm.Bevel.Visible := False;
  WizardForm.Bevel1.Visible := False;
end;