# Split Excel by Manager

A one-click Excel macro that splits a workbook into one password-protected
file per unique **Manager**. Every output file only shows the rows for that
manager, and the password to open the file is:

```
<ManagerName>123
```

So if the manager name is `John`, the password is `John123`.

## How to install it

1. Open your Excel file that has the manager data (columns: Manager,
   Engagement Letter Number, Status, ...). Row 1 must be the headers.
2. Press **Alt + F11** to open the VBA editor.
3. In the menu: **File -> Import File...** and pick
   `SplitByManager.bas` from this folder.
4. Close the VBA editor.
5. Save your workbook as **Excel Macro-Enabled Workbook (`.xlsm`)**.

## How to add the button

1. Turn on the Developer tab if it isn't visible:
   **File -> Options -> Customize Ribbon -> tick "Developer"**.
2. On the Developer tab click **Insert -> Button (Form Control)** and draw
   the button on your sheet.
3. In the "Assign Macro" dialog, pick **SplitByManager** and click OK.
4. Right-click the button to rename it (e.g. "Split by Manager").

## How to use it

1. Make sure the sheet with the data is the active sheet.
2. Click the button.
3. Pick a folder where the files should be saved.
4. The macro creates one `.xlsx` per unique manager, each protected with
   the password `<ManagerName>123`.

## Notes

- The macro finds the Manager column by looking for a header named
  exactly `Manager` (case-insensitive). If your column has a different
  name, change the `MANAGER_HEADER` constant at the top of the `.bas`
  file.
- The password suffix is the constant `PASSWORD_SUFFIX` (default `123`).
  Change it there if you want a different pattern.
- Existing files with the same name in the output folder are overwritten.
- Blank manager cells are skipped.
