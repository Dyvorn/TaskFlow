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

// Win32 API for dragging the frameless window
function ReleaseCapture(): Longint; external 'ReleaseCapture@user32.dll stdcall';
function SendMessage(hWnd: HWND; Msg: UINT; wParam: Longint; lParam: Longint): Longint; external 'SendMessageA@user32.dll stdcall';

var
  TitleBar: TPanel;
  TitleLabel: TLabel;
  CustomNextBtn, CustomBackBtn, CustomCancelBtn: TPanel;
  CustomNextLbl, CustomBackLbl, CustomCancelLbl: TLabel;
  CustomBrowseBtn: TPanel;
  CustomBrowseLbl: TLabel;

// Colors
const
  DarkBG = $1e1c1c;   // #1c1c1e
  CardBG = $2e2c2c;   // #2c2c2e
  Gold   = $24bffb;   // #fbbf24 (Inno uses BGR)
  White  = $ffffff;
  Gray   = $938e8e;


procedure CustomNextClick(Sender: TObject);
begin
  WizardForm.NextButton.OnClick(WizardForm.NextButton);
end;

procedure CustomBackClick(Sender: TObject);
begin
  WizardForm.BackButton.OnClick(WizardForm.BackButton);
end;

procedure CustomCancelClick(Sender: TObject);
begin
  WizardForm.CancelButton.OnClick(WizardForm.CancelButton);
end;

procedure CustomBrowseClick(Sender: TObject);
begin
  WizardForm.DirBrowseButton.OnClick(WizardForm.DirBrowseButton);
end;

function CreateFlatButton(Parent: TWinControl; Caption: String; Left, Top, Width, Height: Integer; OnClick: TNotifyEvent; BgColor, FgColor: TColor; var OutLabel: TLabel): TPanel;
var
  P: TPanel;
  L: TLabel;
begin
  P := TPanel.Create(Parent);
  P.Parent := Parent;
  P.SetBounds(Left, Top, Width, Height);
  P.Color := BgColor;
  P.BevelOuter := bvNone;
  P.Cursor := crHand;
  P.OnClick := OnClick;
  
  L := TLabel.Create(P);
  L.Parent := P;
  L.Caption := Caption;
  L.Font.Color := FgColor;
  L.Font.Style := [fsBold];
  L.Font.Size := 10;
  L.Transparent := False;
  L.Color := BgColor;
  L.OnClick := OnClick;
  
  // Center label
  L.Left := (Width - L.Width) div 2;
  L.Top := (Height - L.Height) div 2;
  
  OutLabel := L;
  Result := P;
end;

