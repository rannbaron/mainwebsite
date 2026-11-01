// --- APPLET SPECIFIC STATE ---
const STORAGE_KEY = 'logisticAppletV21';

const inputR = document.getElementById('inputR'); // Mathematically k
const inputK = document.getElementById('inputK'); // Mathematically L
const inputH = document.getElementById('inputH'); // Mathematically H
const valH = document.getElementById('valH');     
const inputTMax = document.getElementById('inputTMax');
const chkSlope = document.getElementById('chkSlope');

const chkP = [document.getElementById('chkP1'), document.getElementById('chkP2'), document.getElementById('chkP3')];
const pColors = ['#339af0', '#cc5de8', '#f59f00'];

let p0Values = [1200, 100, 110]; 
let draggingIndex = -1;

let p1ManualOverride = false;
let p2ManualOverride = false; 
let p3ManualOverride = false; 

let latexEq = "";
let equilibria = [];
let solutionCurves = [[], [], []];

// --- INITIALIZE SHARED UTILS ---
AppUtils.setupHelpModal('helpBtn', 'helpModal', 'closeHelpBtn');

AppUtils.setupSharing('shareBtn', () => {
    return {
        theme: AppUtils.isDarkMode,
        r: inputR.value, K: inputK.value, H: inputH.value,
        tMax: inputTMax.value, slope: chkSlope.checked,
        p0Vals: p0Values, p0Checks: chkP.map(c => c.checked),
        p1Manual: p1ManualOverride, p2Manual: p2ManualOverride, p3Manual: p3ManualOverride
    };
});

function saveLocal() {
    AppUtils.saveState(STORAGE_KEY, {
        theme: AppUtils.isDarkMode, r: inputR.value, K: inputK.value, H: inputH.value, 
        tMax: inputTMax.value, slope: chkSlope.checked,
        p0Vals: p0Values, p0Checks: chkP.map(c => c.checked),
        p1Manual: p1ManualOverride, p2Manual: p2ManualOverride, p3Manual: p3ManualOverride
    });
}

function loadLocal() {
    const { data, fromUrl } = AppUtils.loadState(STORAGE_KEY);
    if (data) {
        if (data.r !== undefined) inputR.value = data.r;
        if (data.K !== undefined) inputK.value = data.K;
        if (data.tMax !== undefined) inputTMax.value = data.tMax;
        if (data.slope !== undefined) chkSlope.checked = data.slope;
        if (data.p1Manual !== undefined) p1ManualOverride = data.p1Manual;
        if (data.p2Manual !== undefined) p2ManualOverride = data.p2Manual;
        if (data.p3Manual !== undefined) p3ManualOverride = data.p3Manual;
        if (data.H !== undefined) inputH.value = data.H;
        if (data.p0Vals) p0Values = data.p0Vals;
        if (data.p0Checks) data.p0Checks.forEach((chk, i) => chkP[i].checked = chk);
        
        if (fromUrl) {
            AppUtils.cleanUrlOnLoad();
            setTimeout(saveLocal, 500);
        }
    }
    
    const initialTheme = data && data.theme !== undefined ? data.theme : false;
    AppUtils.setupThemeToggle('themeToggle', initialTheme, () => {
        triggerFullUpdate();
        saveLocal();
    });
}

loadLocal();

// --- RESET APPLET LOGIC ---
document.getElementById('resetBtn').addEventListener('click', () => {
    inputR.value = 0.1; inputK.value = 1000; inputH.value = 0; inputTMax.value = 100;
    chkSlope.checked = true;
    chkP[0].checked = true; chkP[1].checked = true; chkP[2].checked = false;
    p0Values = [1200, 100, 110];
    p1ManualOverride = false; p2ManualOverride = false; p3ManualOverride = false;
    lastHForTrigger = 0;
    
    AppUtils.cleanUrlOnLoad();
    updateSliderBounds();
    valH.innerText = (0).toFixed(getHDecimals());
    triggerFullUpdate();
    saveLocal();
});

// --- Precision & Constraints ---
function getHDecimals() {
    let step = parseFloat(inputH.step) || 0.1;
    if (step < 0.009) return 3; 
    if (step < 0.09) return 2;  
    return 1;                   
}

