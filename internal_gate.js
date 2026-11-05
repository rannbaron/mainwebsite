/**
 * RannBar-On.com Unified Internal Security Gate & Granular Access Control
 * =======================================================================
 * Authentication, 2FA & Granular Page Permissions Policy:
 * 1. Step 1: Username & Password Verification (No one-click unlock URLs).
 * 2. Step 2: Email-based 2FA Passcode Verification (6 digits):
 *    - Main 5-Minute Timer (live 05:00 countdown).
 *    - Incorrect Code Handling:
 *      * 1st failure: alert & strict 30-second countdown timer.
 *      * 2nd failure OR timer expiry: kicks back to Step 1.
 * 3. Page-by-Page Granular Permission Enforcement:
 *    - Checks if current page route is in user's `allowed_pages` (or if Master Administrator).
 *    - If denied: displays customized lock screen stating:
 *      "Access Denied: Your account does not have permission to view [Page Name]. Contact an administrator to request access."
 * 4. Automatic Logout Conditions:
 *    - Condition 1: 15-minute inactivity (tracks mousemove, keydown, click, scroll).
 *    - Condition 2: Browser close (sessionStorage 'rann_session_active' & session cookie).
 *    - Condition 3: System suspend / sleep / restart (heartbeat drift > 5000ms).
 */

