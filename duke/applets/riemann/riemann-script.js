math.config({ predictable: true });

// --- DOM Elements & State Variables ---
let isDarkMode = false;
const eqInput = document.getElementById('eqInput');
const boundAInput = document.getElementById('boundA');
const boundBInput = document.getElementById('boundB');
const nInput = document.getElementById('nInput');
const sigFigInput = document.getElementById('sigFigInput');
const hudPosSelect = document.getElementById('hudPos');
const improperWarning = document.getElementById('improperWarning');

const chkLHS = document.getElementById('chkLHS');
const chkRHS = document.getElementById('chkRHS');
const chkMPS = document.getElementById('chkMPS');
const chkError = document.getElementById('chkError');

let compiledEq = null;
let isEqValid = false;
let isTrigMode = false;
let globalFinalTex = ""; // Global reference for the consolidated formula

let globalBounds = { xMin: -1, xMax: 1, yMin: -1, yMax: 1 };
let trueArea = 0;

// --- Extension-Proof URL Sharing Logic ---
const shareBtn = document.getElementById('shareBtn');
shareBtn.addEventListener('click', () => {
    const state = {
        theme: isDarkMode,
        eq: eqInput.value,
        boundA: boundAInput.value,
        boundB: boundBInput.value,
        n: nInput.value,
        sigFigs: sigFigInput.value,
        hudPos: hudPosSelect.value,
        toggles: {
            lhs: chkLHS.checked,
            rhs: chkRHS.checked,
            mps: chkMPS.checked,
            err: chkError.checked
        }
    };
    
    const jsonString = JSON.stringify(state);
    const uriEncoded = encodeURIComponent(jsonString);
    const base64State = btoa(uriEncoded);
    
    const cleanPath = window.location.protocol + "//" + window.location.host + window.location.pathname;
    const shareUrl = cleanPath + '#state=' + base64State;
    
    window.history.replaceState(null, "", shareUrl);
    
    const originalText = shareBtn.innerText;
    shareBtn.innerText = '⬆️ Link in Address Bar! ⬆️';
    
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(shareUrl)
            .then(() => showCopiedFeedback())
            .catch(() => legacyCopy(shareUrl));
    } else {
        legacyCopy(shareUrl);
    }

    function showCopiedFeedback() {
        shareBtn.innerText = '✅ Copied to Clipboard!';
        setTimeout(() => {
            shareBtn.innerText = originalText;
            window.history.replaceState(null, "", cleanPath); 
        }, 2500);
    }

    function legacyCopy(url) {
        try {
            const textArea = document.createElement("textarea");
            textArea.value = url;
            textArea.style.position = "fixed";
            textArea.style.top = "0";
            textArea.style.left = "0";
            textArea.style.width = "1px";
            textArea.style.height = "1px";
            textArea.style.background = "transparent";
            
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            
            const successful = document.execCommand('copy');
            document.body.removeChild(textArea);
            
            if (successful) showCopiedFeedback();
            else setTimeout(() => shareBtn.innerText = originalText, 4000);
        } catch (err) {
            setTimeout(() => shareBtn.innerText = originalText, 4000);
        }
    }
});

