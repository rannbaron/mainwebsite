math.config({ predictable: true });

// --- STATE & UTILS ---
const STORAGE_KEY = 'slopeFieldAppStateV5'; // Bumped for individual viewports
const $ = id => document.getElementById(id);
const $$ = (id, n) => Array.from({length: n}, (_, i) => $(`${id}${i}`));

let savedPointsData = null, savedViewports = null;

const ui = {
    layout: $('layoutSelect'), dens: $('densitySlider'), len: $('lengthSlider'),
    vpXMin: $('vpXMin'), vpXMax: $('vpXMax'), vpYMin: $('vpYMin'), vpYMax: $('vpYMax'),
    vpLock: $('vpLockAspect'), resetBtn: $('resetViewBtn'),
    sols: $$('sol', 4), eqs: $$('eqInput', 4)
};

const getState = () => ({
    theme: AppUtils.isDarkMode, layout: ui.layout.value, density: ui.dens.value, length: ui.len.value,
    sols: ui.sols.map(cb => cb.checked), eqs: ui.eqs.map(i => i.value),
    points: plots.map(p => p.points), viewports: plots.map(p => p.vp)
});

AppUtils.setupHelpModal('helpBtn', 'helpModal', 'closeHelpBtn');
AppUtils.setupSharing('shareBtn', getState);

const saveLocal = () => { if(plots?.length) AppUtils.saveState(STORAGE_KEY, getState()); };

function loadLocal() {
    const { data, fromUrl } = AppUtils.loadState(STORAGE_KEY);
    if (data) {
        if (data.layout) ui.layout.value = data.layout;
        if (data.density) { ui.dens.value = data.density; $('densityVal').innerText = data.density; }
        if (data.length) { ui.len.value = data.length; $('lengthVal').innerText = data.length; }
        if (data.sols) ui.sols.forEach((cb, i) => { if (data.sols[i] !== undefined) cb.checked = data.sols[i]; });
        if (data.eqs) ui.eqs.forEach((inp, i) => { if (data.eqs[i]) inp.value = data.eqs[i]; });
        if (data.points) savedPointsData = data.points;
        
        // Load individual viewports (with backwards compatibility for older shared customViewport)
        if (data.viewports) savedViewports = data.viewports;
        else if (data.viewport) savedViewports = Array(4).fill(data.viewport);

        if (savedViewports && savedViewports[0] && ui.vpXMin) {
            let vp = savedViewports[0];
            ['XMin', 'XMax', 'YMin', 'YMax'].forEach(k => ui[`vp${k}`].value = vp[`x${k.slice(1)}`] || vp[`y${k.slice(1)}`]);
            ui.vpLock.checked = vp.lockAspect;
            ui.vpYMin.disabled = ui.vpYMax.disabled = vp.lockAspect;
        }
        if (fromUrl) { AppUtils.cleanUrlOnLoad(); setTimeout(saveLocal, 500); }
    }
    AppUtils.setupThemeToggle('themeToggle', data?.theme || false, () => { plots.forEach(p => p.needsBgUpdate = true); triggerRedraw(); saveLocal(); });
}
loadLocal();

// --- ENGINE ---
const colors = ['#E63946', '#2A9D8F', '#E9C46A', '#9B5DE5'];

class Plot {
    constructor(id, initialPoints) {
        this.id = id; this.wrapper = $(`wrapper${id}`); this.canvas = $(`canvas${id}`);
        this.canvas.style.touchAction = 'none'; this.ctx = this.canvas.getContext('2d');
        this.eqInput = ui.eqs[id]; this.eqContainer = $(`eqContainer${id}`); this.label = this.wrapper.querySelector('.plot-label');
        
        this.xMin = -10; this.xMax = 10; this.yMin = -10; this.yMax = 10;
        this.points = initialPoints || [{x: 4, y: 3}, {x: 0, y: -1}, {x: -2, y: 0.5}, {x: 2, y: -0.5}];
        
        // Give each plot its own isolated viewport
        this.vp = savedViewports?.[id] ? {...savedViewports[id]} : { active: false, xMin: -10, xMax: 10, yMin: -10, yMax: 10, lockAspect: true };
        
        this.compiledEq = null; this.draggingPoint = null; this.isPanning = false; 
        this.lastPanMx = 0; this.lastPanMy = 0; this.lastTap = 0; 
        this.initialPinchDistance = null; this.initialPinchCenter = null; this.initVp = null;

        // GC Optimizations Pre-allocations
        this.k1 = {x:0, y:0}; this.k2 = {x:0, y:0}; this.k3 = {x:0, y:0}; this.k4 = {x:0, y:0};
        this.evalScope = { x: 0, y: 0, e: Math.E, pi: Math.PI };

        this.eqInput.addEventListener('input', () => { this.updateEquation(); saveLocal(); });
        this.bgCanvas = document.createElement('canvas'); this.bgCtx = this.bgCanvas.getContext('2d'); this.needsBgUpdate = true; 

        this.bindEvents(); this.updateEquation();
    }