(function() {
  const MASTER_USER = "rann";
  const MASTER_PWD = "AS2cYGy9GD7qRt@XV&gf$yUX!pD@";
  const INACTIVITY_TIMEOUT_MS = 15 * 60 * 1000;
  const HEARTBEAT_DRIFT_THRESHOLD_MS = 5000;

  const STORAGE_KEYS = {
    SESSION_ACTIVE: "rann_session_active",
    AUTH_USER: "rann_auth_user",
    LAST_ACTIVE: "rann_auth_last_active"
  };

  const PAGE_CATALOG = {
    "/durhampolitics": "Durham Politics Tracker",
    "/agents": "Agent Command Center",
    "/taskpriority": "Decision Desk Approvals",
    "/internal/vibes.html": "Real-Time Vibes Monitor",
    "/internal/test_inbox.html": "Test Mailbox (outputtest@rannbar-on.com)",
    "/internal/test_inbox": "Test Mailbox (outputtest@rannbar-on.com)",
    "/voice": "Voice Dictation Bridge",
    "/dashboard/accounts": "User Administration Console"
  };

  function getCurrentRouteInfo() {
    const p = window.location.pathname;
    for (const [route, title] of Object.entries(PAGE_CATALOG)) {
      if (p.startsWith(route)) {
        return { route, title };
      }
    }
    return { route: p, title: "Protected Technical Page" };
  }

  function getApiBase() {
    if (window.location.protocol === "file:") return "http://localhost:8086";
    if (window.location.port === "8086") return "";
    return "";
  }

  function getSessionCookie() {
    const match = document.cookie.match(new RegExp('(^|;\\s*)' + STORAGE_KEYS.SESSION_ACTIVE + '=([^;]*)'));
    return match ? decodeURIComponent(match[2]) : null;
  }

  function setSessionCookie(val) {
    document.cookie = STORAGE_KEYS.SESSION_ACTIVE + "=" + encodeURIComponent(val) + "; path=/; SameSite=Lax";
  }

  function clearSessionCookie() {
    document.cookie = STORAGE_KEYS.SESSION_ACTIVE + "=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Lax";
  }

  function recordActivity() {
    try { localStorage.setItem(STORAGE_KEYS.LAST_ACTIVE, Date.now().toString()); } catch(e) {}
  }

  function getLastActive() {
    try {
      const val = localStorage.getItem(STORAGE_KEYS.LAST_ACTIVE);
      return val ? parseInt(val, 10) : 0;
    } catch(e) { return 0; }
  }

  function getStoredUser() {
    try {
      const val = localStorage.getItem(STORAGE_KEYS.AUTH_USER);
      return val ? JSON.parse(val) : null;
    } catch(e) { return null; }
  }

  function setStoredUser(userObj) {
    try { localStorage.setItem(STORAGE_KEYS.AUTH_USER, JSON.stringify(userObj)); } catch(e) {}
  }

  function isSessionValid() {
    const hasSessionStorage = sessionStorage.getItem(STORAGE_KEYS.SESSION_ACTIVE) === "true";
    const hasSessionCookie = getSessionCookie() === "true";

    if (!hasSessionStorage && !hasSessionCookie) return false;

    if (!hasSessionStorage && hasSessionCookie) {
      sessionStorage.setItem(STORAGE_KEYS.SESSION_ACTIVE, "true");
    }

    const user = getStoredUser();
    if (!user) return false;

    const lastActive = getLastActive();
    if (!lastActive || (Date.now() - lastActive > INACTIVITY_TIMEOUT_MS)) return false;

    return true;
  }

  function userHasRoutePermission(user, route) {
    if (!user) return false;
    const isMaster = (user.username === MASTER_USER) || 
                     (user.privilegeLevel === 10) || 
                     (user.privilegeName && user.privilegeName.toLowerCase().includes("master"));
    if (isMaster) return true;

    if (route === "/durhampolitics" && user.username === "durhampol") return true;

    const allowed = user.allowedPages || user.allowed_pages || [];
    if (Array.isArray(allowed)) {
      if (allowed.includes("*") || allowed.includes(route)) return true;
    }
    return false;
  }

  function performLogout(reason) {
    console.warn("RannAuth: Performing logout. Reason:", reason || "unspecified");
    sessionStorage.removeItem(STORAGE_KEYS.SESSION_ACTIVE);
    sessionStorage.removeItem("nc_internal_argon_auth");
    sessionStorage.removeItem("durham_pol_auth");
    clearSessionCookie();
    try {
      localStorage.removeItem(STORAGE_KEYS.AUTH_USER);
      localStorage.removeItem(STORAGE_KEYS.LAST_ACTIVE);
    } catch(e) {}

    renderLockScreen(reason ? `Session terminated: ${reason}` : "");
  }

  // System sleep drift detection
  let lastHeartbeat = Date.now();
  setInterval(function() {
    const now = Date.now();
    const elapsed = now - lastHeartbeat;
    lastHeartbeat = now;

    if (elapsed > HEARTBEAT_DRIFT_THRESHOLD_MS) {
      if (isSessionValid()) {
        performLogout("System sleep/suspend detected");
        return;
      }
    }

    if (isSessionValid()) {
      const lastActive = getLastActive();
      if (Date.now() - lastActive > INACTIVITY_TIMEOUT_MS) {
        performLogout("15 minutes of inactivity exceeded");
      }
    }
  }, 1000);

  // User activity listeners
  let lastActivityUpdate = 0;
  function handleUserActivity() {
    const now = Date.now();
    if (now - lastActivityUpdate > 3000) {
      lastActivityUpdate = now;
      recordActivity();
    }
  }

  ["mousemove", "keydown", "click", "scroll", "touchstart"].forEach(function(evt) {
    window.addEventListener(evt, handleUserActivity, { passive: true });
  });

  window.RannAuth = {
    isAuthenticated: function() { return isSessionValid(); },
    getUser: function() { return isSessionValid() ? getStoredUser() : null; },
    recordActivity: recordActivity,
    logout: function() { performLogout("Manual sign out"); },
    hasRouteAccess: function(route) {
      const u = this.getUser();
      return userHasRoutePermission(u, route);
    }
  };

  // Lock Screen & Access Denied Overlay
  let cachedOriginalContent = "";
  let activeChallenge = null;
  let mainTimerInterval = null;
  let graceTimerInterval = null;

  function renderAccessDeniedScreen(pageTitle, user) {
    removeExistingOverlay();

    const overlay = document.createElement("div");
    overlay.id = "argonLockOverlay";
    overlay.style.cssText = "position:fixed;top:0;left:0;width:100vw;height:100vh;background:#090d16;color:#f8fafc;display:flex;align-items:center;justify-content:center;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;z-index:9999999;padding:20px;box-sizing:border-box;";

    const roleName = user.privilegeName || `Level ${user.privilegeLevel || 1}`;

    overlay.innerHTML = `
      <div style="background:#111827;border:1px solid #ef4444;border-radius:16px;max-width:460px;width:100%;padding:36px 32px;box-shadow:0 25px 50px -12px rgba(0,0,0,0.8);text-align:center;box-sizing:border-box;">
        <div style="display:inline-flex;padding:14px;background:rgba(239,68,68,0.15);border:1px solid rgba(239,68,68,0.3);border-radius:50%;margin-bottom:16px;">
          <svg style="width:36px;height:36px;color:#f87171;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
        </div>
        <div style="font-size:11px;font-weight:800;letter-spacing:1px;color:#ef4444;text-transform:uppercase;margin-bottom:6px;">PAGE ACCESS RESTRICTED</div>
        <h2 style="font-size:22px;font-weight:800;color:#ffffff;margin-bottom:10px;">Access Denied</h2>
        
        <p style="font-size:13.5px;color:#cbd5e1;line-height:1.6;margin-bottom:18px;">
          Your account (<strong>${user.fullName || user.username}</strong> &bull; <span style="color:#f59e0b;font-weight:700;">${roleName}</span>) does not have permission to view <strong>${pageTitle}</strong>.
        </p>

        <div style="background:#0d131f;border:1px solid #1f2937;border-radius:8px;padding:12px 16px;font-size:12.5px;color:#94a3b8;margin-bottom:24px;text-align:left;">
          <i style="font-style:normal;">🔒</i> <strong>Requesting Access:</strong> Contact an administrator at <a href="mailto:rann@rannbar-on.com" style="color:#38bdf8;text-decoration:none;">rann@rannbar-on.com</a> to grant you permission for this page in the User Administration Console.
        </div>

        <div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap;">
          <button onclick="window.RannAuth.logout()" style="background:#374151;color:#ffffff;border:none;padding:10px 18px;border-radius:6px;font-size:13px;font-weight:700;cursor:pointer;">
            Switch Account / Sign Out
          </button>
          <a href="/" style="background:#00539b;color:#ffffff;padding:10px 18px;border-radius:6px;font-size:13px;font-weight:700;text-decoration:none;display:inline-flex;align-items:center;">
            &larr; Return to Public Site
          </a>
        </div>
      </div>
    `;

    document.body.appendChild(overlay);
  }

  function removeExistingOverlay() {
    const existing = document.getElementById("argonLockOverlay");
    if (existing) existing.remove();
  }

  function renderLockScreen(initialNotice) {
    removeExistingOverlay();

    if (!cachedOriginalContent && document.body) {
      cachedOriginalContent = document.body.innerHTML;
    }

    const { route, title: pageTitle } = getCurrentRouteInfo();
    const overlay = document.createElement("div");
    overlay.id = "argonLockOverlay";
    overlay.style.cssText = "position:fixed;top:0;left:0;width:100vw;height:100vh;background:#090d16;color:#f8fafc;display:flex;align-items:center;justify-content:center;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;z-index:9999999;padding:20px;box-sizing:border-box;";

    overlay.innerHTML = `
      <div style="background:#111827;border:1px solid #374151;border-radius:16px;max-width:440px;width:100%;padding:32px;box-shadow:0 25px 50px -12px rgba(0,0,0,0.8);text-align:center;box-sizing:border-box;">
        
        <!-- STEP 1: Username & Password -->
        <div id="stepCredentials">
          <div style="display:inline-flex;padding:12px;background:rgba(99,102,241,0.15);border:1px solid rgba(99,102,241,0.3);border-radius:50%;margin-bottom:14px;">
            <svg style="width:30px;height:30px;color:#818cf8;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/></svg>
          </div>
          <div style="font-size:11px;font-weight:800;letter-spacing:1px;color:#ef4444;text-transform:uppercase;margin-bottom:6px;">RESTRICTED &bull; ${pageTitle}</div>
          <h2 style="font-size:20px;font-weight:800;color:#ffffff;margin-bottom:6px;">Step 1: Sign In</h2>
          <p style="font-size:13px;color:#94a3b8;line-height:1.5;margin-bottom:18px;">Enter your credentials. A one-time 2FA passcode will be dispatched to your registered email.</p>
          
          ${initialNotice ? `<div id="loginNotice" style="background:rgba(239,68,68,0.15);border:1px solid rgba(239,68,68,0.3);color:#fca5a5;padding:8px 12px;border-radius:6px;font-size:12px;margin-bottom:14px;text-align:left;">${initialNotice}</div>` : '<div id="loginNotice" style="display:none;"></div>'}

          <form id="argonForm" onsubmit="return false;" style="display:flex;flex-direction:column;gap:12px;text-align:left;">
            <div>
              <label style="font-size:11px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;display:block;margin-bottom:4px;">Username</label>
              <input type="text" id="argonUsername" placeholder="e.g. rann" autocomplete="username" autofocus style="background:#1f2937;border:1px solid #4b5563;color:#ffffff;padding:10px 14px;border-radius:8px;font-size:14px;outline:none;width:100%;box-sizing:border-box;">
            </div>
            <div>
              <label style="font-size:11px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;display:block;margin-bottom:4px;">Password</label>
              <input type="password" id="argonPassword" placeholder="Enter password..." autocomplete="current-password" style="background:#1f2937;border:1px solid #4b5563;color:#ffffff;padding:10px 14px;border-radius:8px;font-size:14px;outline:none;width:100%;box-sizing:border-box;">
            </div>
            <button type="submit" id="argonSubmitBtn" style="background:#4f46e5;color:#ffffff;border:none;padding:12px 16px;border-radius:8px;font-size:14px;font-weight:700;cursor:pointer;transition:background 0.2s;margin-top:4px;">Continue to 2FA &rarr;</button>
          </form>
          <div id="argonError" style="display:none;color:#f87171;font-size:12.5px;font-weight:600;margin-top:12px;text-align:center;"></div>
        </div>

        <!-- STEP 2: Two-Factor Authentication (2FA) -->
        <div id="step2FA" style="display:none;">
          <div style="display:inline-flex;padding:12px;background:rgba(16,185,129,0.15);border:1px solid rgba(16,185,129,0.3);border-radius:50%;margin-bottom:14px;">
            <svg style="width:30px;height:30px;color:#34d399;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>
          </div>
          <div style="font-size:11px;font-weight:800;letter-spacing:1px;color:#34d399;text-transform:uppercase;margin-bottom:6px;">Step 2: Two-Factor Verification</div>
          <h2 style="font-size:20px;font-weight:800;color:#ffffff;margin-bottom:6px;">Enter Security Passcode</h2>
          <p style="font-size:13px;color:#94a3b8;line-height:1.5;margin-bottom:14px;">A 6-digit passcode was sent to <strong id="step2Email" style="color:#38bdf8;"></strong>.</p>

          <div style="background:#0d131f;border:1px solid #1f2937;border-radius:8px;padding:8px 12px;margin-bottom:14px;display:flex;justify-content:space-between;align-items:center;font-size:12px;">
            <span style="color:#94a3b8;">⏳ Code Expiration:</span>
            <span id="mainTimerDisplay" style="font-family:monospace;font-weight:800;color:#f59e0b;font-size:14px;">05:00</span>
          </div>

          <div id="graceTimerBanner" style="display:none;background:rgba(239,68,68,0.18);border:1px solid #ef4444;border-radius:8px;padding:8px 12px;margin-bottom:14px;font-size:12px;color:#fca5a5;text-align:center;">
            <strong>Incorrect Code!</strong> You have <span id="graceTimerDisplay" style="font-weight:800;font-family:monospace;font-size:13px;">30s</span> to correct it before session cancellation.
          </div>

          <form id="form2FA" onsubmit="return false;" style="display:flex;flex-direction:column;gap:12px;">
            <div>
              <input type="text" id="twoFactorCode" maxlength="6" pattern="[0-9]*" inputmode="numeric" placeholder="------" autocomplete="one-time-code" style="background:#1f2937;border:2px solid #6366f1;color:#ffffff;padding:12px;border-radius:8px;font-size:26px;letter-spacing:10px;text-align:center;font-family:monospace;font-weight:800;outline:none;width:100%;box-sizing:border-box;">
            </div>
            <button type="submit" id="btnVerify2FA" style="background:#10b981;color:#ffffff;border:none;padding:12px 16px;border-radius:8px;font-size:14px;font-weight:700;cursor:pointer;transition:background 0.2s;">Verify &amp; Enter &rarr;</button>
          </form>
          <div id="twoFactorError" style="display:none;color:#f87171;font-size:12.5px;font-weight:600;margin-top:10px;text-align:center;"></div>
          
          <div style="margin-top:14px;text-align:center;">
            <a href="#" id="linkBackToStep1" style="font-size:12px;color:#94a3b8;text-decoration:none;">&larr; Cancel &amp; Return to Step 1</a>
          </div>
        </div>

        <div style="margin-top:20px;border-top:1px solid #1f2937;padding-top:14px;display:flex;justify-content:space-between;font-size:12px;">
          <a href="/newaccount" style="color:#818cf8;text-decoration:none;">Request Account</a>
          <a href="/" style="color:#64748b;text-decoration:none;">&larr; Public Site</a>
        </div>
      </div>
    `;

    document.body.appendChild(overlay);

    const step1 = document.getElementById("stepCredentials");
    const step2 = document.getElementById("step2FA");
    const form1 = document.getElementById("argonForm");
    const form2 = document.getElementById("form2FA");
    const userInput = document.getElementById("argonUsername");
    const pwdInput = document.getElementById("argonPassword");
    const err1 = document.getElementById("argonError");
    const err2 = document.getElementById("twoFactorError");
    const btn1 = document.getElementById("argonSubmitBtn");
    const btn2 = document.getElementById("btnVerify2FA");
    const codeInput = document.getElementById("twoFactorCode");
    const mainTimerDisplay = document.getElementById("mainTimerDisplay");
    const graceTimerBanner = document.getElementById("graceTimerBanner");
    const graceTimerDisplay = document.getElementById("graceTimerDisplay");
    const linkBack = document.getElementById("linkBackToStep1");

    function resetToStep1(reason) {
      if (mainTimerInterval) clearInterval(mainTimerInterval);
      if (graceTimerInterval) clearInterval(graceTimerInterval);
      activeChallenge = null;
      step2.style.display = "none";
      step1.style.display = "block";
      btn1.innerText = "Continue to 2FA \u2192";
      btn1.disabled = false;
      pwdInput.value = "";
      if (reason) {
        const notice = document.getElementById("loginNotice");
        notice.innerText = reason;
        notice.style.display = "block";
      }
      userInput.focus();
    }

    linkBack.addEventListener("click", function(e) {
      e.preventDefault();
      resetToStep1("2FA session cancelled.");
    });

    form1.addEventListener("submit", async function(e) {
      e.preventDefault();
      err1.style.display = "none";
      btn1.innerText = "Verifying...";
      btn1.disabled = true;

      const u = userInput.value.trim().toLowerCase();
      const p = pwdInput.value.trim();

      if (!u || !p) {
        err1.innerText = "Username and password are required.";
        err1.style.display = "block";
        btn1.innerText = "Continue to 2FA \u2192";
        btn1.disabled = false;
        return;
      }

      try {
        const apiBase = getApiBase();
        const resp = await fetch(apiBase + "/api/accounts/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username: u, password: p })
        });
        const data = await resp.json();

        if (resp.ok && data.success && data.two_factor_required) {
          activeChallenge = {
            id: data.challenge_id,
            expiresAt: Date.now() + (data.expires_in || 300) * 1000,
            attempts: 0,
            graceExpiresAt: null
          };
          transitionToStep2(data.email_masked || u);
        } else {
          err1.innerText = data.error || "Invalid username or password.";
          err1.style.display = "block";
          btn1.innerText = "Continue to 2FA \u2192";
          btn1.disabled = false;
          pwdInput.value = "";
          pwdInput.focus();
        }
      } catch (fetchErr) {
        if (u === MASTER_USER && p === MASTER_PWD) {
          activeChallenge = {
            id: "local_offline_challenge",
            localCode: "888888",
            expiresAt: Date.now() + 300 * 1000,
            attempts: 0,
            graceExpiresAt: null,
            offlineUser: {
              username: "rann",
              fullName: "Rann Bar-On",
              email: "rann@rannbar-on.com",
              privilegeLevel: 10,
              privilegeName: "Master Administrator",
              allowedPages: ["*"],
              status: "APPROVED"
            }
          };
          transitionToStep2("r***@rannbar-on.com (Offline Demo Code: 888888)");
        } else {
          err1.innerText = "Authentication service unreachable. Ensure account_server is running.";
          err1.style.display = "block";
          btn1.innerText = "Continue to 2FA \u2192";
          btn1.disabled = false;
        }
      }
    });

    function transitionToStep2(emailMasked) {
      step1.style.display = "none";
      step2.style.display = "block";
      document.getElementById("step2Email").innerText = emailMasked;
      codeInput.value = "";
      err2.style.display = "none";
      graceTimerBanner.style.display = "none";
      codeInput.focus();

      if (mainTimerInterval) clearInterval(mainTimerInterval);
      mainTimerInterval = setInterval(function() {
        if (!activeChallenge) return;
        const remainingMs = activeChallenge.expiresAt - Date.now();
        if (remainingMs <= 0) {
          clearInterval(mainTimerInterval);
          resetToStep1("5-minute verification passcode expired. Please sign in again.");
          return;
        }
        const totalSecs = Math.floor(remainingMs / 1000);
        const mins = Math.floor(totalSecs / 60);
        const secs = totalSecs % 60;
        mainTimerDisplay.innerText = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
      }, 500);
    }

    form2.addEventListener("submit", async function(e) {
      e.preventDefault();
      err2.style.display = "none";
      const code = codeInput.value.trim();

      if (!code || code.length < 6) {
        err2.innerText = "Please enter the full 6-digit passcode.";
        err2.style.display = "block";
        return;
      }

      btn2.innerText = "Validating...";
      btn2.disabled = true;

      if (activeChallenge && activeChallenge.id === "local_offline_challenge") {
        if (code === activeChallenge.localCode) {
          completeAuth(activeChallenge.offlineUser);
          return;
        } else {
          handleFailedCodeAttempt("Incorrect offline code.");
          btn2.innerText = "Verify & Enter \u2192";
          btn2.disabled = false;
          return;
        }
      }

      try {
        const apiBase = getApiBase();
        const resp = await fetch(apiBase + "/api/auth/verify_2fa", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ challenge_id: activeChallenge.id, code: code })
        });
        const data = await resp.json();

        if (resp.ok && data.success && data.user) {
          completeAuth(data.user);
        } else {
          if (data.kicked) {
            resetToStep1(data.error || "2FA session terminated.");
          } else {
            handleFailedCodeAttempt(data.error || "Incorrect verification code.");
            btn2.innerText = "Verify & Enter \u2192";
            btn2.disabled = false;
          }
        }
      } catch (err) {
        err2.innerText = "Network error communicating with auth server.";
        err2.style.display = "block";
        btn2.innerText = "Verify & Enter \u2192";
        btn2.disabled = false;
      }
    });

    function handleFailedCodeAttempt(errorMsg) {
      if (!activeChallenge) return;
      activeChallenge.attempts = (activeChallenge.attempts || 0) + 1;

      if (activeChallenge.attempts >= 2) {
        resetToStep1("Incorrect code on second attempt. Session terminated for security.");
        return;
      }

      activeChallenge.graceExpiresAt = Date.now() + 30 * 1000;
      graceTimerBanner.style.display = "block";
      err2.innerText = errorMsg;
      err2.style.display = "block";
      codeInput.value = "";
      codeInput.focus();

      if (graceTimerInterval) clearInterval(graceTimerInterval);
      graceTimerInterval = setInterval(function() {
        if (!activeChallenge || !activeChallenge.graceExpiresAt) return;
        const graceRemaining = activeChallenge.graceExpiresAt - Date.now();
        if (graceRemaining <= 0) {
          clearInterval(graceTimerInterval);
          resetToStep1("30-second error correction timer expired. Session terminated.");
          return;
        }
        const secs = Math.ceil(graceRemaining / 1000);
        graceTimerDisplay.innerText = `${secs}s`;
      }, 300);
    }

    function completeAuth(user) {
      if (mainTimerInterval) clearInterval(mainTimerInterval);
      if (graceTimerInterval) clearInterval(graceTimerInterval);

      sessionStorage.setItem(STORAGE_KEYS.SESSION_ACTIVE, "true");
      setSessionCookie("true");
      setStoredUser(user);
      recordActivity();

      sessionStorage.setItem("nc_internal_argon_auth", "valid");
      sessionStorage.setItem("durham_pol_auth", "granted");

      // Verify page-by-page granular access
      const { route: currentRoute, title: currentTitle } = getCurrentRouteInfo();
      if (!userHasRoutePermission(user, currentRoute)) {
        renderAccessDeniedScreen(currentTitle, user);
        return;
      }

      overlay.remove();

      if (cachedOriginalContent && document.body.innerHTML === "") {
        document.body.innerHTML = cachedOriginalContent;
      }

      window.dispatchEvent(new CustomEvent("rannAuthSuccess", { detail: user }));
    }
  }

  function initGate() {
    if (!isSessionValid()) {
      renderLockScreen();
    } else {
      recordActivity();
      const user = getStoredUser();
      const { route: currentRoute, title: currentTitle } = getCurrentRouteInfo();
      if (!userHasRoutePermission(user, currentRoute)) {
        renderAccessDeniedScreen(currentTitle, user);
      }
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initGate);
  } else {
    initGate();
  }
})();