// --- Persistence Logic ---
function loadSavedState() {
    let stateToLoad = null;
    let loadedFromUrl = false;

    const hash = window.location.hash;
    if (hash && hash.includes('state=')) {
        try {
            let rawB64 = hash.split('state=')[1];
            let safeB64 = decodeURIComponent(rawB64); 
            let decodedUri = atob(safeB64);
            let finalJson = decodeURIComponent(decodedUri);
            
            stateToLoad = JSON.parse(finalJson);
            loadedFromUrl = true;
        } catch (e) {}
    } 

    if (!stateToLoad) {
        try {
            const savedStr = localStorage.getItem('riemannAppStateV16'); 
            if (savedStr) stateToLoad = JSON.parse(savedStr);
        } catch (e) {}
    }

    if (stateToLoad) {
        if (stateToLoad.theme !== undefined) {
            isDarkMode = stateToLoad.theme;
            document.body.classList.toggle('dark-mode', isDarkMode);
            document.getElementById('themeToggle').innerText = isDarkMode ? '☀️ Light Mode' : '🌙 Dark Mode';
        }
        
        if (stateToLoad.eq !== undefined) eqInput.value = stateToLoad.eq;
        if (stateToLoad.boundA !== undefined) boundAInput.value = stateToLoad.boundA;
        if (stateToLoad.boundB !== undefined) boundBInput.value = stateToLoad.boundB;
        if (stateToLoad.sigFigs !== undefined) sigFigInput.value = stateToLoad.sigFigs;
        if (stateToLoad.hudPos !== undefined) hudPosSelect.value = stateToLoad.hudPos;
        if (stateToLoad.n !== undefined) nInput.value = stateToLoad.n;
        
        if (stateToLoad.toggles) {
            chkLHS.checked = stateToLoad.toggles.lhs;
            chkRHS.checked = stateToLoad.toggles.rhs;
            chkMPS.checked = stateToLoad.toggles.mps;
            chkError.checked = stateToLoad.toggles.err;
        }

        if (loadedFromUrl) {
            const cleanUrl = window.location.protocol + "//" + window.location.host + window.location.pathname + window.location.search;
            window.history.replaceState(null, "", cleanUrl);
            setTimeout(() => { saveState(); }, 500);
        }
    }
}

function saveState() {
    try {
        const state = {
            theme: isDarkMode,
            eq: eqInput.value,
            boundA: boundAInput.value,
            boundB: boundBInput.value,
            n: nInput.value,
            sigFigs: sigFigInput.value,
            hudPos: hudPosSelect.value,
            toggles: {
                lhs: chkLHS.checked,
                rhs: chkRHS.checked,
                mps: chkMPS.checked,
                err: chkError.checked
            }
        };
        localStorage.setItem('riemannAppStateV16', JSON.stringify(state));
    } catch(e) {}
}

loadSavedState();

// --- Theme & Modal ---
const themeToggle = document.getElementById('themeToggle');
themeToggle.addEventListener('click', () => {
    isDarkMode = !isDarkMode;
    document.body.classList.toggle('dark-mode', isDarkMode);
    themeToggle.innerText = isDarkMode ? '☀️ Light Mode' : '🌙 Dark Mode';
    saveState();
    triggerFullUpdate(); 
});

const helpModal = document.getElementById('helpModal');
document.getElementById('helpBtn').addEventListener('click', () => helpModal.style.display = 'flex');
document.getElementById('closeHelpBtn').addEventListener('click', () => helpModal.style.display = 'none');
window.addEventListener('click', (e) => { if (e.target === helpModal) helpModal.style.display = 'none'; });