    sX(x) { return ((x - this.xMin) / (this.xMax - this.xMin)) * this.canvas.width; }
    sY(y) { return this.canvas.height - ((y - this.yMin) / (this.yMax - this.yMin)) * this.canvas.height; }
    mX(px) { return (px / this.canvas.width) * (this.xMax - this.xMin) + this.xMin; }
    mY(py) { return this.yMin + ((this.canvas.height - py) / this.canvas.height) * (this.yMax - this.yMin); }

    updateEquation() {
        try {
            const { compiled, tex } = SharedMath.parseEquation(this.eqInput.value, ['x', 'y', 'e', 'pi']);
            this.compiledEq = compiled; this.compiledEq.evaluate({x: 1, y: 1}); this.eqInput.classList.remove('error');
            katex.render(`\\text{Plot ${this.id + 1}: } \\displaystyle \\frac{dy}{dx} = ${tex}`, this.label, { throwOnError: false, displayMode: false });
            this.needsBgUpdate = true; this.draw();
        } catch { this.eqInput.classList.add('error'); }
    }

    getDeriv(x, y) {
        if(!this.compiledEq) return NaN;
        try { 
            this.evalScope.x = x; this.evalScope.y = y; let r = this.compiledEq.evaluate(this.evalScope);
            return (typeof r === 'object' || isNaN(r) || (!isFinite(r) && Math.abs(r) !== Infinity)) ? NaN : r; 
        } catch { return NaN; }
    }

    getOrientedDerivTo(x, y, dx, dy, out) {
        let m = this.getDeriv(x, y); if (isNaN(m)) return out.x = out.y = 0;
        let vx = !isFinite(m) ? 0 : 1, vy = !isFinite(m) ? 1 : m;
        let mag = Math.sqrt(vx*vx + vy*vy); vx /= mag; vy /= mag; // Fast Math
        if (vx*dx + vy*dy < 0) { vx = -vx; vy = -vy; }
        out.x = vx; out.y = vy;
    }

    rk4(x0, y0, dir, max_steps) {
        let h = 0.01, pts = [{x: x0, y: y0}], x = x0, y = y0, m0 = this.getDeriv(x0, y0);
        if (isNaN(m0)) return pts;
        let vx0 = !isFinite(m0)?0:1, vy0 = !isFinite(m0)?1:m0, mag0 = Math.sqrt(vx0*vx0 + vy0*vy0), dx = (vx0/mag0)*dir, dy = (vy0/mag0)*dir;

        for(let i=0; i<max_steps; i++) {
            this.getOrientedDerivTo(x, y, dx, dy, this.k1); if (!this.k1.x && !this.k1.y) break; 
            this.getOrientedDerivTo(x + h/2*this.k1.x, y + h/2*this.k1.y, this.k1.x, this.k1.y, this.k2);
            this.getOrientedDerivTo(x + h/2*this.k2.x, y + h/2*this.k2.y, this.k2.x, this.k2.y, this.k3);
            this.getOrientedDerivTo(x + h*this.k3.x, y + h*this.k3.y, this.k3.x, this.k3.y, this.k4);
            
            let sx = (this.k1.x + 2*this.k2.x + 2*this.k3.x + this.k4.x)/6, sy = (this.k1.y + 2*this.k2.y + 2*this.k3.y + this.k4.y)/6;
            let sMag = Math.sqrt(sx*sx + sy*sy); if (sMag < 1e-5) break; 
            
            x += h * (dx = sx/sMag); y += h * (dy = sy/sMag); pts.push({x, y});
            if (x < this.xMin-5 || x > this.xMax+5 || y < this.yMin-5 || y > this.yMax+5) break;
        }
        return pts;
    }

