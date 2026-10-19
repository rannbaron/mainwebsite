/**
 * Google Apps Script for NC Early Voting Daily Intelligence Subscriptions
 * ------------------------------------------------------------------------
 * HOW TO DEPLOY:
 * 1. Open Google Sheets (https://sheets.new) and name the spreadsheet:
 *    "NC Early Voting 2026 Subscribers"
 * 2. In the menu, go to: Extensions -> Apps Script
 * 3. Delete any code in the editor and paste this entire file.
 * 4. Click "Deploy" (top right) -> "New deployment"
 * 5. Select type: "Web app"
 * 6. Set Description: "NC Early Voting Subscriptions"
 * 7. Set "Execute as": "Me"
 * 8. Set "Who has access": "Anyone"  <-- CRITICAL for accepting web form signups
 * 9. Click "Deploy" and authorize access.
 * 10. Copy the Web App URL (starts with https://script.google.com/macros/s/.../exec)
 * 
 * 11. Connect it:
 *     a. In `index.html`, set:
 *        const SUBSCRIPTION_ENDPOINT = "https://script.google.com/macros/s/.../exec";
 *     b. In GitHub Repository Settings -> Secrets and variables -> Actions:
 *        Add Secret: SUBSCRIBERS_REMOTE_URL = https://script.google.com/macros/s/.../exec
 */

function setupSheet() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  if (sheet.getLastRow() === 0) {
    sheet.appendRow(["Timestamp", "Email", "Status", "Source"]);
    sheet.getRange(1, 1, 1, 4).setFontWeight("bold").setBackground("#0f172a").setFontColor("#f8fafc");
  }
}

// Handles POST requests from the website subscription form
function doPost(e) {
  try {
    setupSheet();
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    
    var email = "";
    var source = "web";
    
    if (e && e.postData && e.postData.contents) {
      try {
        var data = JSON.parse(e.postData.contents);
        email = data.email || "";
        source = data.source || "web";
      } catch (err) {
        email = e.parameter.email || "";
        source = e.parameter.source || "form";
      }
    } else if (e && e.parameter) {
      email = e.parameter.email || "";
      source = e.parameter.source || "form";
    }

    email = email.trim().toLowerCase();
    
    if (!email || email.indexOf("@") === -1) {
      return ContentService.createTextOutput(JSON.stringify({ status: "error", message: "Invalid email" }))
        .setMimeType(ContentService.MimeType.JSON);
    }

    // Check if already in sheet
    var rows = sheet.getDataRange().getValues();
    var foundIndex = -1;
    for (var i = 1; i < rows.length; i++) {
      if (rows[i][1] && rows[i][1].toString().toLowerCase() === email) {
        foundIndex = i + 1;
        break;
      }
    }

    if (foundIndex > 0) {
      // Reactivate if unsubscribed
      sheet.getRange(foundIndex, 3).setValue("active");
    } else {
      sheet.appendRow([new Date(), email, "active", source]);
    }

    return ContentService.createTextOutput(JSON.stringify({ status: "success", email: email }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ status: "error", message: err.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

// Handles GET requests from GitHub Actions / Python to retrieve active subscriber list
function doGet(e) {
  try {
    setupSheet();
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    var rows = sheet.getDataRange().getValues();
    var subscribers = [];

    for (var i = 1; i < rows.length; i++) {
      var email = rows[i][1] ? rows[i][1].toString().trim().toLowerCase() : "";
      var status = rows[i][2] ? rows[i][2].toString().trim().toLowerCase() : "active";
      if (email && email.indexOf("@") !== -1 && status === "active") {
        if (subscribers.indexOf(email) === -1) {
          subscribers.push(email);
        }
      }
    }

    return ContentService.createTextOutput(JSON.stringify({ subscribers: subscribers }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ subscribers: [], error: err.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}