procedure InitializeWizard;
begin
  // 1. Window Setup (Frameless, Compact)
  WizardForm.BorderStyle := bsNone;
  WizardForm.ClientWidth := 440;
  WizardForm.ClientHeight := 550;
  WizardForm.Color := DarkBG;
  WizardForm.Position := poScreenCenter;

  // 2. Custom Title Bar
  TitleBar := TPanel.Create(WizardForm);
  TitleBar.Parent := WizardForm;
  TitleBar.SetBounds(0, 0, WizardForm.ClientWidth, 50);
  TitleBar.Color := CardBG;
  TitleBar.BevelOuter := bvNone;

  TitleLabel := TLabel.Create(TitleBar);
  TitleLabel.Parent := TitleBar;
  TitleLabel.Caption := 'TaskFlow Setup';
  TitleLabel.Font.Color := White;
  TitleLabel.Font.Style := [fsBold];
  TitleLabel.Font.Size := 12;
  TitleLabel.Left := 20;
  TitleLabel.Top := 14;
  TitleLabel.Transparent := True;

  // 3. Hide Standard Chrome
  WizardForm.Bevel.Visible := False;
  WizardForm.Bevel1.Visible := False;
  WizardForm.MainPanel.Visible := False; 
  WizardForm.NextButton.Visible := False;
  WizardForm.BackButton.Visible := False;
  WizardForm.CancelButton.Visible := False;
  
  // Move standard buttons off-screen to prevent them from flashing/glitching
  WizardForm.NextButton.Left := -9999;
  WizardForm.BackButton.Left := -9999;
  WizardForm.CancelButton.Left := -9999;

  // Custom Browse Button (SelectDirPage)
  // Parent to SelectDirPage so it shows/hides automatically
  CustomBrowseBtn := CreateFlatButton(WizardForm.SelectDirPage, 'Browse...', WizardForm.DirBrowseButton.Left, WizardForm.DirBrowseButton.Top, WizardForm.DirBrowseButton.Width, WizardForm.DirBrowseButton.Height, @CustomBrowseClick, CardBG, Gold, CustomBrowseLbl);
  
  // Hide standard Browse button
  WizardForm.DirBrowseButton.Visible := False;

  // 4. Custom Buttons (Bottom Area)
  CustomCancelBtn := CreateFlatButton(WizardForm, 'Cancel',   20, 500,  80, 36, @CustomCancelClick, DarkBG, Gray,   CustomCancelLbl);
  CustomBackBtn   := CreateFlatButton(WizardForm, '< Back',   220, 500,  80, 36, @CustomBackClick,   CardBG, Gold,   CustomBackLbl);
  CustomNextBtn   := CreateFlatButton(WizardForm, 'Next >',   310, 500, 110, 36, @CustomNextClick,   Gold,   DarkBG, CustomNextLbl);

  // 5. Reparent & Style Page Headers (since MainPanel is hidden)
  WizardForm.PageNameLabel.Parent := WizardForm;
  WizardForm.PageNameLabel.Top := 60;
  WizardForm.PageNameLabel.Left := 20;
  WizardForm.PageNameLabel.Width := 400;
  WizardForm.PageNameLabel.Font.Color := Gold;
  WizardForm.PageNameLabel.Font.Style := [fsBold];
  WizardForm.PageNameLabel.Font.Size := 10;
  WizardForm.PageNameLabel.Color := DarkBG;
  
  WizardForm.PageDescriptionLabel.Parent := WizardForm;
  WizardForm.PageDescriptionLabel.Top := 80;
  WizardForm.PageDescriptionLabel.Left := 20;
  WizardForm.PageDescriptionLabel.Width := 400;
  WizardForm.PageDescriptionLabel.Font.Color := White;
  WizardForm.PageDescriptionLabel.Color := DarkBG;

  // 6. Adjust Content Area
  WizardForm.OuterNotebook.SetBounds(0, 110, 440, 380);
  WizardForm.InnerPage.Color := DarkBG;
  
  // 7. Style Standard Text
  WizardForm.WelcomeLabel1.Font.Color := Gold;
  WizardForm.WelcomeLabel1.Color := DarkBG;
  WizardForm.WelcomeLabel2.Font.Color := White;
  WizardForm.WelcomeLabel2.Color := DarkBG;
  
  WizardForm.FinishedHeadingLabel.Font.Color := Gold;
  WizardForm.FinishedHeadingLabel.Color := DarkBG;
  WizardForm.FinishedLabel.Font.Color := White;
  WizardForm.FinishedLabel.Color := DarkBG;
  
  // Input Fields
  WizardForm.DirEdit.Color := CardBG;
  WizardForm.DirEdit.Font.Color := White;

  // Inner Page Labels (Ensure readability on dark background)
  WizardForm.SelectDirLabel.Font.Color := White;
  WizardForm.SelectDirLabel.Color := DarkBG;
  
  WizardForm.SelectDirBrowseLabel.Font.Color := White;
  WizardForm.SelectDirBrowseLabel.Color := DarkBG;
  
  WizardForm.SelectTasksLabel.Font.Color := White;
  WizardForm.SelectTasksLabel.Color := DarkBG;
  
  WizardForm.ReadyLabel.Font.Color := White;
  WizardForm.ReadyLabel.Color := DarkBG;
  
  WizardForm.StatusLabel.Font.Color := White;
  WizardForm.StatusLabel.Color := DarkBG;
  
  WizardForm.FilenameLabel.Font.Color := Gray;
  WizardForm.FilenameLabel.Color := DarkBG;
  
  WizardForm.DiskSpaceLabel.Font.Color := Gray;
  WizardForm.DiskSpaceLabel.Color := DarkBG;

  // Checkboxes (Tasks & Run)
  WizardForm.TasksList.Color := DarkBG;
  WizardForm.TasksList.Font.Color := White;
  
  WizardForm.RunList.Color := DarkBG;
  WizardForm.RunList.Font.Color := White;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  // Update Button Visibility & Text
  CustomBackBtn.Visible := (CurPageID <> wpWelcome) and (CurPageID <> wpFinished);
  CustomCancelBtn.Visible := (CurPageID <> wpFinished) and (CurPageID <> wpInstalling);
  CustomNextBtn.Visible := (CurPageID <> wpInstalling);
  
  CustomBackBtn.BringToFront;
  CustomCancelBtn.BringToFront;
  CustomNextBtn.BringToFront;

  // Hide headers on Welcome/Finished pages (they use their own labels)
  WizardForm.PageNameLabel.Visible := (CurPageID <> wpWelcome) and (CurPageID <> wpFinished);
  WizardForm.PageDescriptionLabel.Visible := (CurPageID <> wpWelcome) and (CurPageID <> wpFinished);

  if CurPageID = wpFinished then begin
    CustomNextLbl.Caption := 'Finish';
  end else if CurPageID = wpReady then begin
    CustomNextLbl.Caption := 'Install';
  end else begin
    CustomNextLbl.Caption := 'Next >';
  end;

  // Re-center label
  with CustomNextLbl do begin
    Left := (CustomNextBtn.Width - Width) div 2;
  end;
end;