    draw() {
        let w = this.canvas.clientWidth, h = this.canvas.clientHeight; if(!w || !h) return;
        if(this.canvas.width !== w || this.canvas.height !== h) {
            this.canvas.width = this.bgCanvas.width = w; this.canvas.height = this.bgCanvas.height = h; this.needsBgUpdate = true;
        }

        let asp = w / h;
        if (!this.vp.active) {
            let s = 20; if (asp >= 1) { this.yMax = s/2; this.yMin = -this.yMax; this.xMax = this.yMax*asp; this.xMin = -this.xMax; }
            else { this.xMax = s/2; this.xMin = -this.xMax; this.yMax = this.xMax/asp; this.yMin = -this.yMax; }
            if (this.id === 0 && ui.vpXMin && document.activeElement !== ui.vpXMin && document.activeElement !== ui.vpXMax) {
                ui.vpXMin.value = this.xMin.toFixed(2); ui.vpXMax.value = this.xMax.toFixed(2); ui.vpYMin.value = this.yMin.toFixed(2); ui.vpYMax.value = this.yMax.toFixed(2);
            }
        } else {
            if (this.vp.lockAspect) {
                let xSpan = this.vp.xMax - this.vp.xMin, ySpan = xSpan/asp, yC = (this.vp.yMax + this.vp.yMin)/2;
                this.xMin = this.vp.xMin; this.xMax = this.vp.xMax; this.yMin = yC - ySpan/2; this.yMax = yC + ySpan/2;
                if (this.id === 0 && ui.vpYMin && document.activeElement !== ui.vpYMin && document.activeElement !== ui.vpYMax) {
                    ui.vpYMin.value = this.yMin.toFixed(2); ui.vpYMax.value = this.yMax.toFixed(2);
                }
            } else {
                this.xMin = this.vp.xMin; this.xMax = this.vp.xMax; this.yMin = this.vp.yMin; this.yMax = this.vp.yMax;
            }
        }

        if (this.needsBgUpdate) {
            this.bgCtx.clearRect(0, 0, w, h);
            const isDark = AppUtils.isDarkMode, axisCol = isDark ? '#495057' : '#ced4da', tickCol = isDark ? '#adb5bd' : '#6c757d', slpCol = isDark ? '#6c757d' : '#adb5bd';

            this.bgCtx.strokeStyle = axisCol; this.bgCtx.lineWidth = 2; this.bgCtx.beginPath();
            let oX = this.sX(0), oY = this.sY(0);
            if (oX >= 0 && oX <= w) { this.bgCtx.moveTo(oX, 0); this.bgCtx.lineTo(oX, h); }
            if (oY >= 0 && oY <= h) { this.bgCtx.moveTo(0, oY); this.bgCtx.lineTo(w, oY); }
            this.bgCtx.stroke();

            this.bgCtx.fillStyle = this.bgCtx.strokeStyle = tickCol; this.bgCtx.font = '12px Arial'; this.bgCtx.lineWidth = 1;
            let tickStep = Math.max(1, Math.pow(10, Math.floor(Math.log10(this.xMax - this.xMin))) / 2);
            
            this.bgCtx.textAlign = 'center'; this.bgCtx.textBaseline = 'top';
            for(let i = Math.ceil(this.xMin/tickStep)*tickStep; i <= this.xMax; i += tickStep) {
                if (Math.abs(i) < 1e-5) continue;
                let sx = this.sX(i), sy = Math.max(0, Math.min(oY, h-20));
                this.bgCtx.beginPath(); this.bgCtx.moveTo(sx, sy-5); this.bgCtx.lineTo(sx, sy+5); this.bgCtx.stroke();
                this.bgCtx.fillText(parseFloat(i.toPrecision(3)), sx, sy+8);
            }
            
            this.bgCtx.textAlign = 'right'; this.bgCtx.textBaseline = 'middle';
            for(let i = Math.ceil(this.yMin/tickStep)*tickStep; i <= this.yMax; i += tickStep) {
                if (Math.abs(i) < 1e-5) continue;
                let sx = Math.max(20, Math.min(oX, w)), sy = this.sY(i);
                this.bgCtx.beginPath(); this.bgCtx.moveTo(sx-5, sy); this.bgCtx.lineTo(sx+5, sy); this.bgCtx.stroke();
                this.bgCtx.fillText(parseFloat(i.toPrecision(3)), sx-8, sy);
            }

            let mStep = (this.xMax - this.xMin) / parseInt(ui.dens.value), tickLen = parseFloat(ui.len.value) * (mStep * (w / (this.xMax - this.xMin))) * 0.8;
            this.bgCtx.strokeStyle = slpCol; this.bgCtx.lineWidth = 1.5;

            for(let x = Math.ceil(this.xMin/mStep)*mStep; x <= this.xMax; x += mStep) {
                for(let y = Math.ceil(this.yMin/mStep)*mStep; y <= this.yMax; y += mStep) {
                    let dy = this.getDeriv(x, y);
                    if (!isNaN(dy)) {
                        let a = Math.atan(dy), dxs = Math.cos(a)*tickLen/2, dys = Math.sin(a)*tickLen/2, sx = this.sX(x), sy = this.sY(y);
                        this.bgCtx.beginPath(); this.bgCtx.moveTo(sx-dxs, sy+dys); this.bgCtx.lineTo(sx+dxs, sy-dys); this.bgCtx.stroke();
                    }
                }
            }
            this.needsBgUpdate = false;
        }

        this.ctx.clearRect(0, 0, w, h); this.ctx.drawImage(this.bgCanvas, 0, 0);

        const txtCol = AppUtils.isDarkMode ? '#f8f9fa' : '#000000';
        for(let i=0; i<4; i++) {
            if(!ui.sols[i].checked) continue;
            let pt = this.points[i], curve = this.rk4(pt.x, pt.y, -1, 10000).reverse().concat(this.rk4(pt.x, pt.y, 1, 10000).slice(1));

            if (curve.length > 0) {
                this.ctx.strokeStyle = colors[i]; this.ctx.lineWidth = 3; this.ctx.beginPath();
                curve.forEach((p, idx) => { let sx = this.sX(p.x), sy = this.sY(p.y); idx===0 ? this.ctx.moveTo(sx, sy) : this.ctx.lineTo(sx, sy); });
                this.ctx.stroke();
            }

            let sx = this.sX(pt.x), sy = this.sY(pt.y);
            this.ctx.fillStyle = colors[i]; this.ctx.beginPath(); this.ctx.arc(sx, sy, 8, 0, Math.PI*2); this.ctx.fill();
            this.ctx.strokeStyle = txtCol; this.ctx.lineWidth = 2; this.ctx.stroke();

            this.ctx.fillStyle = txtCol; this.ctx.font = 'bold 14px Arial'; this.ctx.textAlign = 'left'; this.ctx.textBaseline = 'bottom';
            this.ctx.fillText(`(${Number.isInteger(pt.x)?pt.x:pt.x.toFixed(1)}, ${Number.isInteger(pt.y)?pt.y:pt.y.toFixed(1)})`, sx+12, sy-12);
        }
    }	

