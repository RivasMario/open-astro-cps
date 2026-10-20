On Error Resume Next
Set obj = CreateObject("RemoteProtocols.RemSB9600")
If Err.Number <> 0 Then
    WScript.Echo "CreateObject FAILED: " & Err.Number & " " & Err.Description
    WScript.Quit
End If
WScript.Echo "Object created: " & TypeName(obj)

' GetPortNames is read-only enumeration - no device contact
names = ""
rc = obj.GetPortNames(names)
If Err.Number <> 0 Then
    WScript.Echo "GetPortNames call FAILED: " & Err.Number & " " & Err.Description & " (may need different arg signature)"
Else
    WScript.Echo "GetPortNames rc=" & rc & " names=[" & names & "]"
End If
