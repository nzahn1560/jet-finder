/**
 * Copy visible (non-filtered) rows from "Aircraft Data" sheet to "Filtered View" sheet
 * Ignores header row (row 1) and starts copying from row 2
 * Clears old data in "Filtered View" before pasting
 */
function copyVisibleRows() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sourceSheet = ss.getSheetByName("Aircraft Data");
  const targetSheet = ss.getSheetByName("Filtered View");
  
  // Verify both sheets exist
  if (!sourceSheet || !targetSheet) {
    Logger.log("Error: Could not find one or both sheets");
    return;
  }
  
  // Get the total data range including headers
  const dataRange = sourceSheet.getDataRange();
  const numRows = dataRange.getNumRows();
  const numCols = dataRange.getNumColumns();
  
  // If there's no data, exit
  if (numRows <= 1) {
    Logger.log("No data to copy (only header row found)");
    return;
  }
  
  // Get all values from source sheet
  const values = dataRange.getValues();
  const header = values[0]; // Capture the header row
  
  // Create an array to hold visible rows
  const visibleRows = [];
  visibleRows.push(header); // Add header row first
  
  // Loop through each row (starting from row 2, index 1)
  for (let i = 1; i < numRows; i++) {
    // Check if the row is visible (not filtered out)
    if (!sourceSheet.isRowHiddenByFilter(i + 1)) { // +1 because rows are 1-indexed
      visibleRows.push(values[i]);
    }
  }
  
  // Clear the target sheet but preserve formatting
  if (targetSheet.getLastRow() > 0) {
    targetSheet.getRange(1, 1, targetSheet.getLastRow(), targetSheet.getLastColumn()).clearContent();
  }
  
  // Write data to target sheet if we have visible rows
  if (visibleRows.length > 0) {
    targetSheet.getRange(1, 1, visibleRows.length, numCols).setValues(visibleRows);
  }
  
  Logger.log(`Copied ${visibleRows.length - 1} visible rows (plus header row) to "Filtered View" sheet`);
}

/**
 * Add menu item when spreadsheet opens
 */
function onOpen() {
  const ui = SpreadsheetApp.getUi();
  ui.createMenu('Aircraft Data')
    .addItem('Copy Visible Rows to Filtered View', 'copyVisibleRows')
    .addToUi();
} 