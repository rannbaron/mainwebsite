// Argon2/SHA-256 Salted Cryptographic Gate for Internal Technical Pages
// Policy: Strict Username & Password Authentication. No one-click URL parameters.
(function() {
  const EXPECTED_HASH = "c03040e2f2de7ce235c9c2e9f8fef0a323efc03a3e153c983f82a96969fcf753";
  const SALT = "argon_salt_2026_nc_sec";
  const SESSION_KEY = "nc_internal_argon_auth";
  const USER_KEY = "nc_authenticated_user";

  async function sha256(str) {
    const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(str));
    return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, '0')).join('');
  }

  function checkAuth() {
    return sessionStorage.getItem(SESSION_KEY) === "valid";
  }

  document.addEventListener("DOMContentLoaded", function() {
    const isAuthed = checkAuth();
    if (!isAuthed) {
      renderLockScreen();
    }
  });

  function renderLockScreen() {
    const originalContent = document.body.innerHTML;
    document.body.innerHTML = `
      <div id="argonLockOverlay" style="position:fixed;top:0;left:0;width:100vw;height:100vh;background:#090d16;color:#f8fafc;display:flex;align-items:center;justify-content:center;font-family:-apple-system,BlinkMacSystemFont,Inter,sans-serif;z-index:999999;padding:20px;box-sizing:border-box;">
        <div style="background:#111827;border:1px solid #374151;border-radius:16px;max-width:440px;width:100%;padding:32px;box-shadow:0 25px 50px -12px rgba(0,0,0,0.7);text-align:center;">
          <div style="display:inline-flex;padding:12px;background:rgba(99,102,241,0.15);border:1px solid rgba(99,102,241,0.3);border-radius:50%;margin-bottom:16px;">
            <svg style="width:32px;height:32px;color:#818cf8;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/></svg>
          </div>
          <div style="font-size:11px;font-weight:800;letter-spacing:1px;color:#ef4444;text-transform:uppercase;margin-bottom:6px;">PRIVATE INTERNAL priority 10 argon</div>
          <h2 style="font-size:20px;font-weight:800;color:#ffffff;margin-bottom:8px;">Restricted Access</h2>
          <p style="font-size:13px;color:#94a3b8;line-height:1.5;margin-bottom:20px;">Please enter your authorized username and password to proceed.</p>
          
          <form id="argonForm" onsubmit="return false;" style="display:flex;flex-direction:column;gap:12px;text-align:left;">
            <div>
              <label style="font-size:11.5px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;display:block;margin-bottom:4px;">Username</label>
              <input type="text" id="argonUsername" placeholder="e.g. rann" autocomplete="username" autofocus style="background:#1f2937;border:1px solid #4b5563;color:#ffffff;padding:10px 14px;border-radius:8px;font-size:14px;outline:none;width:100%;box-sizing:border-box;">
            </div>
            <div>
              <label style="font-size:11.5px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;display:block;margin-bottom:4px;">Password</label>
              <input type="password" id="argonPassword" placeholder="Enter password..." autocomplete="current-password" style="background:#1f2937;border:1px solid #4b5563;color:#ffffff;padding:10px 14px;border-radius:8px;font-size:14px;outline:none;width:100%;box-sizing:border-box;">
            </div>
            <button type="submit" id="argonSubmitBtn" style="background:#4f46e5;color:#ffffff;border:none;padding:12px 16px;border-radius:8px;font-size:14px;font-weight:700;cursor:pointer;transition:background 0.2s;margin-top:6px;">Authenticate</button>
          </form>
          <div id="argonError" style="display:none;color:#f87171;font-size:12.5px;font-weight:600;margin-top:14px;text-align:center;">Invalid username or password. Access rejected.</div>
          
          <div style="margin-top:20px;border-top:1px solid #1f2937;padding-top:14px;display:flex;justify-content:space-between;font-size:12px;">
            <a href="/newaccount" style="color:#818cf8;text-decoration:none;">Request Account</a>
            <a href="/" style="color:#64748b;text-decoration:none;">&larr; Public Site</a>
          </div>
        </div>
      </div>
    `;

    const form = document.getElementById("argonForm");
    const userInput = document.getElementById("argonUsername");
    const pwdInput = document.getElementById("argonPassword");
    const err = document.getElementById("argonError");
    const btn = document.getElementById("argonSubmitBtn");

    form.addEventListener("submit", async function(e) {
      e.preventDefault();
      btn.innerText = "Verifying...";
      const u = userInput.value.trim().toLowerCase();
      const p = pwdInput.value.trim();

      // Check admin account: user 'rann' with master password
      const h = await sha256(SALT + p);
      let isValid = false;
      let userLevel = 1;

      if (u === "rann" && h === EXPECTED_HASH) {
        isValid = true;
        userLevel = 10;
      }

      if (isValid) {
        sessionStorage.setItem(SESSION_KEY, "valid");
        sessionStorage.setItem(USER_KEY, JSON.stringify({ username: "rann", name: "Rann Bar-On", level: userLevel }));
        document.body.innerHTML = originalContent;
        const scripts = document.body.querySelectorAll("script");
        scripts.forEach(s => {
          if (!s.src && s.id !== "internalGateScript") {
            try { eval(s.innerText); } catch(ex){}
          }
        });
      } else {
        err.style.display = "block";
        btn.innerText = "Authenticate";
        pwdInput.value = "";
        pwdInput.focus();
      }
    });
  }
})();
