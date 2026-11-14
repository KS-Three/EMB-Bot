; Inno Setup 6 script: the frozen folder (packaging/build_freeze.py) as one
; setup.exe. Compiled and proved by packaging/build_installer.py, which passes
; the four /D defines; do not compile it by hand without them.
;
; PER USER, NO ADMIN PROMPT (PrivilegesRequired=lowest): it installs under
; %LOCALAPPDATA%\Programs, so a shop PC whose owner is not its administrator
; can still install it, and nothing is written outside the user's profile.
;
; UNSIGNED. Windows SmartScreen will warn on download and on first run until
; there is a code-signing certificate (Kent's call, not made).
;
; THE SHORTCUT STARTS THE LAUNCHER (embbot_launcher.py, the frozen entry since
; 2026-11-13): it holds port 8721, reuses a copy already running, opens the
; browser at http://127.0.0.1:8721/ and starts itself with --serve as the
; service. No arguments: the one port is the launcher's own rule.

#ifndef SourceDir
  #error Pass /DSourceDir=<the frozen folder>
#endif
#ifndef OutputDir
  #error Pass /DOutputDir=<where setup.exe goes>
#endif
#ifndef OutputBase
  #error Pass /DOutputBase=<setup file name, no extension>
#endif
#ifndef AppVersion
  #error Pass /DAppVersion=<the release name>
#endif
#ifndef ExeName
  #define ExeName "embbot-digitizer.exe"
#endif

[Setup]
; AppId is how Windows knows a later installer is an UPGRADE of this one.
; Never change it: a new id installs a second copy beside the first.
AppId={{E5D491C7-8B84-4FE9-84CF-3737653A83ED}
AppName=EMB Bot Studio
AppVersion={#AppVersion}
AppPublisher=Fritsch's Stitches
DefaultDirName={autopf}\EMB Bot Studio
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#OutputDir}
OutputBaseFilename={#OutputBase}
Compression=lzma2/max
SolidCompression=yes
LZMAUseSeparateProcess=yes
WizardStyle=modern
UninstallDisplayName=EMB Bot Studio

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\EMB Bot Studio"; Filename: "{app}\{#ExeName}"; WorkingDir: "{app}"
