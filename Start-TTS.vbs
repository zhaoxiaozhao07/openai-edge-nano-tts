Dim WshShell, fso, currentPath
Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

currentPath = fso.GetParentFolderName(WScript.ScriptFullName)

WshShell.CurrentDirectory = currentPath

WshShell.Run "uv run main.py", 0, False