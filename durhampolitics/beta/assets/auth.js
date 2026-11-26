/* Strictly Rann-only authentication gate for /durhampolitics/beta/ */
(function () {
  const SALT = "durham_beta_rann_v1";
  const EXPECTED_HASH = "0ca8144b84e3fb9c1091c871b3f403e71945d9607e78d251984f8cf2865e6e6a";
  const SESSION_KEY = "rann_session_active";
  const LAST_ACTIVE_KEY = "rann_auth_last_active";
  const IDLE_LIMIT_MS = 60 * 60 * 1000;

  let memLastActive = Date.now();

  function touch() {
    memLastActive = Date.now();
    try {
      localStorage.setItem(LAST_ACTIVE_KEY, String(memLastActive));
    } catch (e) {}
  }

  function getLastActive() {
    let v = memLastActive;
    try {
      const s = parseInt(localStorage.getItem(LAST_ACTIVE_KEY) || "0", 10);
      if (s > v) v = s;
    } catch (e) {}
    return v;
  }

  async function sha256Hex(str) {
    const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(str));
    return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, "0")).join("");
  }

  function unlock() {
    const ov = document.getElementById("betaAuthOverlay");
    const app = document.getElementById("betaApp");
    if (ov) ov.style.display = "none";
    if (app) app.style.display = "block";
    if (typeof window.__onBetaAuthUnlocked === "function" && !window.__betaInited) {
      window.__betaInited = true;
      window.__onBetaAuthUnlocked();
    }
  }

  function lock(msg) {
    sessionStorage.removeItem(SESSION_KEY);
    const ov = document.getElementById("betaAuthOverlay");
    const app = document.getElementById("betaApp");
    if (app) app.style.display = "none";
    if (ov) ov.style.display = "flex";
    const err = document.getElementById("betaAuthError");
    if (err && msg) {
      err.textContent = msg;
      err.style.display = "block";
    }
  }

  window.betaSignOut = function () {
    lock("Signed out.");
  };

  window.handleBetaAuth = async function (e) {
    e.preventDefault();
    const uEl = document.getElementById("betaUserInput");
    const pEl = document.getElementById("betaPassInput");
    const err = document.getElementById("betaAuthError");
    const user = (uEl ? uEl.value.trim().toLowerCase() : "");
    const pwd = (pEl ? pEl.value.trim() : "");

    if (user !== "rann") {
      if (err) {
        err.textContent = "Beta preview access is restricted to administrator (rann) only.";
        err.style.display = "block";
      }
      return;
    }

    const digest = await sha256Hex(SALT + ":" + pwd);
    if (digest === EXPECTED_HASH) {
      sessionStorage.setItem(SESSION_KEY, "valid");
      touch();
      if (err) err.style.display = "none";
      unlock();
    } else {
      if (err) {
        err.textContent = "Invalid administrator password.";
        err.style.display = "block";
      }
      if (pEl) pEl.focus();
    }
  };

  ["mousemove", "mousedown", "keydown", "scroll", "touchstart"].forEach(ev => {
    window.addEventListener(ev, () => {
      if (Date.now() - memLastActive > 5000) touch();
    }, { passive: true });
  });

  setInterval(() => {
    if (sessionStorage.getItem(SESSION_KEY) === "valid" && (Date.now() - getLastActive() > IDLE_LIMIT_MS)) {
      lock("Session timed out after 1 hour of inactivity.");
    }
  }, 10000);

  document.addEventListener("DOMContentLoaded", () => {
    const active = sessionStorage.getItem(SESSION_KEY) === "valid";
    if (active && (Date.now() - getLastActive() <= IDLE_LIMIT_MS)) {
      touch();
      unlock();
    } else {
      lock("");
    }
  });
})();
