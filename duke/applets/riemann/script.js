math.config({ predictable: true });

// --- STATE & UTILS ---
const STORAGE_KEY = 'riemannAppStateV18';
const $ = id => document.getElementById(id);
const ui = {
    eq: $('eqInput'), a: $('boundA'), b: $('boundB'), n: $('nInput'), sig: $('sigFigInput'),
    hud: $('hudPos'), warn: $('improperWarning'), lhs: $('chkLHS'), rhs: $('chkRHS'), 
    mps: $('chkMPS'), err: $('chkError')
};

let compiledEq = null, isEqValid = false, isTrigMode = false;
let globalFinalTex = "", globalBounds = { xMin: -1, xMax: 1, yMin: -1, yMax: 1 }, trueArea = 0;

// --- STATE MANAGEMENT ---
const getState = () => ({
    theme: AppUtils.isDarkMode, eq: ui.eq.value, boundA: ui.a.value, boundB: ui.b.value,
    n: ui.n.value, sigFigs: ui.sig.value, hudPos: ui.hud.value,
    toggles: { lhs: ui.lhs.checked, rhs: ui.rhs.checked, mps: ui.mps.checked, err: ui.err.checked }
});

AppUtils.setupHelpModal('helpBtn', 'helpModal', 'closeHelpBtn');
AppUtils.setupSharing('shareBtn', getState);
const saveLocal = () => { if(plots) AppUtils.saveState(STORAGE_KEY, getState()); };

function loadLocal() {
    const { data, fromUrl } = AppUtils.loadState(STORAGE_KEY);
    if (data) {
        // Safe mapping to bridge localStorage keys to our shortened ui object keys
        const propMap = { eq: 'eq', boundA: 'a', boundB: 'b', n: 'n', sigFigs: 'sig', hudPos: 'hud' };
        Object.keys(propMap).forEach(key => {
            if (data[key] !== undefined) ui[propMap[key]].value = data[key];
        });
        
        if (data.toggles) {
            ['lhs', 'rhs', 'mps', 'err'].forEach(k => ui[k].checked = data.toggles[k]);
        }
        
        if (fromUrl) { AppUtils.cleanUrlOnLoad(); setTimeout(saveLocal, 500); }
    }
    AppUtils.setupThemeToggle('themeToggle', data?.theme || false, () => { triggerFullUpdate(); saveLocal(); });
}
loadLocal();

// --- MATH LOGIC ---
function parseEquation() {
    try {
        const { compiled, tex, isTrigMode: trig } = SharedMath.parseEquation(ui.eq.value, ['x', 'e', 'pi']);
        compiledEq = compiled; isTrigMode = trig; compiledEq.evaluate({x: 1}); 
        ui.eq.classList.remove('error'); isEqValid = true;
        globalFinalTex = `f(x) = \\displaystyle ${tex}`;
        
        ['LHS', 'RHS', 'MPS', 'Consolidated'].forEach(t => {
            let el = $(`mathOverlay${t}`);
            if (el) katex.render(globalFinalTex, el, { throwOnError: false, displayMode: t === 'Consolidated' });
        });
    } catch (e) {
        ui.eq.classList.add('error'); isEqValid = false;
        ['LHS', 'RHS', 'MPS', 'Consolidated'].forEach(t => { let el = $(`mathOverlay${t}`); if(el) el.innerHTML = ''; });
    }
}

function getBound(inputEl, fallback) {
    try {
        let val = math.evaluate(SharedMath.formatImplicitMath(inputEl.value));
        if (typeof val === 'number' && !isNaN(val)) { inputEl.classList.remove('error'); return val; }
    } catch (e) {}
    inputEl.classList.add('error'); return fallback;
}

const f = (x) => { try { let r = compiledEq.evaluate({x}); return (typeof r === 'object' || isNaN(r)) ? NaN : r; } catch { return NaN; } };

