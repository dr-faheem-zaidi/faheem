Attribute VB_Name = "SplitByManager"
Option Explicit

' ===================================================================
'  SplitByManager
'  -----------------------------------------------------------------
'  Creates one Excel file per unique Manager found in the active
'  sheet. Each output file contains only the rows for that manager
'  and is saved with a password of the form: <ManagerName>123
'
'  Assumptions:
'   - The data lives on the active worksheet.
'   - Row 1 contains column headers.
'   - One of the headers is literally "Manager" (case-insensitive).
'     Change MANAGER_HEADER below if your column is named differently.
'
'  How to use:
'   1. Open your workbook with the manager data.
'   2. Press Alt+F11 to open the VBA editor.
'   3. File -> Import File -> select SplitByManager.bas
'   4. Close the editor, go back to Excel.
'   5. Developer tab -> Insert -> Button (Form Control),
'      draw it on the sheet, and assign macro "SplitByManager".
'   6. Click the button.
' ===================================================================

Private Const MANAGER_HEADER As String = "Manager"
Private Const PASSWORD_SUFFIX As String = "123"

Public Sub SplitByManager()
    Dim srcWs As Worksheet
    Dim lastRow As Long, lastCol As Long
    Dim headerRange As Range
    Dim managerCol As Long
    Dim outputFolder As String
    Dim managers As Object     ' Scripting.Dictionary
    Dim cell As Range
    Dim key As Variant
    Dim srcWb As Workbook

    Set srcWb = ActiveWorkbook
    Set srcWs = ActiveSheet

    ' --- Find the last used cell ---
    lastRow = srcWs.Cells(srcWs.Rows.Count, 1).End(xlUp).Row
    lastCol = srcWs.Cells(1, srcWs.Columns.Count).End(xlToLeft).Column

    If lastRow < 2 Then
        MsgBox "No data rows found on '" & srcWs.Name & "'.", vbExclamation
        Exit Sub
    End If

    ' --- Locate the Manager column by header name ---
    Set headerRange = srcWs.Range(srcWs.Cells(1, 1), srcWs.Cells(1, lastCol))
    managerCol = 0

    Dim h As Range
    For Each h In headerRange.Cells
        If StrComp(Trim$(CStr(h.Value)), MANAGER_HEADER, vbTextCompare) = 0 Then
            managerCol = h.Column
            Exit For
        End If
    Next h

    If managerCol = 0 Then
        MsgBox "Could not find a column named '" & MANAGER_HEADER & "' in row 1.", vbExclamation
        Exit Sub
    End If

    ' --- Ask where to save the output files ---
    outputFolder = PickFolder("Choose a folder to save the manager files")
    If Len(outputFolder) = 0 Then Exit Sub
    If Right$(outputFolder, 1) <> Application.PathSeparator Then
        outputFolder = outputFolder & Application.PathSeparator
    End If

    ' --- Collect unique, non-empty manager names ---
    Set managers = CreateObject("Scripting.Dictionary")
    managers.CompareMode = 1 ' TextCompare - case insensitive

    Dim dataRange As Range
    Set dataRange = srcWs.Range(srcWs.Cells(2, managerCol), srcWs.Cells(lastRow, managerCol))

    For Each cell In dataRange.Cells
        Dim name As String
        name = Trim$(CStr(cell.Value))
        If Len(name) > 0 Then
            If Not managers.Exists(name) Then managers.Add name, True
        End If
    Next cell

    If managers.Count = 0 Then
        MsgBox "No manager names were found in the data.", vbExclamation
        Exit Sub
    End If

    ' --- Turn off noise for speed ---
    Application.ScreenUpdating = False
    Application.DisplayAlerts = False
    Application.EnableEvents = False
    Application.Calculation = xlCalculationManual

    Dim created As Long
    created = 0

    On Error GoTo CleanUp

    ' Remove any existing AutoFilter so our filter call is clean
    If srcWs.AutoFilterMode Then srcWs.AutoFilterMode = False

    Dim fullRange As Range
    Set fullRange = srcWs.Range(srcWs.Cells(1, 1), srcWs.Cells(lastRow, lastCol))

    For Each key In managers.Keys
        Dim mgrName As String
        mgrName = CStr(key)

        ' Filter the source for this manager
        fullRange.AutoFilter Field:=managerCol, Criteria1:=mgrName

        ' Copy visible rows (header + matching data) into a new workbook
        Dim newWb As Workbook
        Set newWb = Workbooks.Add(xlWBATWorksheet)

        fullRange.SpecialCells(xlCellTypeVisible).Copy
        newWb.Worksheets(1).Range("A1").PasteSpecial xlPasteAll
        newWb.Worksheets(1).Range("A1").Select
        Application.CutCopyMode = False

        ' Rename the sheet to the manager (trim to Excel's 31-char limit, strip bad chars)
        newWb.Worksheets(1).Name = SafeSheetName(mgrName)

        ' Save password-protected. Password to OPEN the file = <Manager>123
        Dim outPath As String
        outPath = outputFolder & SafeFileName(mgrName) & ".xlsx"

        ' Delete a previous version if it exists so SaveAs doesn't prompt
        If Len(Dir$(outPath)) > 0 Then Kill outPath

        newWb.SaveAs Filename:=outPath, _
                     FileFormat:=xlOpenXMLWorkbook, _
                     Password:=mgrName & PASSWORD_SUFFIX, _
                     CreateBackup:=False
        newWb.Close SaveChanges:=False
        Set newWb = Nothing

        created = created + 1
    Next key

CleanUp:
    Dim errNum As Long, errDesc As String
    errNum = Err.Number
    errDesc = Err.Description
    On Error Resume Next

    If srcWs.AutoFilterMode Then srcWs.AutoFilterMode = False
    Application.CutCopyMode = False
    Application.Calculation = xlCalculationAutomatic
    Application.EnableEvents = True
    Application.DisplayAlerts = True
    Application.ScreenUpdating = True

    If errNum <> 0 Then
        MsgBox "Finished with an error after creating " & created & " file(s)." & vbCrLf & _
               "Error " & errNum & ": " & errDesc, vbExclamation
    Else
        MsgBox "Done. Created " & created & " file(s) in:" & vbCrLf & outputFolder, vbInformation
    End If
End Sub

' Strip characters that are illegal in Windows filenames.
Private Function SafeFileName(ByVal s As String) As String
    Dim bad As Variant
    bad = Array("\", "/", ":", "*", "?", """", "<", ">", "|")
    Dim i As Long
    For i = LBound(bad) To UBound(bad)
        s = Replace(s, bad(i), "_")
    Next i
    SafeFileName = Trim$(s)
End Function

' Sheet names: <=31 chars and must not contain \ / ? * [ ]
Private Function SafeSheetName(ByVal s As String) As String
    Dim bad As Variant
    bad = Array("\", "/", "?", "*", "[", "]", ":")
    Dim i As Long
    For i = LBound(bad) To UBound(bad)
        s = Replace(s, bad(i), "_")
    Next i
    s = Trim$(s)
    If Len(s) > 31 Then s = Left$(s, 31)
    If Len(s) = 0 Then s = "Sheet1"
    SafeSheetName = s
End Function

Private Function PickFolder(ByVal title As String) As String
    Dim fd As FileDialog
    Set fd = Application.FileDialog(msoFileDialogFolderPicker)
    fd.title = title
    fd.AllowMultiSelect = False
    If fd.Show = -1 Then
        PickFolder = fd.SelectedItems(1)
    Else
        PickFolder = ""
    End If
End Function