function updateSliderBounds() {
    let k = parseFloat(inputR.value) || 0;
    let L = parseFloat(inputK.value) || 1;
    let maxH = 0.4 * k * L;
    
    if (parseFloat(inputH.max) !== maxH) {
        inputH.max = maxH;
        let step = maxH >= 100 ? 1 : (maxH >= 10 ? 0.1 : (maxH >= 1 ? 0.01 : 0.001));
        inputH.step = step;
    }
    
    if (parseFloat(inputH.value) > maxH) inputH.value = maxH;
    valH.innerText = (parseFloat(inputH.value) || 0).toFixed(getHDecimals());
}

// --- Math Engine ---
function dPdt(P, k, L, H) { return k * P * (1 - P / L) - H; }

function getTimeBounds() {
    let L = parseFloat(inputK.value) || 1;
    let tMax = parseFloat(inputTMax.value) || 100;
    return { xMin: -tMax * 0.028, xMax: tMax, yMin: 0, yMax: L * 1.3 };
}

function updateMath() {
    let k = parseFloat(inputR.value) || 0;
    let L = parseFloat(inputK.value) || 1;
    let H = parseFloat(inputH.value) || 0;
    let tMax = parseFloat(inputTMax.value) || 100;

    let H_str = H.toFixed(getHDecimals());
    latexEq = `\\frac{dP}{dt} = ${k} P \\left(1 - \\frac{P}{${L}}\\right) - ${H_str}`;
    
    ['Phase', 'Time'].forEach(type => {
        let overlay = document.getElementById(`mathOverlay${type}`);
        if (overlay) katex.render(latexEq, overlay, { throwOnError: false, displayMode: false });
    });

    let a = -k / L; let b = k; let c = -H;
    let discriminant = b*b - 4*a*c;
    let tolerance = 1e-8; 

    equilibria = [];
    if (discriminant > tolerance) {
        let p1 = (-b + Math.sqrt(discriminant)) / (2*a);
        let p2 = (-b - Math.sqrt(discriminant)) / (2*a);
        equilibria.push(Math.min(p1, p2)); 
        equilibria.push(Math.max(p1, p2)); 
    } else if (discriminant > -tolerance && discriminant <= tolerance) {
        equilibria.push(-b / (2*a)); 
    }

    if (!p1ManualOverride && chkP[0].checked) p0Values[0] = 1.2 * L;
    if (!p2ManualOverride && chkP[1].checked && equilibria.length === 2) p0Values[1] = equilibria[0] + 0.1 * (equilibria[1] - equilibria[0]);
    if (H > 0 && !p3ManualOverride && chkP[2].checked && equilibria.length > 0) p0Values[2] = 0.9 * equilibria[0];

    // RK4 Solver
    solutionCurves = [[], [], []];
    let steps = 400; let dt = tMax / steps;
    
    for (let cIdx = 0; cIdx < 3; cIdx++) {
        if (!chkP[cIdx].checked) continue;
        let currP = p0Values[cIdx];
        for(let i=0; i<=steps; i++) {
            let t = i * dt;
            solutionCurves[cIdx].push({t: t, P: currP});
            
            let k1 = dPdt(currP, k, L, H);
            let k2 = dPdt(currP + dt * k1 / 2, k, L, H);
            let k3 = dPdt(currP + dt * k2 / 2, k, L, H);
            let k4 = dPdt(currP + dt * k3, k, L, H);
            
            currP = currP + (dt / 6) * (k1 + 2*k2 + 2*k3 + k4);
            if (currP < 0) { solutionCurves[cIdx].push({t: t+dt, P: 0}); break; }
        }
    }
}

// --- Drag Interaction ---
const canvasTime = document.getElementById('canvasTime');

function getMousePos(e) {
    let rect = canvasTime.getBoundingClientRect();
    let clientX = e.touches ? e.touches[0].clientX : e.clientX;
    let clientY = e.touches ? e.touches[0].clientY : e.clientY;
    return { x: clientX - rect.left, y: clientY - rect.top };
}

