/**
 * AppUtils: Shared UI & Persistence Library
 */
const AppUtils = {
    isDarkMode: false,

    loadState: function(storageKey) {
        let stateToLoad = null;
        let loadedFromUrl = false;

        const hash = window.location.hash;
        if (hash && hash.includes('state=')) {
            try {
                stateToLoad = JSON.parse(decodeURIComponent(atob(decodeURIComponent(hash.split('state=')[1]))));
                loadedFromUrl = true;
            } catch (e) { console.warn("Failed to parse URL state."); }
        } 

        if (!stateToLoad) {
            try {
                const savedStr = localStorage.getItem(storageKey);
                if (savedStr) stateToLoad = JSON.parse(savedStr);
            } catch (e) { console.warn("Failed to load local state."); }
        }

        return { data: stateToLoad, fromUrl: loadedFromUrl };
    },

    saveState: function(storageKey, stateObj) {
        try { localStorage.setItem(storageKey, JSON.stringify(stateObj)); } 
        catch(e) { console.warn("Failed to save state."); }
    },

    cleanUrlOnLoad: function() {
        const cleanUrl = window.location.protocol + "//" + window.location.host + window.location.pathname + window.location.search;
        window.history.replaceState(null, "", cleanUrl);
    },

    setupSharing: function(btnId, getStateCallback) {
        const shareBtn = document.getElementById(btnId);
        if (!shareBtn) return;

        shareBtn.addEventListener('click', () => {
            const state = getStateCallback();
            const shareUrl = window.location.protocol + "//" + window.location.host + window.location.pathname + '#state=' + btoa(encodeURIComponent(JSON.stringify(state)));
            window.history.replaceState(null, "", shareUrl);
            
            const originalText = shareBtn.innerText;
            shareBtn.innerText = '⬆️ Link in Address Bar! ⬆️';
            
            if (navigator.clipboard && window.isSecureContext) {
                navigator.clipboard.writeText(shareUrl).then(showCopied).catch(() => legacyCopy(shareUrl));
            } else { legacyCopy(shareUrl); }

            function showCopied() {
                shareBtn.innerText = '✅ Copied to Clipboard!';
                setTimeout(() => { shareBtn.innerText = originalText; window.history.replaceState(null, "", window.location.pathname); }, 2500);
            }
            function legacyCopy(url) {
                try {
                    const textArea = document.createElement("textarea");
                    textArea.value = url; textArea.style.position = "fixed"; textArea.style.opacity = "0";
                    document.body.appendChild(textArea); textArea.focus(); textArea.select();
                    if (document.execCommand('copy')) showCopied(); else setTimeout(() => shareBtn.innerText = originalText, 4000);
                    document.body.removeChild(textArea);
                } catch (err) { setTimeout(() => shareBtn.innerText = originalText, 4000); }
            }
        });
    },

    setupThemeToggle: function(btnId, initialState, onChangeCallback) {
        this.isDarkMode = initialState || false;
        const btn = document.getElementById(btnId);
        const applyTheme = () => {
            document.body.classList.toggle('dark-mode', this.isDarkMode);
            if (btn) btn.innerText = this.isDarkMode ? '☀️ Light Mode' : '🌙 Dark Mode';
        };
        applyTheme();
        if (btn) {
            btn.addEventListener('click', () => {
                this.isDarkMode = !this.isDarkMode;
                applyTheme();
                if (onChangeCallback) onChangeCallback(this.isDarkMode);
            });
        }
    },

    setupHelpModal: function(openBtnId, modalId, closeBtnId) {
        const helpModal = document.getElementById(modalId);
        const openBtn = document.getElementById(openBtnId);
        const closeBtn = document.getElementById(closeBtnId);
        if (!helpModal || !openBtn || !closeBtn) return;

        openBtn.addEventListener('click', () => helpModal.style.display = 'flex');
        closeBtn.addEventListener('click', () => helpModal.style.display = 'none');
        window.addEventListener('click', (e) => { if (e.target === helpModal) helpModal.style.display = 'none'; });
    }
};
