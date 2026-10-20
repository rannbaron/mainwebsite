/**
 * Google Apps Script for NC Early Voting Daily Intelligence Subscriptions
 * ------------------------------------------------------------------------
 * FEATURES:
 * 1. Accepts POST requests from the website subscription form.
 * 2. Deduplicates subscribers and logs them to your connected Google Sheet.
 * 3. FIRST-TIME SUBSCRIBER IMMEDIATE DISPATCH:
 *    When a new user subscribes for the first time, immediately fetches
 *    the latest published daily update report from GitHub Pages and sends
 *    it directly to their inbox!
 * 4. Responds to GET requests with active subscriber list for the morning batch pipeline.
 * 
 * HOW TO UPDATE / DEPLOY IN GOOGLE APPS SCRIPT:
 * 1. Open your Apps Script project (from Extensions -> Apps Script in your spreadsheet).
 * 2. Replace the editor contents with this file and click the Save icon.
 * 3. Click "Deploy" (top right) -> "Manage deployments".
 * 4. Click the edit icon (pencil) next to the Active Web App deployment.
 * 5. Change Version to: "New version".
 * 6. Click "Deploy".
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

    var isNew = (foundIndex === -1);
    var sentImmediate = false;

    if (foundIndex > 0) {
      // Existing subscriber: reactivate if unsubscribed
      sheet.getRange(foundIndex, 3).setValue("active");
    } else {
      // First-time subscriber: Record to sheet and send today's update report immediately!
      sheet.appendRow([new Date(), email, "active", source]);
      sentImmediate = sendWelcomeUpdateEmail(email);
    }

    return ContentService.createTextOutput(JSON.stringify({
      status: "success",
      email: email,
      is_new: isNew,
      immediate_email_sent: sentImmediate
    })).setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ status: "error", message: err.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * Fetches today's published daily update email and immediately delivers it
 * to a brand-new subscriber.
 */
function sendWelcomeUpdateEmail(recipientEmail) {
  try {
    var url = "https://rannbaron.github.io/mainwebsite/latest_daily_email.json";
    var resp = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
    
    if (resp.getResponseCode() === 200) {
      var data = JSON.parse(resp.getContentText());
      var subject = data.subject || "NC Early Voting Daily Update";
      var htmlBody = data.html || "";
      var plainBody = data.text || "Please view this email in an HTML-compatible client.";
      
      MailApp.sendEmail({
        to: recipientEmail,
        subject: subject,
        body: plainBody,
        htmlBody: htmlBody,
        name: "NC Early Voting Intelligence"
      });
      Logger.log("Successfully dispatched immediate welcome update email to: " + recipientEmail);
      return true;
    } else {
      Logger.log("Could not fetch latest_daily_email.json: HTTP " + resp.getResponseCode());
      return false;
    }
  } catch (err) {
    Logger.log("Error sending immediate welcome email to " + recipientEmail + ": " + err.toString());
    return false;
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