function handleDragStart(e) {
    let pos = getMousePos(e); let bounds = getTimeBounds();
    let h = canvasTime.clientHeight; let w = canvasTime.clientWidth;
    let toScreenX = (x) => ((x - bounds.xMin) / (bounds.xMax - bounds.xMin)) * w;
    let toScreenY = (y) => h - ((y - bounds.yMin) / (bounds.yMax - bounds.yMin)) * h;

    if (Math.abs(pos.x - toScreenX(0)) < 25) {
        for (let i = 0; i < 3; i++) {
            if (chkP[i].checked && Math.abs(pos.y - toScreenY(p0Values[i])) < 20) {
                draggingIndex = i; canvasTime.style.cursor = 'ns-resize';
                if(e.cancelable) e.preventDefault(); break;
            }
        }
    }
}

function handleDragMove(e) {
    let pos = getMousePos(e); let bounds = getTimeBounds();
    let h = canvasTime.clientHeight; let w = canvasTime.clientWidth;
    
    if (draggingIndex !== -1) {
        let newP0 = bounds.yMin + (1 - pos.y / h) * (bounds.yMax - bounds.yMin);
        p0Values[draggingIndex] = Math.max(0, newP0); 
        
        if (draggingIndex === 0) p1ManualOverride = true;
        if (draggingIndex === 1) p2ManualOverride = true;
        if (draggingIndex === 2) p3ManualOverride = true;

        triggerFullUpdate(); if(e.cancelable) e.preventDefault();
    } else {
        let toScreenX = (x) => ((x - bounds.xMin) / (bounds.xMax - bounds.xMin)) * w;
        let toScreenY = (y) => h - ((y - bounds.yMin) / (bounds.yMax - bounds.yMin)) * h;
        let hovering = false;
        if (Math.abs(pos.x - toScreenX(0)) < 25) {
            for (let i = 0; i < 3; i++) {
                if (chkP[i].checked && Math.abs(pos.y - toScreenY(p0Values[i])) < 20) { hovering = true; break; }
            }
        }
        canvasTime.style.cursor = hovering ? 'ns-resize' : 'default';
    }
}

function handleDragEnd() {
    if (draggingIndex !== -1) {
        draggingIndex = -1;
        canvasTime.style.cursor = 'default';
        saveLocal();
    }
}

canvasTime.addEventListener('mousedown', handleDragStart);
window.addEventListener('mousemove', handleDragMove);
window.addEventListener('mouseup', handleDragEnd);
canvasTime.addEventListener('touchstart', handleDragStart, {passive: false});
window.addEventListener('touchmove', handleDragMove, {passive: false});
window.addEventListener('touchend', handleDragEnd);

// --- Plotting Engine ---
class Plot {
    constructor(type) {
        this.type = type; 
        this.canvas = document.getElementById(`canvas${type}`);
        this.ctx = this.canvas.getContext('2d');
        this.hud = document.getElementById(`hud${type}`);
        this.statsDiv = document.getElementById(`stats${type}`);
    }

