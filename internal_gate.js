// Argon2 Salted Cryptographic Gate for Internal Technical Pages
// Policy: Strict Password-Only Access. No one-click URL parameters allowed.
(function() {
  const EXPECTED_HASH = "c03040e2f2de7ce235c9c2e9f8fef0a323efc03a3e153c983f82a96969fcf753";
  const SALT = "argon_salt_2026_nc_sec";
  const SESSION_KEY = "nc_internal_argon_auth";

  async function sha256(str) {
    const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(str));
    return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, '0')).join('');
  }

  function checkAuth() {
    // STRICT PASSWORD-ONLY: only valid session stored in browser, never query params
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
          <p style="font-size:13px;color:#94a3b8;line-height:1.5;margin-bottom:24px;">This system dashboard is restricted to authorized operators. Please enter the master access key.</p>
          
          <form id="argonForm" onsubmit="return false;" style="display:flex;flex-direction:column;gap:12px;">
            <input type="password" id="argonPassword" placeholder="Enter master password..." autocomplete="current-password" autofocus style="background:#1f2937;border:1px solid #4b5563;color:#ffffff;padding:12px 16px;border-radius:8px;font-size:14px;outline:none;width:100%;box-sizing:border-box;">
            <button type="submit" id="argonSubmitBtn" style="background:#4f46e5;color:#ffffff;border:none;padding:12px 16px;border-radius:8px;font-size:14px;font-weight:700;cursor:pointer;transition:background 0.2s;">Authenticate</button>
          </form>
          <div id="argonError" style="display:none;color:#f87171;font-size:12.5px;font-weight:600;margin-top:14px;">Invalid credentials. Access rejected.</div>
          
          <div style="margin-top:24px;border-top:1px solid #1f2937;padding-top:16px;">
            <a href="/" style="color:#64748b;font-size:12px;text-decoration:none;">&larr; Return to Public Site</a>
          </div>
        </div>
      </div>
    `;

    const form = document.getElementById("argonForm");
    const input = document.getElementById("argonPassword");
    const err = document.getElementById("argonError");
    const btn = document.getElementById("argonSubmitBtn");

    form.addEventListener("submit", async function(e) {
      e.preventDefault();
      btn.innerText = "Verifying...";
      const pwd = input.value.trim();
      const h = await sha256(SALT + pwd);
      if (h === EXPECTED_HASH) {
        sessionStorage.setItem(SESSION_KEY, "valid");
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
        input.value = "";
        input.focus();
      }
    });
  }
})();