    bindEvents() {
        const getP = e => { const r = this.canvas.getBoundingClientRect(), t = e.touches?.[0] || e; return { mx: t.clientX - r.left, my: t.clientY - r.top }; };
        const setVp = () => { if(!this.vp.active) this.vp = { ...this.vp, xMin: this.xMin, xMax: this.xMax, yMin: this.yMin, yMax: this.yMax, active: true }; };

        const onStart = e => {
            const { mx, my } = getP(e); let hit = false;
            for(let i=0; i<4; i++) {
                if(ui.sols[i].checked && Math.sqrt((mx-this.sX(this.points[i].x))**2 + (my-this.sY(this.points[i].y))**2) < (e.touches?30:15)) { 
                    this.draggingPoint = i; hit = true; break; 
                }
            }
            if (!hit) { this.isPanning = true; this.lastPanMx = mx; this.lastPanMy = my; this.canvas.style.cursor = 'grabbing'; }
            if (hit && e.touches && e.cancelable) e.preventDefault(); 
            if (e.touches) { let n = Date.now(); if (n-this.lastTap < 300 && n-this.lastTap > 0) { onDbl(mx, my); if(e.cancelable) e.preventDefault(); } this.lastTap = n; }
        };

        const onMove = e => {
            if(this.draggingPoint !== null || this.isPanning) {
                if (e.cancelable) e.preventDefault(); 
                if (this.animationFrameId) cancelAnimationFrame(this.animationFrameId);
                
                this.animationFrameId = requestAnimationFrame(() => {
                    const { mx, my } = getP(e);
                    if (this.draggingPoint !== null) {
                        let nx = this.mX(mx), ny = this.mY(my);
                        if (Math.abs(nx - Math.round(nx)) < 0.3) nx = Math.round(nx);
                        if (Math.abs(ny - Math.round(ny)) < 0.3) ny = Math.round(ny);
                        this.points[this.draggingPoint] = {x: nx, y: ny};
                    } else if (this.isPanning) {
                        setVp();
                        let dx = (mx - this.lastPanMx)/this.canvas.width*(this.xMax-this.xMin), dy = (my - this.lastPanMy)/this.canvas.height*(this.yMax-this.yMin);
                        this.vp.xMin -= dx; this.vp.xMax -= dx; this.vp.yMin += dy; this.vp.yMax += dy;
                        this.lastPanMx = mx; this.lastPanMy = my; this.needsBgUpdate = true;
                    }
                    this.draw();
                });
            }
        };

        const onEnd = () => { 
            if (this.draggingPoint !== null) this.draggingPoint = null;
            if (this.isPanning) { this.isPanning = false; this.canvas.style.cursor = 'crosshair'; }
            saveLocal(); 
        };

        const onDbl = (mx, my) => {
            for(let i=0; i<4; i++) {
                if(ui.sols[i].checked && Math.sqrt((mx-this.sX(this.points[i].x))**2 + (my-this.sY(this.points[i].y))**2) < 30) {
                    let p = this.points[i], inp = prompt(`Plot ${this.id+1}, Sol ${i+1} (x, y):`, `${Number.isInteger(p.x)?p.x:p.x.toFixed(2)}, ${Number.isInteger(p.y)?p.y:p.y.toFixed(2)}`);
                    if (inp) {
                        let pts = inp.split(',').map(n => parseFloat(n.trim()));
                        if (pts.length >= 2 && !isNaN(pts[0]) && !isNaN(pts[1])) { this.points[i] = {x: pts[0], y: pts[1]}; this.draw(); saveLocal(); }
                        else alert("Invalid input.");
                    } break;
                }
            }
        };

        this.canvas.addEventListener('mousedown', onStart); this.canvas.addEventListener('mousemove', onMove);
        window.addEventListener('mouseup', onEnd); this.canvas.addEventListener('dblclick', e => onDbl(getP(e).mx, getP(e).my));

        this.canvas.addEventListener('wheel', e => {
            e.preventDefault(); const { mx, my } = getP(e), z = e.deltaY > 0 ? 1.1 : (1/1.1); setVp();
            let mX = this.mX(mx), mY = this.mY(my);
            this.vp.xMin = mX - (mX - this.vp.xMin)*z; this.vp.xMax = mX + (this.vp.xMax - mX)*z;
            this.vp.yMin = mY - (mY - this.vp.yMin)*z; this.vp.yMax = mY + (this.vp.yMax - mY)*z;
            this.needsBgUpdate = true; this.draw();
            clearTimeout(this.zoomSaveTimeout); this.zoomSaveTimeout = setTimeout(saveLocal, 300);
        }, { passive: false });

        this.canvas.addEventListener('touchstart', e => {
            if (e.touches.length === 2) {
                e.preventDefault(); this.isPanning = false; this.draggingPoint = null;
                let dx = e.touches[0].clientX - e.touches[1].clientX, dy = e.touches[0].clientY - e.touches[1].clientY;
                this.initialPinchDistance = Math.sqrt(dx*dx + dy*dy);
                let cx = (e.touches[0].clientX + e.touches[1].clientX)/2, cy = (e.touches[0].clientY + e.touches[1].clientY)/2, r = this.canvas.getBoundingClientRect();
                this.initialPinchCenter = { x: this.mX(cx - r.left), y: this.mY(cy - r.top) }; setVp(); this.initVp = {...this.vp};
            } else onStart(e);
        }, { passive: false });

        this.canvas.addEventListener('touchmove', e => {
            if (e.touches.length === 2 && this.initialPinchDistance) {
                e.preventDefault();
                let dx = e.touches[0].clientX - e.touches[1].clientX, dy = e.touches[0].clientY - e.touches[1].clientY;
                let z = this.initialPinchDistance / Math.sqrt(dx*dx + dy*dy); 
                this.vp.xMin = this.initialPinchCenter.x - (this.initialPinchCenter.x - this.initVp.xMin)*z;
                this.vp.xMax = this.initialPinchCenter.x + (this.initVp.xMax - this.initialPinchCenter.x)*z;
                this.vp.yMin = this.initialPinchCenter.y - (this.initialPinchCenter.y - this.initVp.yMin)*z;
                this.vp.yMax = this.initialPinchCenter.y + (this.initVp.yMax - this.initialPinchCenter.y)*z;
                this.needsBgUpdate = true; this.draw();
            } else onMove(e);
        }, { passive: false });

        window.addEventListener('touchend', e => { if (e.touches.length < 2 && this.initialPinchDistance) { this.initialPinchDistance = null; saveLocal(); } onEnd(); });
        window.addEventListener('touchcancel', onEnd);
    }
}