    draw() {
        const dpr = window.devicePixelRatio || 1;
        const w = this.canvas.clientWidth;
        const h = this.canvas.clientHeight;
        if (w === 0 || h === 0) return;

        if (this.canvas.width !== w * dpr || this.canvas.height !== h * dpr) {
            this.canvas.width = w * dpr;
            this.canvas.height = h * dpr;
        }

        this.ctx.save();
        this.ctx.scale(dpr, dpr);
        this.ctx.clearRect(0, 0, w, h);

        let k = parseFloat(inputR.value) || 0;
        let L = parseFloat(inputK.value) || 1;
        let H = parseFloat(inputH.value) || 0;

        let bounds;
        if (this.type === 'Phase') {
            bounds = { xMin: -L * 0.1, xMax: L * 1.3, yMin: -k * L * 0.1, yMax: k * L * 0.3 };
            if (H > k * L * 0.25) bounds.yMin = -H * 1.2;
        } else {
            bounds = getTimeBounds();
        }

        const toScreenX = (x) => ((x - bounds.xMin) / (bounds.xMax - bounds.xMin)) * w;
        const toScreenY = (y) => h - ((y - bounds.yMin) / (bounds.yMax - bounds.yMin)) * h;
        
        let xAxisY = toScreenY(0);
        let yAxisX = toScreenX(0);

        const axisColor = AppUtils.isDarkMode ? '#495057' : '#ced4da';
        const tickColor = AppUtils.isDarkMode ? '#adb5bd' : '#6c757d';
        const curveColor = AppUtils.isDarkMode ? '#f8f9fa' : '#212529';

        this.ctx.strokeStyle = axisColor;
        this.ctx.lineWidth = 2;
        this.ctx.beginPath();
        this.ctx.moveTo(yAxisX, 0); this.ctx.lineTo(yAxisX, h);
        this.ctx.moveTo(0, xAxisY); this.ctx.lineTo(w, xAxisY);
        this.ctx.stroke();

        this.ctx.fillStyle = tickColor; this.ctx.strokeStyle = tickColor; this.ctx.font = '12px Arial'; this.ctx.lineWidth = 1;
        this.ctx.textAlign = 'center'; this.ctx.textBaseline = 'top';
        
        let xStep = SharedMath.getStandardStep(bounds.xMax - bounds.xMin);
        let yStep = SharedMath.getStandardStep(bounds.yMax - bounds.yMin);

        for (let x = Math.ceil(bounds.xMin / xStep) * xStep; x <= bounds.xMax; x += xStep) {
            if (Math.abs(x) < 1e-5) continue;
            let sx = toScreenX(x);
            this.ctx.beginPath(); this.ctx.moveTo(sx, xAxisY - 4); this.ctx.lineTo(sx, xAxisY + 4); this.ctx.stroke();
            this.ctx.fillText(Number.isInteger(x) ? x : x.toFixed(1), sx, xAxisY + 8);
        }

        this.ctx.textAlign = 'left'; this.ctx.textBaseline = 'middle';
        for (let y = Math.ceil(bounds.yMin / yStep) * yStep; y <= bounds.yMax; y += yStep) {
            if (Math.abs(y) < 1e-5) continue;
            let sy = toScreenY(y);
            this.ctx.beginPath(); this.ctx.moveTo(yAxisX - 4, sy); this.ctx.lineTo(yAxisX + 4, sy); this.ctx.stroke();
            this.ctx.fillText(Number.isInteger(y) ? y : y.toFixed(1), yAxisX + 8, sy);
        }
        
        this.ctx.textBaseline = this.type === 'Time' ? 'bottom' : 'top';
        this.ctx.fillText("0", yAxisX + 8, xAxisY + (this.type === 'Time' ? -8 : 8));

        const getEqColor = (index, totalEq) => totalEq === 2 && index === 1 ? '#51cf66' : (totalEq === 1 ? '#f59f00' : '#fa5252');

        if (this.type === 'Phase') {
            this.ctx.fillStyle = tickColor; this.ctx.textAlign = 'right'; this.ctx.textBaseline = 'bottom';
            this.ctx.fillText("Pop (P)", w - 10, xAxisY - 8);
            this.ctx.textAlign = 'left'; this.ctx.textBaseline = 'top';
            this.ctx.fillText("Growth (dP/dt)", yAxisX + 10, 10);

            this.ctx.strokeStyle = curveColor; this.ctx.lineWidth = 2.5; this.ctx.beginPath();
            for(let px = 0; px <= w; px++) {
                let P = bounds.xMin + (px/w)*(bounds.xMax - bounds.xMin);
                let growth = dPdt(P, k, L, H);
                if (px === 0) this.ctx.moveTo(px, toScreenY(growth));
                else this.ctx.lineTo(px, toScreenY(growth));
            }
            this.ctx.stroke();

            // --- HARVESTING (H) DOTTED LINE ---
            if (H > 0) {
                let pMid = L / 2;
                let topY = k * L / 4;
                let botY = topY - H;
                
                let sX = toScreenX(pMid);
                let sYTop = toScreenY(topY);
                let sYBot = toScreenY(botY);

                this.ctx.save();
                this.ctx.beginPath();
                this.ctx.setLineDash([4, 4]);
                this.ctx.strokeStyle = AppUtils.isDarkMode ? '#adb5bd' : '#6c757d'; 
                this.ctx.lineWidth = 2;
                this.ctx.moveTo(sX, sYTop);
                this.ctx.lineTo(sX, sYBot);
                this.ctx.stroke();

                this.ctx.setLineDash([]);
                this.ctx.fillStyle = AppUtils.isDarkMode ? '#f8f9fa' : '#212529';
                this.ctx.textAlign = 'left';
                this.ctx.textBaseline = 'middle';
                this.ctx.fillText(`H = ${H.toFixed(2)}`, sX + 6, (sYTop + sYBot) / 2);
                this.ctx.restore();
            }
            // ---------------------------------------------

            equilibria.forEach((eq, index) => {
                let sX = toScreenX(eq);
                let sY = toScreenY(0);
                
                this.ctx.fillStyle = getEqColor(index, equilibria.length);
                this.ctx.beginPath(); this.ctx.arc(sX, sY, 6, 0, Math.PI*2); this.ctx.fill();
                this.ctx.strokeStyle = AppUtils.isDarkMode ? '#212529' : '#fff';
                this.ctx.lineWidth = 1.5; this.ctx.stroke();
                
                this.ctx.fillStyle = AppUtils.isDarkMode ? '#f8f9fa' : '#212529';
                this.ctx.textAlign = 'center'; this.ctx.textBaseline = 'top';
                this.ctx.fillText(eq.toFixed(1), sX, sY + 12);
            });

        } else {
            this.ctx.fillStyle = tickColor; this.ctx.textAlign = 'right'; this.ctx.textBaseline = 'bottom';
            this.ctx.fillText("Time (t)", w - 10, xAxisY - 8);
            this.ctx.textAlign = 'left'; this.ctx.textBaseline = 'top';
            this.ctx.fillText("Pop (P)", yAxisX + 10, 10);

            if (chkSlope.checked) {
                let dens = 25;
                let dxScreen = w / dens;
                let dyScreen = h / dens;
                let dx = (bounds.xMax - bounds.xMin) / dens;
                let dy = (bounds.yMax - bounds.yMin) / dens;
                
                this.ctx.strokeStyle = AppUtils.isDarkMode ? '#6c757d' : '#adb5bd';
                this.ctx.lineWidth = 1.5;
                let tickLen = Math.min(dxScreen, dyScreen) * 0.6;
                
                // THE FIX: Calculate the pixel ratio correctly (Y-scale / X-scale)
                let pxRatio = (dyScreen / dy) / (dxScreen / dx);
                
                for(let ix = 0; ix <= dens; ix++) {
                    for(let iy = 0; iy <= dens; iy++) {
                        let t = bounds.xMin + ix * dx;
                        let P = bounds.yMin + iy * dy;
                        let slope = dPdt(P, k, L, H);
                        
                        if (!isNaN(slope) && isFinite(slope)) {
                            // Apply the pxRatio to bend the ticks accurately
                            let angle = Math.atan(slope * pxRatio);
                            let sDx = Math.cos(angle) * tickLen / 2;
                            let sDy = Math.sin(angle) * tickLen / 2;
                            let cx = toScreenX(t);
                            let cy = toScreenY(P);
                            
                            this.ctx.beginPath();
                            this.ctx.moveTo(cx - sDx, cy + sDy);
                            this.ctx.lineTo(cx + sDx, cy - sDy);
                            this.ctx.stroke();
                        }
                    }
                }
            }

            this.ctx.setLineDash([6, 6]);
            this.ctx.lineWidth = 1.5;
            equilibria.forEach((eq, index) => {
                let sY = toScreenY(eq);
                this.ctx.strokeStyle = getEqColor(index, equilibria.length);
                this.ctx.beginPath(); this.ctx.moveTo(0, sY); this.ctx.lineTo(w, sY); this.ctx.stroke();
            });
            this.ctx.setLineDash([]);

            for (let cIdx = 0; cIdx < 3; cIdx++) {
                if (!chkP[cIdx].checked || solutionCurves[cIdx].length === 0) continue;
                
                this.ctx.strokeStyle = pColors[cIdx];
                this.ctx.lineWidth = 3;
                this.ctx.beginPath();
                
                let first = true;
                for (let pt of solutionCurves[cIdx]) {
                    let sx = toScreenX(pt.t);
                    let sy = toScreenY(pt.P);
                    if (first) { this.ctx.moveTo(sx, sy); first = false; }
                    else { this.ctx.lineTo(sx, sy); }
                }
                this.ctx.stroke();

                let pt0 = solutionCurves[cIdx][0];
                let sX = toScreenX(pt0.t);
                let sY = toScreenY(pt0.P);
                this.ctx.fillStyle = pColors[cIdx];
                this.ctx.beginPath(); this.ctx.arc(sX, sY, draggingIndex === cIdx ? 8 : 6, 0, Math.PI*2); this.ctx.fill();
                this.ctx.strokeStyle = AppUtils.isDarkMode ? '#212529' : '#fff';
                this.ctx.lineWidth = 1.5; this.ctx.stroke();
            }
        }

        if (this.type === 'Phase') {
            this.statsDiv.innerHTML = `<div style="font-weight: 500;">Equilibria:</div>`;
            if (equilibria.length === 0) {
                this.statsDiv.innerHTML += `<div style="color: #fa5252; margin-top: 4px;">None (Extinction)</div>`;
            } else {
                equilibria.forEach((eq, idx) => {
                    let col = getEqColor(idx, equilibria.length);
                    this.statsDiv.innerHTML += `<div style="color: ${col}; margin-top: 4px;">P = ${eq.toFixed(1)}</div>`;
                });
            }

            let scores = { tl: 0, tr: 0, bl: 0, br: 0 };
            for(let px = 0; px <= w; px += w/10) {
                let P = bounds.xMin + (px/w)*(bounds.xMax-bounds.xMin);
                let sY = toScreenY(dPdt(P, k, L, H));
                if (sY < 100) px < w/2 ? scores.tl++ : scores.tr++;
                if (sY > h-100) px < w/2 ? scores.bl++ : scores.br++;
            }
            let minScore = Math.min(scores.tl, scores.tr, scores.bl, scores.br);
            let finalPos = 'tr';
            if (scores.tr === minScore) finalPos = 'tr';
            else if (scores.tl === minScore) finalPos = 'tl';
            else if (scores.br === minScore) finalPos = 'br';
            else finalPos = 'bl';

            this.hud.style.top = 'auto'; this.hud.style.bottom = 'auto'; this.hud.style.left = 'auto'; this.hud.style.right = 'auto';
            let pad = '12px'; let topPad = '45px'; 
            if (finalPos === 'tl') { this.hud.style.top = topPad; this.hud.style.left = pad; } 
            if (finalPos === 'tr') { this.hud.style.top = topPad; this.hud.style.right = pad; }
            if (finalPos === 'bl') { this.hud.style.bottom = pad; this.hud.style.left = pad; }
            if (finalPos === 'br') { this.hud.style.bottom = pad; this.hud.style.right = pad; }
        }

        this.ctx.restore(); 
    }
}

const plots = [new Plot('Phase'), new Plot('Time')];

function triggerFullUpdate() { 
    updateSliderBounds(); updateMath(); 
    requestAnimationFrame(() => { plots.forEach(p => p.draw()); }); 
}

window.addEventListener('resize', triggerFullUpdate);

let lastHForTrigger = parseFloat(inputH.value) || 0;
inputH.addEventListener('input', (e) => { 
    let newH = parseFloat(e.target.value);
    valH.innerText = newH.toFixed(getHDecimals()); 
    if (newH > 0 && lastHForTrigger === 0) chkP[2].checked = true;
    lastHForTrigger = newH;
    triggerFullUpdate(); saveLocal(); 
});

[inputR, inputK, inputTMax, chkSlope, chkP[0], chkP[1], chkP[2]].forEach(el => {
    el.addEventListener('input', () => { triggerFullUpdate(); saveLocal(); });
    el.addEventListener('change', () => { triggerFullUpdate(); saveLocal(); });
});

valH.innerText = parseFloat(inputH.value).toFixed(getHDecimals());
triggerFullUpdate();
