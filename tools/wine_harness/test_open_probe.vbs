On Error Resume Next
Set obj = CreateObject("RemoteProtocols.RemSB9600")
If Err.Number <> 0 Then
    WScript.Echo "CreateObject FAILED: " & Err.Number & " " & Err.Description
    WScript.Quit
End If
WScript.Echo "Object created: " & TypeName(obj)

' Open(lpszDeviceName, dwFlags) per typelib param names. Try COM5 (mapped to
' the real /dev/ttyACM0), flags=0.
rc = obj.Open("COM5", 0)
If Err.Number <> 0 Then
    WScript.Echo "Open call raised error: " & Err.Number & " " & Err.Description
Else
    WScript.Echo "Open() returned: " & rc
End If
Err.Clear

' GetTimers is named as a pure getter (pTimers out-param) - should not transmit
' anything to the radio, just reads the object's internal timer config.
t = Empty
rc2 = obj.GetTimers(t)
If Err.Number <> 0 Then
    WScript.Echo "GetTimers call raised error: " & Err.Number & " " & Err.Description
Else
    WScript.Echo "GetTimers() returned: " & rc2 & " value=[" & t & "]"
End If
Err.Clear

' Explicitly NOT calling Send("EPREQ", ...) or Request(...) here - those are
' the mode-changing / transmitting calls. Close cleanly.
rc3 = obj.Close()
WScript.Echo "Close() returned: " & rc3