function computeGlobalBounds() {
    if (!isEqValid) return;
    let a = getBound(ui.a, 0), b = getBound(ui.b, 5);
    if (a > b) [a, b] = [b, a];
    if (a === b) b = a + 1;

    let isImproper = false, dxCheck = (b - a) / 1000;
    for (let i = 0; i <= 1000; i++) {
        let y = f(a + i * dxCheck);
        if (Number.isNaN(y) || !Number.isFinite(y) || Math.abs(y) > 1e6) { isImproper = true; break; }
    }
    ui.warn.style.display = isImproper ? 'block' : 'none';

    let xSpan = b - a;
    globalBounds = { xMin: a - xSpan * 0.15, xMax: b + xSpan * 0.15, yMin: Infinity, yMax: -Infinity };

    for (let i = 0; i <= 500; i++) {
        let y = f(globalBounds.xMin + (globalBounds.xMax - globalBounds.xMin) * (i / 500));
        if (isFinite(y) && Math.abs(y) < 1e6) {
            globalBounds.yMax = Math.max(globalBounds.yMax, y);
            globalBounds.yMin = Math.min(globalBounds.yMin, y);
        }
    }

    if (globalBounds.yMax === -Infinity) { globalBounds.yMax = 10; globalBounds.yMin = -10; } 
    if (globalBounds.yMax === globalBounds.yMin) { globalBounds.yMax += 5; globalBounds.yMin -= 5; }

    globalBounds.yMin = Math.min(0, globalBounds.yMin - (globalBounds.yMax - globalBounds.yMin) * 0.15);
    globalBounds.yMax = Math.max(0, globalBounds.yMax + (globalBounds.yMax - globalBounds.yMin) * 0.15);
    if (isImproper) { globalBounds.yMax = Math.min(100, globalBounds.yMax); globalBounds.yMin = Math.max(-100, globalBounds.yMin); }
}

function calculateTrueArea() {
    if (!isEqValid) return trueArea = 0;
    let a = getBound(ui.a, 0), b = getBound(ui.b, 5);
    if (a === b) return trueArea = 0;
    if (a > b) [a, b] = [b, a];

    let h = (b - a) / 2000, sum1 = 0, sum2 = 0;
    for(let i=1; i<2000; i+=2) { let y = f(a + i*h); if (isFinite(y)) sum1 += y; }
    for(let i=2; i<1999; i+=2) { let y = f(a + i*h); if (isFinite(y)) sum2 += y; }
    
    let fa = f(a), fb = f(b);
    trueArea = (h/3) * ((isFinite(fa)?fa:0) + (isFinite(fb)?fb:0) + 4*sum1 + 2*sum2);
}

const formatVal = (val) => {
    if (isNaN(val) || !isFinite(val)) return "Undefined";
    if (Math.abs(val) < 1e-12) return "0";
    return Number(val.toPrecision(parseInt(ui.sig.value) || 4)).toString();
};

function updateLayoutVisibility() {
    ['LHS', 'RHS', 'MPS'].forEach(t => $(`wrapper${t}`).style.display = ui[t.toLowerCase()].checked ? 'block' : 'none');
    let count = [ui.lhs.checked, ui.rhs.checked, ui.mps.checked].filter(Boolean).length;
    let grid = $('grid-container');
    grid.className = count === 3 ? 'layout-3' : '';
    grid.style.gridTemplateColumns = count === 2 ? '1fr 1fr' : '1fr';
    window.isConsolidated = count === 3;
}

// --- RENDERING ---
class Plot {
    constructor(type) {
        this.type = type;
        this.wrapper = $(`wrapper${type}`);
        this.canvas = $(`canvas${type}`);
        this.ctx = this.canvas.getContext('2d');
        this.hud = $(`hud${type}`);
        this.statsDiv = $(`stats${type}`);
        this.currentSum = 0; this.currentErr = 0;
    }

    resolveColor() {
        let val = getComputedStyle(document.body).getPropertyValue(`--color-${this.type.toLowerCase()}`).trim();
        if (val) return val;
        const fallbacks = { LHS: ['#fa5252', '#ff8787'], RHS: ['#228be6', '#4dabf7'], MPS: ['#40c057', '#8ce99a'] };
        return fallbacks[this.type][AppUtils.isDarkMode ? 1 : 0];
    }

