/**
 * Google Apps Script for NC Early Voting Daily Intelligence Subscriptions
 * ------------------------------------------------------------------------
 * FEATURES:
 * 1. Accepts POST requests from the website subscription form.
 * 2. Deduplicates subscribers and logs them to your connected Google Sheet.
 * 3. FIRST-TIME SUBSCRIBER IMMEDIATE DISPATCH:
 *    When a new user subscribes, immediately fetches the latest published
 *    daily update report and delivers it directly to their inbox!
 * 4. Responds to GET requests with active subscriber list for the morning batch pipeline.
 * 5. Includes an un-caught `testSendWelcome` function to force Google's Authorization dialog.
 * 
 * HOW TO ACTIVATE / DEPLOY IN GOOGLE APPS SCRIPT:
 * 1. Paste this entire file into your Apps Script editor and click the Save icon (Ctrl+S).
 * 2. Select `testSendWelcome` from the function dropdown at the top and click "Run" (▶).
 *    -> Because this function is uncaught, Google will immediately prompt you:
 *       "Authorization Required: NC Early Voting Subscriptions needs permission to access your data."
 *    -> Click "Review permissions" -> Choose your Google Account -> Click "Advanced" -> Click "Go to NC Early Voting (unsafe)" -> Click "Allow".
 *    -> You will receive the Day 5 report in your inbox immediately!
 * 3. Click "Deploy" (top right) -> "Manage deployments".
 * 4. Click the edit icon (pencil) next to the Active Web App deployment.
 * 5. Change Version to: "New version".
 * 6. Click "Deploy".
 */

function setupSheet() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  if (sheet.getLastRow() === 0) {
    sheet.appendRow(["Timestamp", "Email", "Status", "Source", "Welcome Sent"]);
    sheet.getRange(1, 1, 1, 5).setFontWeight("bold").setBackground("#0f172a").setFontColor("#f8fafc");
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
      // Existing subscriber
      sheet.getRange(foundIndex, 3).setValue("active");
      
      // If welcome email was never sent to this address, send it now!
      var alreadySent = (rows[foundIndex - 1].length >= 5) ? rows[foundIndex - 1][4] : "";
      if (!alreadySent || alreadySent.toString().toLowerCase() !== "yes") {
        sentImmediate = sendWelcomeUpdateEmail(email);
        if (sentImmediate) {
          sheet.getRange(foundIndex, 5).setValue("yes");
        }
      }
    } else {
      // First-time subscriber: Record to sheet and send today's update report immediately!
      sentImmediate = sendWelcomeUpdateEmail(email);
      sheet.appendRow([new Date(), email, "active", source, sentImmediate ? "yes" : "pending"]);
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
    // Use canonical custom domain to avoid 301 redirects
    var url = "https://rannbar-on.com/latest_daily_email.json";
    var resp = UrlFetchApp.fetch(url, { muteHttpExceptions: true, followRedirects: true });
    var statusCode = resp.getResponseCode();
    
    // Fallback if needed
    if (statusCode !== 200) {
      url = "https://rannbaron.github.io/mainwebsite/latest_daily_email.json";
      resp = UrlFetchApp.fetch(url, { muteHttpExceptions: true, followRedirects: true });
      statusCode = resp.getResponseCode();
    }
    
    if (statusCode === 200) {
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
      Logger.log("Could not fetch latest_daily_email.json: HTTP " + statusCode);
      return false;
    }
  } catch (err) {
    Logger.log("Error sending immediate welcome email to " + recipientEmail + ": " + err.toString());
    return false;
  }
}

/**
 * Run this function ONCE inside the Apps Script editor to authorize email permissions
 * and immediately test delivery to your email address!
 * 
 * NOTE: This function intentionally does NOT catch errors so Google Apps Script
 * will halt and pop up the "Authorization Required" dialog!
 */
function testSendWelcome() {
  var testEmail = "rb6@duke.edu";
  Logger.log("Initiating test delivery to: " + testEmail);
  
  // Direct call forces Google Apps Script to request missing UrlFetchApp and MailApp permissions:
  var url = "https://rannbar-on.com/latest_daily_email.json";
  var resp = UrlFetchApp.fetch(url);
  var data = JSON.parse(resp.getContentText());
  
  MailApp.sendEmail({
    to: testEmail,
    subject: data.subject,
    body: data.text,
    htmlBody: data.html,
    name: "NC Early Voting Intelligence"
  });
  
  Logger.log("SUCCESS! Welcome email dispatched to: " + testEmail);
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