const plots = Array.from({length:4}, (_,i) => new Plot(i, savedPointsData?.[i]));
const triggerRedraw = () => plots.forEach(p => { if(p.wrapper.style.display !== 'none') p.draw(); });

const updateLayout = () => {
    let v = parseInt(ui.layout.value); $('grid-container').className = `grid-${v}`;
    plots.forEach((p, i) => { 
        let show = i < v; p.wrapper.style.display = p.eqContainer.style.display = show ? 'flex' : 'none'; 
        if (show) p.needsBgUpdate = true;
    });
    setTimeout(triggerRedraw, 50);
};

ui.layout.addEventListener('change', () => { updateLayout(); saveLocal(); });
window.addEventListener('resize', () => { plots.forEach(p => p.needsBgUpdate = true); requestAnimationFrame(triggerRedraw); });

const bindSlider = (el, valEl) => ui[el].addEventListener('input', e => { $(valEl).innerText = e.target.value; plots.forEach(p => p.needsBgUpdate = true); triggerRedraw(); saveLocal(); });
bindSlider('dens', 'densityVal'); bindSlider('len', 'lengthVal');

ui.sols.forEach(cb => cb.addEventListener('change', () => { triggerRedraw(); saveLocal(); }));

const updateVpUI = () => {
    if (!ui.vpXMin) return;
    let lock = ui.vpLock.checked;
    ui.vpYMin.disabled = ui.vpYMax.disabled = lock;
    
    // When the top UI limits are modified, it acts as a "Sync All" for all plots
    plots.forEach(p => {
        p.vp = { 
            active: true, 
            xMin: parseFloat(ui.vpXMin.value) || p.vp.xMin, 
            xMax: parseFloat(ui.vpXMax.value) || p.vp.xMax, 
            yMin: parseFloat(ui.vpYMin.value) || p.vp.yMin, 
            yMax: parseFloat(ui.vpYMax.value) || p.vp.yMax, 
            lockAspect: lock 
        };
        p.needsBgUpdate = true;
    });
    triggerRedraw(); saveLocal();
};

if (ui.vpXMin) ['vpXMin','vpXMax','vpYMin','vpYMax','vpLock'].forEach(k => ui[k].addEventListener('change', updateVpUI));

if (ui.resetBtn) ui.resetBtn.addEventListener('click', () => { 
    plots.forEach(p => { p.vp.active = false; p.needsBgUpdate = true; }); 
    triggerRedraw(); saveLocal(); 
});

updateLayout();