    draw() {
        if (this.wrapper.style.display === 'none') return;
        this.color = this.resolveColor();

        const dpr = window.devicePixelRatio || 1, w = this.canvas.clientWidth, h = this.canvas.clientHeight;
        if (w === 0 || h === 0) return;
        if (this.canvas.width !== w * dpr || this.canvas.height !== h * dpr) { this.canvas.width = w * dpr; this.canvas.height = h * dpr; }

        this.ctx.save(); this.ctx.scale(dpr, dpr); this.ctx.clearRect(0, 0, w, h);
        if (!isEqValid) return this.ctx.restore();

        let a = getBound(ui.a, 0), b = getBound(ui.b, 5), n = parseInt(ui.n.value) || 1, bnds = globalBounds;
        if (a > b) [a, b] = [b, a];
        
        const sX = (x) => ((x - bnds.xMin) / (bnds.xMax - bnds.xMin)) * w;
        const sY = (y) => h - ((y - bnds.yMin) / (bnds.yMax - bnds.yMin)) * h;

        // Axes
        this.ctx.strokeStyle = AppUtils.isDarkMode ? '#495057' : '#ced4da'; this.ctx.lineWidth = 2; this.ctx.beginPath();
        this.ctx.moveTo(sX(0), 0); this.ctx.lineTo(sX(0), h); this.ctx.moveTo(0, sY(0)); this.ctx.lineTo(w, sY(0)); this.ctx.stroke();

        // Ticks
        let xStep = isTrigMode && SharedMath.getStandardStep(bnds.xMax - bnds.xMin) > 0.5 ? Math.PI/2 : SharedMath.getStandardStep(bnds.xMax - bnds.xMin);
        let yStep = SharedMath.getStandardStep(bnds.yMax - bnds.yMin);
        this.ctx.fillStyle = this.ctx.strokeStyle = AppUtils.isDarkMode ? '#adb5bd' : '#6c757d'; this.ctx.font = '12px Arial'; this.ctx.lineWidth = 1;
        
        this.ctx.textAlign = 'center'; this.ctx.textBaseline = 'top';
        for (let x = Math.ceil(bnds.xMin / xStep) * xStep; x <= bnds.xMax; x += xStep) {
            if (Math.abs(x) < 1e-5) continue;
            this.ctx.beginPath(); this.ctx.moveTo(sX(x), sY(0) - 4); this.ctx.lineTo(sX(x), sY(0) + 4); this.ctx.stroke();
            let lbl = Number.isInteger(x) ? x : x.toFixed(1);
            if (isTrigMode && Math.abs(x/Math.PI) > 1e-5) {
                let p = x/Math.PI; lbl = Math.abs(p-1)<1e-5 ? "π" : Math.abs(p+1)<1e-5 ? "-π" : Math.abs(p-0.5)<1e-5 ? "π/2" : Math.abs(p+0.5)<1e-5 ? "-π/2" : `${p.toFixed(1)}π`;
            }
            this.ctx.fillText(lbl, sX(x), sY(0) + 8);
        }

        this.ctx.textAlign = 'left'; this.ctx.textBaseline = 'middle';
        for (let y = Math.ceil(bnds.yMin / yStep) * yStep; y <= bnds.yMax; y += yStep) {
            if (Math.abs(y) < 1e-5) continue;
            this.ctx.beginPath(); this.ctx.moveTo(sX(0) - 4, sY(y)); this.ctx.lineTo(sX(0) + 4, sY(y)); this.ctx.stroke();
            this.ctx.fillText(Number.isInteger(y) ? y : y.toFixed(1), sX(0) + 8, sY(y));
        }

        // Rectangles
        let dx = (b - a) / n; this.currentSum = 0; this.ctx.lineWidth = 1.5;
        for (let i = 0; i < n; i++) {
            let xL = a + i * dx, xR = a + (i + 1) * dx, evalX = this.type === 'LHS' ? xL : (this.type === 'RHS' ? xR : (xL + xR) / 2);
            let hVal = f(evalX);
            if (!isFinite(hVal)) continue;

            this.currentSum += hVal * dx;
            let sXL = sX(xL), sXR = sX(xR), sY0 = sY(0), sYH = sY(hVal);

            this.ctx.fillStyle = this.color; this.ctx.globalAlpha = AppUtils.isDarkMode ? 0.3 : 0.15;
            this.ctx.fillRect(sXL, Math.min(sY0, sYH), sXR - sXL, Math.abs(sYH - sY0));
            this.ctx.globalAlpha = 1.0; this.ctx.strokeStyle = this.color;
            this.ctx.strokeRect(sXL, Math.min(sY0, sYH), sXR - sXL, Math.abs(sYH - sY0));

            if (ui.err.checked) {
                this.ctx.save(); this.ctx.beginPath(); this.ctx.moveTo(sXL, sYH);
                for(let errX = xL; errX <= xR; errX += (xR-xL)/20) this.ctx.lineTo(sX(errX), sY(f(errX)));
                this.ctx.lineTo(sXR, sYH); this.ctx.closePath();
                this.ctx.fillStyle = 'rgba(245, 159, 0, 0.4)'; this.ctx.fill(); this.ctx.restore();
            }

            this.ctx.fillStyle = this.color; this.ctx.beginPath(); this.ctx.arc(sX(evalX), sYH, 4, 0, Math.PI*2); this.ctx.fill();
            this.ctx.strokeStyle = AppUtils.isDarkMode ? '#212529' : '#fff'; this.ctx.stroke();
        }

        // Curve
        this.currentErr = Math.abs(trueArea - this.currentSum);
        this.ctx.strokeStyle = AppUtils.isDarkMode ? '#f8f9fa' : '#212529'; this.ctx.lineWidth = 2.5; this.ctx.beginPath();
        for(let px = 0, first = true; px <= w; px+=2) {
            let y = f(bnds.xMin + (px/w)*(bnds.xMax - bnds.xMin));
            if (isFinite(y)) { if(first) { this.ctx.moveTo(px, sY(y)); first=false; } else this.ctx.lineTo(px, sY(y)); } else first = true;
        }
        this.ctx.stroke();

        this.statsDiv.innerHTML = `<div style="color:${this.color}; font-weight:bold;">Area ≈ ${formatVal(this.currentSum)}</div><div style="font-size:0.9em; color:var(--text-color); margin-top:4px;">Error: ${formatVal(this.currentErr)}</div>`;
        this.hud.style.display = window.isConsolidated ? 'none' : 'flex';
        if (!window.isConsolidated) this.positionHUD(w, h, bnds, sY);
        this.ctx.restore(); 
    }

