On Error Resume Next
Set obj = CreateObject("RemoteProtocols.RemSB9600")
If Err.Number <> 0 Then
    WScript.Echo "CreateObject FAILED: " & Err.Number & " " & Err.Description
Else
    WScript.Echo "CreateObject OK: " & TypeName(obj)
End If