// --- Math Parsing & KaTeX Typesetting ---
function formatImplicitMath(str) {
    let s = str.replace(/\s+/g, '');
    s = s.replace(/arcsin/gi, 'asin').replace(/arccos/gi, 'acos').replace(/arctan/gi, 'atan');
    s = s.replace(/\|([^|]+)\|/g, 'abs($1)');
    s = s.replace(/log(?!10)/gi, 'log10').replace(/ln/gi, 'log');
    s = s.replace(/\/([0-9]*(?:x(?:\^[0-9.]+)?)+)/gi, '/($1)');
    s = s.replace(/([0-9])([x\(])/gi, '$1*$2');
    s = s.replace(/(x)([0-9])/gi, '$1*$2');
    s = s.replace(/(x)(\()/gi, '$1*$2');
    s = s.replace(/(\))([x0-9\(])/gi, '$1*$2');
    s = s.replace(/([0-9x])(sin|cos|tan|asin|acos|atan|exp|log10|log|sqrt|abs|pi|e)/gi, '$1*$2');
    return s;
}

function parseEquation() {
    try {
        let processed = formatImplicitMath(eqInput.value);
        let parsed = math.parse(processed);
        
        isTrigMode = false;
        const allowedVars = ['x', 'e', 'pi'];
        parsed.traverse(function(node, path, parent) {
            if (node.type === 'SymbolNode') {
                if (parent && parent.type === 'FunctionNode' && path === 'fn') return;
                if (!allowedVars.includes(node.name)) throw new Error(`Illegal variable: ${node.name}`);
            }
            if (node.type === 'FunctionNode' && ['sin', 'cos', 'tan', 'sec', 'csc', 'cot'].includes(node.fn.name)) {
                isTrigMode = true;
            }
        });

        compiledEq = parsed.compile();
        compiledEq.evaluate({x: 1}); 
        eqInput.classList.remove('error');
        isEqValid = true;

        let equationTex = parsed.toTex({ parenthesis: 'auto', implicit: 'hide' });
        equationTex = equationTex.replace(/\\log\left/g, '\\ln\\left');
        equationTex = equationTex.replace(/\\cdot\s*/g, '');
        
        globalFinalTex = `f(x) = \\displaystyle ${equationTex}`;
        
        // Render inline for individual graphs
        ['LHS', 'RHS', 'MPS'].forEach(type => {
            let overlay = document.getElementById(`mathOverlay${type}`);
            if (overlay) katex.render(globalFinalTex, overlay, { throwOnError: false, displayMode: false });
        });

        // Render Centered Display Mode for the Master Consolidated HUD
        let masterOverlay = document.getElementById('mathOverlayConsolidated');
        if (masterOverlay) {
            katex.render(globalFinalTex, masterOverlay, { throwOnError: false, displayMode: true });
        }

    } catch (e) {
        eqInput.classList.add('error');
        isEqValid = false;
        ['mathOverlayLHS', 'mathOverlayRHS', 'mathOverlayMPS', 'mathOverlayConsolidated'].forEach(id => {
            let overlay = document.getElementById(id);
            if (overlay) overlay.innerHTML = '';
        });
    }
}

function getBound(inputElement, fallbackValue) {
    try {
        let processed = formatImplicitMath(inputElement.value);
        let val = math.evaluate(processed);
        if (typeof val === 'number' && !isNaN(val)) {
            inputElement.classList.remove('error');
            return val;
        }
    } catch (e) {}
    inputElement.classList.add('error');
    return fallbackValue;
}

function f(x) {
    if(!isEqValid || !compiledEq) return NaN;
    try { 
        let res = compiledEq.evaluate({x});
        if (typeof res === 'object') return NaN; 
        if (isNaN(res)) return NaN;
        return res; 
    } catch { return NaN; }
}

function computeGlobalBounds() {
    if (!isEqValid) return;

    let a = getBound(boundAInput, 0);
    let b = getBound(boundBInput, 5);
    if (a > b) { let temp = a; a = b; b = temp; }
    if (a === b) b = a + 1;

    let isImproper = false;
    let nChecks = 1000;
    let dxCheck = (b - a) / nChecks;
    
    for (let i = 0; i <= nChecks; i++) {
        let x = a + i * dxCheck;
        let y = f(x);
        if (Number.isNaN(y) || !Number.isFinite(y) || Math.abs(y) > 1e6) {
            isImproper = true;
            break;
        }
    }
    
    improperWarning.style.display = isImproper ? 'block' : 'none';

    let xSpan = b - a;
    globalBounds.xMin = a - (xSpan * 0.15);
    globalBounds.xMax = b + (xSpan * 0.15);

    let yMax = -Infinity;
    let yMin = Infinity;
    
    for (let i = 0; i <= 500; i++) {
        let x = globalBounds.xMin + (globalBounds.xMax - globalBounds.xMin) * (i / 500);
        let y = f(x);
        if (!isNaN(y) && isFinite(y) && Math.abs(y) < 1e6) {
            if (y > yMax) yMax = y;
            if (y < yMin) yMin = y;
        }
    }

    if (yMax === -Infinity) { yMax = 10; yMin = -10; } 
    if (yMax === yMin) { yMax += 5; yMin -= 5; }

    if (yMin > 0) yMin = 0;
    if (yMax < 0) yMax = 0;

    let ySpan = yMax - yMin;
    globalBounds.yMin = yMin - (ySpan * 0.15);
    globalBounds.yMax = yMax + (ySpan * 0.15);

    if (isImproper) {
        trueArea = NaN;
    } else {
        trueArea = 0;
        let simpx = (b - a) / 2000;
        for (let i = 0; i < 2000; i++) {
            let mid = a + i * simpx + simpx / 2;
            let val = f(mid);
            if (!isNaN(val)) trueArea += simpx * val;
        }
    }
}

function formatFractionOfPi(val) {
    const tol = 1e-5;
    if (Math.abs(val) < tol) return "0";
    
    let frac = val / Math.PI;
    for (let d of [1, 2, 4, 8]) {
        let num = Math.round(frac * d);
        if (Math.abs(frac * d - num) < tol) {
            if (num === 0) return "0";
            let sign = num < 0 ? "-" : "";
            let absNum = Math.abs(num);
            let piStr = absNum === 1 ? "π" : absNum + "π";
            if (d === 1) return sign + piStr;
            return sign + piStr + "/" + d;
        }
    }
    return parseFloat(val.toFixed(2));
}

class Plot {
    constructor(type) {
        this.type = type; 
        this.wrapper = document.getElementById(`wrapper${type}`);
        this.canvas = document.getElementById(`canvas${type}`);
        this.ctx = this.canvas.getContext('2d');
        
        this.hud = document.getElementById(`hud${type}`);
        this.statsDiv = document.getElementById(`stats${type}`);
        
        // Save values for the consolidated HUD
        this.currentSum = 0;
        this.currentErr = 0;
    }

    draw() {
        if(this.wrapper.style.display === 'none') return;

        if (!isEqValid) {
            this.hud.style.display = 'none';
            this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
            return;
        }

        const dpr = window.devicePixelRatio || 1;
        const displayWidth = this.canvas.clientWidth;
        const displayHeight = this.canvas.clientHeight;

        if (displayWidth === 0 || displayHeight === 0) return;

        if (this.canvas.width !== displayWidth * dpr || this.canvas.height !== displayHeight * dpr) {
            this.canvas.width = displayWidth * dpr;
            this.canvas.height = displayHeight * dpr;
        }

        this.ctx.save();
        this.ctx.scale(dpr, dpr);
        
        let w = displayWidth;
        let h = displayHeight;

        this.ctx.clearRect(0, 0, w, h);

        const {xMin, xMax, yMin, yMax} = globalBounds;
        let a = getBound(boundAInput, 0);
        let b = getBound(boundBInput, 5);
        if (a > b) { let temp = a; a = b; b = temp; }

        const toScreenX = (x) => ((x - xMin) / (xMax - xMin)) * w;
        const toScreenY = (y) => h - ((y - yMin) / (yMax - yMin)) * h;

        const axisColor = isDarkMode ? '#495057' : '#ced4da';
        const tickColor = isDarkMode ? '#adb5bd' : '#6c757d';
        const curveColor = isDarkMode ? '#f8f9fa' : '#212529';
        
        const styleObj = getComputedStyle(document.body);
        let themeColorHex = '';
        if (this.type === 'LHS') themeColorHex = styleObj.getPropertyValue('--color-lhs').trim();
        if (this.type === 'RHS') themeColorHex = styleObj.getPropertyValue('--color-rhs').trim();
        if (this.type === 'MPS') themeColorHex = styleObj.getPropertyValue('--color-mps').trim();

        const getStandardStep = (span) => {
            if (span > 100) return 20;
            if (span > 50) return 10;
            if (span > 20) return 5;
            if (span > 10) return 2;
            return 1;
        };

        const getTrigStep = (span) => {
            let spanPi = span / Math.PI;
            if (spanPi > 20) return Math.PI * 4;
            if (spanPi > 10) return Math.PI * 2;
            if (spanPi > 4) return Math.PI;
            if (spanPi > 2) return Math.PI / 2;
            if (spanPi > 1) return Math.PI / 4;
            return Math.PI / 8;
        };

        let xStep = isTrigMode ? getTrigStep(xMax - xMin) : getStandardStep(xMax - xMin);
        let yStep = getStandardStep(yMax - yMin);

        let yAxisScreenX = toScreenX(0);
        if (0 < xMin) yAxisScreenX = toScreenX(xMin);
        if (0 > xMax) yAxisScreenX = toScreenX(xMax);

        let xAxisScreenY = toScreenY(0);

        this.ctx.strokeStyle = axisColor;
        this.ctx.lineWidth = 2;
        this.ctx.beginPath();
        this.ctx.moveTo(yAxisScreenX, 0); this.ctx.lineTo(yAxisScreenX, h); 
        this.ctx.moveTo(0, xAxisScreenY); this.ctx.lineTo(w, xAxisScreenY); 
        this.ctx.stroke();

        this.ctx.fillStyle = tickColor;
        this.ctx.font = '13px Arial';
        this.ctx.lineWidth = 1;
        this.ctx.strokeStyle = tickColor;

        this.ctx.textAlign = 'center';
        this.ctx.textBaseline = 'top';
        let startX = Math.ceil(xMin / xStep) * xStep;
        for (let x = startX; x <= xMax; x += xStep) {
            if (Math.abs(x) < 0.0001) continue; 
            let sx = toScreenX(x);
            this.ctx.beginPath();
            this.ctx.moveTo(sx, xAxisScreenY - 5);
            this.ctx.lineTo(sx, xAxisScreenY + 5);
            this.ctx.stroke();
            this.ctx.fillText(isTrigMode ? formatFractionOfPi(x) : x.toString(), sx, xAxisScreenY + 8);
        }

        this.ctx.textAlign = 'right';
        this.ctx.textBaseline = 'middle';
        let startY = Math.ceil(yMin / yStep) * yStep;
        for (let y = startY; y <= yMax; y += yStep) {
            if (Math.abs(y) < 0.0001) continue; 
            let sy = toScreenY(y);
            this.ctx.beginPath();
            this.ctx.moveTo(yAxisScreenX - 5, sy);
            this.ctx.lineTo(yAxisScreenX + 5, sy);
            this.ctx.stroke();
            this.ctx.fillText(y.toString(), yAxisScreenX - 8, sy);
        }

        this.ctx.strokeStyle = curveColor;
        this.ctx.lineWidth = 2.5;
        this.ctx.beginPath();
        let isDrawing = false;
        for (let px = 0; px <= w; px++) {
            let x = xMin + (px / w) * (xMax - xMin);
            let y = f(x);
            if (!isNaN(y) && Math.abs(y) < 1e6) { 
                if (!isDrawing) { this.ctx.moveTo(px, toScreenY(y)); isDrawing = true; } 
                else { this.ctx.lineTo(px, toScreenY(y)); }
            } else { isDrawing = false; }
        }
        this.ctx.stroke();

        let n = parseInt(nInput.value) || 8; 
        let dx = (b - a) / n;
        let mySum = 0;

        const drawErrorArea = (xStart, xEnd, yRect) => {
            this.ctx.beginPath();
            this.ctx.moveTo(toScreenX(xStart), toScreenY(yRect));
            this.ctx.lineTo(toScreenX(xEnd), toScreenY(yRect));
            for (let x = xEnd; x >= xStart; x -= (xEnd - xStart) / 20) {
                let yCurve = f(x);
                if (!isNaN(yCurve) && Math.abs(yCurve) < 1e6) this.ctx.lineTo(toScreenX(x), toScreenY(yCurve));
            }
            this.ctx.closePath();
            
            let r = parseInt(themeColorHex.slice(1, 3), 16);
            let g = parseInt(themeColorHex.slice(3, 5), 16);
            let bl = parseInt(themeColorHex.slice(5, 7), 16);
            this.ctx.fillStyle = `rgba(${r}, ${g}, ${bl}, 0.5)`;
            this.ctx.fill();
        };

        for (let i = 0; i < n; i++) {
            let xi = a + i * dx;
            let xNext = a + (i + 1) * dx;
            let xMid = a + (i + 0.5) * dx;

            let yRect = 0;
            if (this.type === 'LHS') yRect = f(xi);
            if (this.type === 'RHS') yRect = f(xNext);
            if (this.type === 'MPS') yRect = f(xMid);

            if (!isNaN(yRect) && isFinite(yRect)) {
                mySum += yRect * dx;
                let screenX = toScreenX(xi);
                let screenW = toScreenX(xNext) - screenX;
                let screenY = toScreenY(Math.max(0, yRect));
                let screenH = Math.abs(toScreenY(0) - toScreenY(yRect));

                if (chkError.checked) drawErrorArea(xi, xNext, yRect);

                this.ctx.strokeStyle = themeColorHex;
                this.ctx.fillStyle = isDarkMode ? `${themeColorHex}22` : `${themeColorHex}11`;
                this.ctx.lineWidth = 1.5;
                this.ctx.fillRect(screenX, screenY, screenW, screenH);
                this.ctx.strokeRect(screenX, screenY, screenW, screenH);
            } else {
                mySum = NaN; 
            }
        }

        let err = Math.abs(mySum - trueArea);
        let sf = parseInt(sigFigInput.value) || 4;
        const formatVal = (v) => (isNaN(v) || !isFinite(v)) ? "Undefined" : math.format(v, { precision: sf, notation: 'auto' });

        // Save values so the Master HUD can read them later
        this.currentSum = mySum;
        this.currentErr = err;

        // --- HIDE INDIVIDUAL HUD IF CONSOLIDATED VIEW IS ACTIVE ---
        if (window.isConsolidated) {
            this.hud.style.display = 'none';
            this.ctx.restore(); 
            return; 
        }

        // --- Standard 1 or 2 graph layout logic ---
        this.hud.style.display = 'flex';
        this.statsDiv.innerHTML = `
            <div style="margin-bottom: 2px; color: ${isDarkMode ? '#f8f9fa' : '#212529'};">True Area ≈ ${formatVal(trueArea)}</div>
            <div style="margin-bottom: 2px; color: ${themeColorHex};">${this.type} Sum ≈ ${formatVal(mySum)}</div>
            <div style="color: #f59f00;">Error = ${formatVal(err)}</div>
        `;

        // --- INTELLIGENT HUD POSITIONING ---
        let posPref = hudPosSelect.value;
        let finalPos = posPref;

        if (posPref === 'auto') {
            let scores = { tl: 0, tr: 0, bl: 0, br: 0 };
            
            let hudW = 200, hudH = 130; 
            let topBound = 45 + hudH; 
            let botBound = h - hudH - 12; 
            
            for(let px = 0; px <= w; px += Math.max(1, w/40)) {
                let x = xMin + (px/w)*(xMax-xMin);
                let y = f(x);
                if(isNaN(y)) continue;
                
                let sY = toScreenY(y);
                let sBase = toScreenY(0);
                let minVal = Math.min(sY, sBase); 
                let maxVal = Math.max(sY, sBase); 
                
                let isLeft = px < w/2;
                
                if (minVal < topBound) {
                    if (isLeft) scores.tl++; else scores.tr++;
                }
                if (maxVal > botBound) {
                    if (isLeft) scores.bl++; else scores.br++;
                }
            }
            
            let minScore = Math.min(scores.tl, scores.tr, scores.bl, scores.br);
            if (scores.tr === minScore) finalPos = 'tr';
            else if (scores.tl === minScore) finalPos = 'tl';
            else if (scores.br === minScore) finalPos = 'br';
            else finalPos = 'bl';
        }

        this.hud.style.top = 'auto'; this.hud.style.bottom = 'auto';
        this.hud.style.left = 'auto'; this.hud.style.right = 'auto';
        
        let pad = '12px';
        let topPad = '45px'; 

        if (finalPos === 'tl') { this.hud.style.top = topPad; this.hud.style.left = pad; } 
        if (finalPos === 'tr') { this.hud.style.top = topPad; this.hud.style.right = pad; }
        if (finalPos === 'bl') { this.hud.style.bottom = pad; this.hud.style.left = pad; }
        if (finalPos === 'br') { this.hud.style.bottom = pad; this.hud.style.right = pad; }

        this.ctx.restore(); 
    }
}

const plots = [new Plot('LHS'), new Plot('RHS'), new Plot('MPS')];

function updateLayoutVisibility() {
    plots[0].wrapper.style.display = chkLHS.checked ? 'flex' : 'none';
    plots[1].wrapper.style.display = chkRHS.checked ? 'flex' : 'none';
    plots[2].wrapper.style.display = chkMPS.checked ? 'flex' : 'none';

    let count = (chkLHS.checked ? 1 : 0) + (chkRHS.checked ? 1 : 0) + (chkMPS.checked ? 1 : 0);
    document.getElementById('grid-container').className = `layout-${count}`;
    
    // Set global flag to trigger the consolidated Master HUD
    window.isConsolidated = (count === 3);
}

// --- NEW Master Consolidated HUD Builder ---
function updateConsolidatedHUD() {
    const hud = document.getElementById('consolidatedHUD');
    if (!isEqValid || !window.isConsolidated) {
        hud.style.display = 'none';
        return;
    }
    hud.style.display = 'flex';

    let sf = parseInt(sigFigInput.value) || 4;
    const formatVal = (v) => (isNaN(v) || !isFinite(v)) ? "Undefined" : math.format(v, { precision: sf, notation: 'auto' });

    const styleObj = getComputedStyle(document.body);
    let colLHS = styleObj.getPropertyValue('--color-lhs').trim() || '#339af0';
    let colRHS = styleObj.getPropertyValue('--color-rhs').trim() || '#51cf66';
    let colMPS = styleObj.getPropertyValue('--color-mps').trim() || '#cc5de8';
    let mainCol = isDarkMode ? '#f8f9fa' : '#212529';
    
    // NEW Border color logic based on theme
    let borderCol = isDarkMode ? '#495057' : '#ced4da';
    
    // We now target the MIDDLE (Sums) element's top and bottom borders for separation
    let sumsDiv = document.getElementById('sumsConsolidated');
    sumsDiv.style.borderTop = `1px solid ${borderCol}`;
    sumsDiv.style.borderBottom = `1px solid ${borderCol}`;

    // Elements are visually swapped in HTML, we just populate them

    // TOP: Formula (Handled automatically by Katex in parseEquation)

    // MIDDLE: 3 Sums and Errors
    sumsDiv.innerHTML = `
        <div style="text-align: center;">
            <div style="color: ${colLHS}; font-weight: bold;">LHS ≈ ${formatVal(plots[0].currentSum)}</div>
            <div style="color: #f59f00; font-size: 0.85em; margin-top: 2px;">Err: ${formatVal(plots[0].currentErr)}</div>
        </div>
        <div style="text-align: center;">
            <div style="color: ${colRHS}; font-weight: bold;">RHS ≈ ${formatVal(plots[1].currentSum)}</div>
            <div style="color: #f59f00; font-size: 0.85em; margin-top: 2px;">Err: ${formatVal(plots[1].currentErr)}</div>
        </div>
        <div style="text-align: center;">
            <div style="color: ${colMPS}; font-weight: bold;">MPS ≈ ${formatVal(plots[2].currentSum)}</div>
            <div style="color: #f59f00; font-size: 0.85em; margin-top: 2px;">Err: ${formatVal(plots[2].currentErr)}</div>
        </div>
    `;

    // BOTTOM: True Area
    document.getElementById('trueAreaConsolidated').innerHTML = `
        <span style="color: ${mainCol}; font-weight: bold;">True Area ≈ ${formatVal(trueArea)}</span>
    `;
}

function triggerFullUpdate() {
    parseEquation();
    computeGlobalBounds();
    updateLayoutVisibility();

    requestAnimationFrame(() => {
        plots.forEach(p => p.draw());
        if (window.isConsolidated) {
            updateConsolidatedHUD();
        } else {
            document.getElementById('consolidatedHUD').style.display = 'none';
        }
    });
}

// Global Event Listeners
window.addEventListener('resize', () => {
    requestAnimationFrame(() => {
        plots.forEach(p => p.draw());
        if (window.isConsolidated) updateConsolidatedHUD();
    });
});

eqInput.addEventListener('input', () => { triggerFullUpdate(); saveState(); });
boundAInput.addEventListener('input', () => { triggerFullUpdate(); saveState(); });
boundBInput.addEventListener('input', () => { triggerFullUpdate(); saveState(); });
sigFigInput.addEventListener('input', () => { triggerFullUpdate(); saveState(); });
nInput.addEventListener('input', () => { triggerFullUpdate(); saveState(); }); 
hudPosSelect.addEventListener('change', () => { triggerFullUpdate(); saveState(); });

[chkLHS, chkRHS, chkMPS, chkError].forEach(chk => {
    chk.addEventListener('change', () => { triggerFullUpdate(); saveState(); });
});

triggerFullUpdate();
