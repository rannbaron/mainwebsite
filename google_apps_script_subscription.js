/**
 * Google Apps Script for NC Early Voting Daily Intelligence Subscriptions
 * ------------------------------------------------------------------------
 * FEATURES:
 * 1. Accepts POST requests from the website subscription form.
 * 2. Deduplicates subscribers and logs them to your connected Google Sheet.
 * 3. FIRST-TIME SUBSCRIBER IMMEDIATE DISPATCH:
 *    When a new user subscribes, immediately fetches the latest published
 *    daily update report and delivers it directly to their inbox!
 * 4. ONE-CLICK UNSUBSCRIBE / RESUBSCRIBE:
 *    Handles `action=unsubscribe` and `action=resubscribe` with a beautiful
 *    confirmation page, and marks the user's status in the Google Sheet.
 * 5. Responds to GET requests with active subscriber list for the morning batch pipeline.
 * 6. Includes `testSendWelcome` to easily grant email permissions and test delivery.
 * 
 * HOW TO ACTIVATE / DEPLOY IN GOOGLE APPS SCRIPT:
 * 1. Paste this entire file into your Apps Script editor and click the Save icon (Ctrl+S).
 * 2. Select `testSendWelcome` from the function dropdown at the top and click "Run" (▶).
 *    -> Grant permissions if prompted (Review permissions -> Advanced -> Allow).
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
 * to a brand-new subscriber with their personalized unsubscribe link.
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
      
      // Inject personalized unsubscribe URL
      var scriptUrl = ScriptApp.getService().getUrl();
      var unsubUrl = scriptUrl + "?action=unsubscribe&email=" + encodeURIComponent(recipientEmail);
      htmlBody = htmlBody.replace(/\{\{UNSUBSCRIBE_URL\}\}/g, unsubUrl).replace(/\{UNSUBSCRIBE_URL\}/g, unsubUrl);
      plainBody = plainBody.replace(/\{\{UNSUBSCRIBE_URL\}\}/g, unsubUrl).replace(/\{UNSUBSCRIBE_URL\}/g, unsubUrl);

      MailApp.sendEmail({
        to: recipientEmail,
        subject: subject,
        body: plainBody,
        htmlBody: htmlBody,
        name: "NC Early Voting Intelligence",
        replyTo: "baronrann@gmail.com"
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
  
  var scriptUrl = ScriptApp.getService().getUrl();
  var unsubUrl = scriptUrl + "?action=unsubscribe&email=" + encodeURIComponent(testEmail);
  var html = (data.html || "").replace(/\{\{UNSUBSCRIBE_URL\}\}/g, unsubUrl).replace(/\{UNSUBSCRIBE_URL\}/g, unsubUrl);
  var text = (data.text || "").replace(/\{\{UNSUBSCRIBE_URL\}\}/g, unsubUrl).replace(/\{UNSUBSCRIBE_URL\}/g, unsubUrl);

  MailApp.sendEmail({
    to: testEmail,
    subject: data.subject,
    body: text,
    htmlBody: html,
    name: "NC Early Voting Intelligence",
    replyTo: "baronrann@gmail.com"
  });
  
  Logger.log("SUCCESS! Welcome email dispatched to: " + testEmail);
}

// Handles GET requests (Unsubscribe, Resubscribe, or pipeline subscriber list)
function doGet(e) {
  try {
    setupSheet();
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    var rows = sheet.getDataRange().getValues();

    var action = (e && e.parameter && e.parameter.action) ? e.parameter.action.toLowerCase() : "";
    var email = (e && e.parameter && e.parameter.email) ? e.parameter.email.trim().toLowerCase() : "";

    // 1. Handle One-Click Unsubscribe
    if (action === "unsubscribe") {
      var found = false;
      if (email) {
        for (var i = 1; i < rows.length; i++) {
          if (rows[i][1] && rows[i][1].toString().trim().toLowerCase() === email) {
            sheet.getRange(i + 1, 3).setValue("unsubscribed");
            found = true;
            break;
          }
        }
      }
      var resubUrl = ScriptApp.getService().getUrl() + "?action=resubscribe&email=" + encodeURIComponent(email);
      var html = renderUnsubscribeHtml(email, found, resubUrl);
      return HtmlService.createHtmlOutput(html)
        .setTitle("Unsubscribed - NC Early Voting Intelligence")
        .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
    }

    // 2. Handle Resubscribe
    if (action === "resubscribe") {
      if (email) {
        for (var i = 1; i < rows.length; i++) {
          if (rows[i][1] && rows[i][1].toString().trim().toLowerCase() === email) {
            sheet.getRange(i + 1, 3).setValue("active");
            break;
          }
        }
      }
      var html = renderResubscribeHtml(email);
      return HtmlService.createHtmlOutput(html)
        .setTitle("Resubscribed - NC Early Voting Intelligence")
        .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
    }

    // 3. Default: Return active and unsubscribed lists for Python pipeline
    var subscribers = [];
    var unsubscribed = [];

    for (var i = 1; i < rows.length; i++) {
      var em = rows[i][1] ? rows[i][1].toString().trim().toLowerCase() : "";
      var status = rows[i][2] ? rows[i][2].toString().trim().toLowerCase() : "active";
      if (em && em.indexOf("@") !== -1) {
        if (status === "active") {
          if (subscribers.indexOf(em) === -1) subscribers.push(em);
        } else if (status === "unsubscribed") {
          if (unsubscribed.indexOf(em) === -1) unsubscribed.push(em);
        }
      }
    }

    return ContentService.createTextOutput(JSON.stringify({
      subscribers: subscribers,
      unsubscribed: unsubscribed
    })).setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ subscribers: [], unsubscribed: [], error: err.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function renderUnsubscribeHtml(email, unsubscribed, resubUrl) {
  var title = unsubscribed ? "Unsubscribed" : "Unsubscribe";
  var bodyContent = "";

  if (unsubscribed) {
    bodyContent = [
      '<div style="width:52px;height:52px;background:#ecfdf5;color:#059669;border-radius:50%;display:flex;align-items:center;justify-content:center;margin:0 auto 16px;font-size:26px;">&#10003;</div>',
      '<h1 style="font-size:20px;font-weight:700;color:#0f172a;margin:0 0 8px;">You have been unsubscribed</h1>',
      '<p style="color:#64748b;font-size:14px;line-height:1.6;margin:0 0 24px;">',
      '  <strong>' + escapeHtml(email) + '</strong> has been removed from daily dispatches. You will no longer receive morning early voting updates.',
      '</p>',
      '<div style="display:flex;flex-direction:column;gap:12px;align-items:center;">',
      '  <a href="' + resubUrl + '" style="font-size:13px;color:#2563eb;text-decoration:none;font-weight:600;">Unsubscribed by mistake? Click here to re-subscribe</a>',
      '  <a href="https://rannbar-on.com/beta/" style="display:inline-block;background:#0f172a;color:#ffffff;padding:10px 22px;border-radius:8px;font-size:13px;font-weight:600;text-decoration:none;margin-top:8px;">Return to Early Voting Explorer &rarr;</a>',
      '</div>'
    ].join("\n");
  } else {
    var formAction = ScriptApp.getService().getUrl();
    bodyContent = [
      '<h1 style="font-size:20px;font-weight:700;color:#0f172a;margin:0 0 8px;">Unsubscribe from Updates</h1>',
      '<p style="color:#64748b;font-size:14px;line-height:1.6;margin:0 0 20px;">',
      (email ? 'The email <strong>' + escapeHtml(email) + '</strong> was not found in our active list.' : 'Enter your email address below to unsubscribe from daily morning early voting reports.'),
      '</p>',
      '<form method="GET" action="' + formAction + '" style="display:flex;flex-direction:column;gap:12px;">',
      '  <input type="hidden" name="action" value="unsubscribe">',
      '  <input type="email" name="email" required placeholder="Enter your email address" value="' + escapeHtml(email) + '" style="padding:10px 14px;border:1px solid #cbd5e1;border-radius:8px;font-size:14px;outline:none;">',
      '  <button type="submit" style="background:#dc2626;color:#ffffff;border:none;padding:10px 16px;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer;">Confirm Unsubscribe</button>',
      '</form>',
      '<div style="margin-top:20px;text-align:center;">',
      '  <a href="https://rannbar-on.com/beta/" style="color:#64748b;font-size:13px;text-decoration:none;">&larr; Return to Interactive Map</a>',
      '</div>'
    ].join("\n");
  }

  return [
    '<!DOCTYPE html>',
    '<html>',
    '<head>',
    '  <meta charset="utf-8">',
    '  <meta name="viewport" content="width=device-width, initial-scale=1">',
    '  <title>' + title + ' - NC Early Voting Intelligence</title>',
    '  <style>',
    '    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #070b14; color: #f8fafc; margin: 0; padding: 24px; min-height: 100vh; display: flex; align-items: center; justify-content: center; box-sizing: border-box; }',
    '    .card { background: #ffffff; color: #0f172a; border-radius: 16px; max-width: 480px; width: 100%; padding: 32px 28px; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.4), 0 10px 10px -5px rgba(0, 0, 0, 0.2); text-align: center; }',
    '  </style>',
    '</head>',
    '<body>',
    '  <div class="card">',
    bodyContent,
    '  </div>',
    '</body>',
    '</html>'
  ].join("\n");
}

function renderResubscribeHtml(email) {
  return [
    '<!DOCTYPE html>',
    '<html>',
    '<head>',
    '  <meta charset="utf-8">',
    '  <meta name="viewport" content="width=device-width, initial-scale=1">',
    '  <title>Re-subscribed - NC Early Voting Intelligence</title>',
    '  <style>',
    '    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #070b14; color: #f8fafc; margin: 0; padding: 24px; min-height: 100vh; display: flex; align-items: center; justify-content: center; box-sizing: border-box; }',
    '    .card { background: #ffffff; color: #0f172a; border-radius: 16px; max-width: 480px; width: 100%; padding: 32px 28px; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.4), 0 10px 10px -5px rgba(0, 0, 0, 0.2); text-align: center; }',
    '  </style>',
    '</head>',
    '<body>',
    '  <div class="card">',
    '    <div style="width:52px;height:52px;background:#eff6ff;color:#2563eb;border-radius:50%;display:flex;align-items:center;justify-content:center;margin:0 auto 16px;font-size:26px;">&#10003;</div>',
    '    <h1 style="font-size:20px;font-weight:700;color:#0f172a;margin:0 0 8px;">Subscription Re-activated!</h1>',
    '    <p style="color:#64748b;font-size:14px;line-height:1.6;margin:0 0 24px;">',
    '      <strong>' + escapeHtml(email) + '</strong> has been re-subscribed to daily morning early voting updates.',
    '    </p>',
    '    <a href="https://rannbar-on.com/beta/" style="display:inline-block;background:#2563eb;color:#ffffff;padding:10px 22px;border-radius:8px;font-size:13px;font-weight:600;text-decoration:none;">Open Early Voting Explorer &rarr;</a>',
    '  </div>',
    '</body>',
    '</html>'
  ].join("\n");
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

function renderUnsubscribeHtml(email, unsubscribed, resubUrl) {
  var title = unsubscribed ? "Unsubscribed" : "Unsubscribe";
  var bodyContent = "";

  if (unsubscribed) {
    bodyContent = [
      '<div style="width:52px;height:52px;background:#ecfdf5;color:#059669;border-radius:50%;display:flex;align-items:center;justify-content:center;margin:0 auto 16px;font-size:26px;">&#10003;</div>',
      '<h1 style="font-size:20px;font-weight:700;color:#0f172a;margin:0 0 8px;">You have been unsubscribed</h1>',
      '<p style="color:#64748b;font-size:14px;line-height:1.6;margin:0 0 24px;">',
      '  <strong>' + escapeHtml(email) + '</strong> has been removed from daily dispatches. You will no longer receive morning early voting updates.',
      '</p>',
      '<div style="display:flex;flex-direction:column;gap:12px;align-items:center;">',
      '  <a href="' + resubUrl + '" style="font-size:13px;color:#2563eb;text-decoration:none;font-weight:600;">Unsubscribed by mistake? Click here to re-subscribe</a>',
      '  <a href="https://rannbar-on.com/beta/" style="display:inline-block;background:#0f172a;color:#ffffff;padding:10px 22px;border-radius:8px;font-size:13px;font-weight:600;text-decoration:none;margin-top:8px;">Return to Early Voting Explorer &rarr;</a>',
      '</div>'
    ].join("\n");
  } else {
    var formAction = ScriptApp.getService().getUrl();
    bodyContent = [
      '<h1 style="font-size:20px;font-weight:700;color:#0f172a;margin:0 0 8px;">Unsubscribe from Updates</h1>',
      '<p style="color:#64748b;font-size:14px;line-height:1.6;margin:0 0 20px;">',
      (email ? 'The email <strong>' + escapeHtml(email) + '</strong> was not found in our active list.' : 'Enter your email address below to unsubscribe from daily morning early voting reports.'),
      '</p>',
      '<form method="GET" action="' + formAction + '" style="display:flex;flex-direction:column;gap:12px;">',
      '  <input type="hidden" name="action" value="unsubscribe">',
      '  <input type="email" name="email" required placeholder="Enter your email address" value="' + escapeHtml(email) + '" style="padding:10px 14px;border:1px solid #cbd5e1;border-radius:8px;font-size:14px;outline:none;">',
      '  <button type="submit" style="background:#dc2626;color:#ffffff;border:none;padding:10px 16px;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer;">Confirm Unsubscribe</button>',
      '</form>',
      '<div style="margin-top:20px;text-align:center;">',
      '  <a href="https://rannbar-on.com/beta/" style="color:#64748b;font-size:13px;text-decoration:none;">&larr; Return to Interactive Map</a>',
      '</div>'
    ].join("\n");
  }

  return [
    '<!DOCTYPE html>',
    '<html>',
    '<head>',
    '  <meta charset="utf-8">',
    '  <meta name="viewport" content="width=device-width, initial-scale=1">',
    '  <title>' + title + ' - NC Early Voting Intelligence</title>',
    '  <style>',
    '    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #070b14; color: #f8fafc; margin: 0; padding: 24px; min-height: 100vh; display: flex; align-items: center; justify-content: center; box-sizing: border-box; }',
    '    .card { background: #ffffff; color: #0f172a; border-radius: 16px; max-width: 480px; width: 100%; padding: 32px 28px; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.4), 0 10px 10px -5px rgba(0, 0, 0, 0.2); text-align: center; }',
    '  </style>',
    '</head>',
    '<body>',
    '  <div class="card">',
    bodyContent,
    '  </div>',
    '</body>',
    '</html>'
  ].join("\n");
}

function renderResubscribeHtml(email) {
  return [
    '<!DOCTYPE html>',
    '<html>',
    '<head>',
    '  <meta charset="utf-8">',
    '  <meta name="viewport" content="width=device-width, initial-scale=1">',
    '  <title>Re-subscribed - NC Early Voting Intelligence</title>',
    '  <style>',
    '    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #070b14; color: #f8fafc; margin: 0; padding: 24px; min-height: 100vh; display: flex; align-items: center; justify-content: center; box-sizing: border-box; }',
    '    .card { background: #ffffff; color: #0f172a; border-radius: 16px; max-width: 480px; width: 100%; padding: 32px 28px; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.4), 0 10px 10px -5px rgba(0, 0, 0, 0.2); text-align: center; }',
    '  </style>',
    '</head>',
    '<body>',
    '  <div class="card">',
    '    <div style="width:52px;height:52px;background:#eff6ff;color:#2563eb;border-radius:50%;display:flex;align-items:center;justify-content:center;margin:0 auto 16px;font-size:26px;">&#10003;</div>',
    '    <h1 style="font-size:20px;font-weight:700;color:#0f172a;margin:0 0 8px;">Subscription Re-activated!</h1>',
    '    <p style="color:#64748b;font-size:14px;line-height:1.6;margin:0 0 24px;">',
    '      <strong>' + escapeHtml(email) + '</strong> has been re-subscribed to daily morning early voting updates.',
    '    </p>',
    '    <a href="https://rannbar-on.com/beta/" style="display:inline-block;background:#2563eb;color:#ffffff;padding:10px 22px;border-radius:8px;font-size:13px;font-weight:600;text-decoration:none;">Open Early Voting Explorer &rarr;</a>',
    '  </div>',
    '</body>',
    '</html>'
  ].join("\n");
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

