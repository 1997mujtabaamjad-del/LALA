Set WshShell = CreateObject("WScript.Shell")
strDesktop = WshShell.SpecialFolders("Desktop")
strScriptDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)

Set objShortcut = WshShell.CreateShortcut(strDesktop & "\Laalaa Arc Reactor.lnk")
objShortcut.TargetPath = strScriptDir & "\Laalaa_Arc_Reactor.vbs"
objShortcut.WorkingDirectory = strScriptDir
objShortcut.Description = "Laalaa J.A.R.V.I.S. Arc Reactor AI Companion"
objShortcut.IconLocation = strScriptDir & "\src\bishu\data\reactor_icon.png,0"
objShortcut.Save

WScript.Echo "Success! Laalaa Arc Reactor App Shortcut has been placed directly on your Windows Desktop."