    positionHUD(w, h, bnds, sY) {
        let pref = ui.hud.value;
        this.hud.style.top = this.hud.style.bottom = this.hud.style.left = this.hud.style.right = 'auto';
        
        if (pref === 'auto') {
            let scores = { tl: 0, tr: 0, bl: 0, br: 0 };
            for(let px = 0; px <= w; px += w/20) {
                let y = sY(f(bnds.xMin + (px/w)*(bnds.xMax-bnds.xMin)));
                if (y < 100) px < w/2 ? scores.tl++ : scores.tr++;
                if (y > h-100) px < w/2 ? scores.bl++ : scores.br++;
            }
            let min = Math.min(scores.tl, scores.tr, scores.bl, scores.br);
            pref = scores.tr === min ? 'tr' : scores.tl === min ? 'tl' : scores.br === min ? 'br' : 'bl';
        }
        this.hud.style[pref[0]==='t'?'top':'bottom'] = pref[0]==='t'?'45px':'12px';
        this.hud.style[pref[1]==='l'?'left':'right'] = '12px';
    }
}

const plots = [new Plot('LHS'), new Plot('RHS'), new Plot('MPS')];

function updateConsolidatedHUD() {
    const cHUD = $('consolidatedHUD');
    if (!window.isConsolidated) return cHUD.style.display = 'none';
    cHUD.style.display = 'block';
    const errCol = AppUtils.isDarkMode ? '#adb5bd' : '#6c757d';

    $('sumsConsolidated').innerHTML = plots.map(p => `
        <div style="text-align: center; ${p.type !== 'LHS' ? 'border-left: 1px solid var(--border-light); padding-left: 15px;' : ''}">
            <div style="color: var(--color-${p.type.toLowerCase()}); font-size: 1.1em; font-weight: bold;">${p.type} ≈ ${formatVal(p.currentSum)}</div>
            <div style="color: ${errCol}; font-size: 0.85em;">Err: ${formatVal(p.currentErr)}</div>
        </div>
    `).join('');
    $('trueAreaConsolidated').innerHTML = `<span style="color: var(--text-main); font-weight: bold;">True Area ≈ ${formatVal(trueArea)}</span>`;
}

function triggerFullUpdate() {
    parseEquation(); computeGlobalBounds(); calculateTrueArea(); updateLayoutVisibility();
    requestAnimationFrame(() => { plots.forEach(p => p.draw()); updateConsolidatedHUD(); });
}

// --- EVENT LISTENERS ---
window.addEventListener('resize', () => requestAnimationFrame(() => { plots.forEach(p => p.draw()); if(window.isConsolidated) updateConsolidatedHUD(); }));
['eq', 'a', 'b', 'sig', 'n'].forEach(k => ui[k].addEventListener('input', () => { triggerFullUpdate(); saveLocal(); }));
ui.hud.addEventListener('change', () => { triggerFullUpdate(); saveLocal(); }); // Select needs change event
['lhs', 'rhs', 'mps', 'err'].forEach(k => ui[k].addEventListener('change', () => { triggerFullUpdate(); saveLocal(); }));

triggerFullUpdate();