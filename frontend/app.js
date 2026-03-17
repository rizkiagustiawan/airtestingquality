// -------------------------------------------------------------
// Web GIS State Management
// -------------------------------------------------------------
let state = {
    dashboardData: [],
    emissionSources: [],
    receptors: [],
    activeModule: 'monitoring',
    chartInstance: null,
    layers: {
        monitoring: null,
        sources: null,
        aermod: null,
        calpuff: null
    }
};

const API_BASE = '';
const DEFAULT_DATA_SOURCE = new URLSearchParams(window.location.search).get('source') || 'synthetic';

let map = null;

function getDashboardDataUrl() {
    return `${API_BASE}/api/dashboard-data?source=${encodeURIComponent(DEFAULT_DATA_SOURCE)}`;
}

// -------------------------------------------------------------
// Initialization & Map Setup
// -------------------------------------------------------------
function initApp() {
    initMap();
    setupEventListeners();

    // Premium loading sequence
    let progress = 0;
    const progressEl = document.getElementById('loader-progress');
    const interval = setInterval(() => {
        progress += Math.random() * 20 + 5;
        if (progress > 100) progress = 100;
        progressEl.style.width = `${progress}%`;

        if (progress === 100) {
            clearInterval(interval);
            setTimeout(() => {
                document.getElementById('loading-overlay').classList.add('hidden');
                fetchInitialData().then(() => {
                    startLivePolling();
                });
            }, 600);
        }
    }, 150);
}

function startLivePolling() {
    // Refresh data from backend to avoid synthetic UI-only fluctuations.
    setInterval(async () => {
        try {
            const dashRes = await fetch(getDashboardDataUrl());
            const dashData = await dashRes.json();
            if (dashData.status !== 'success') return;
            state.dashboardData = dashData.data;

            if (state.activeModule === 'monitoring') {
                renderMonitoringList();
                renderMonitoringMarkers();
                const activeTitle = document.getElementById('ispu-station-name').textContent;
                const openSt = state.dashboardData.find(s => s.location === activeTitle);
                if (openSt) showMonitoringDetails(openSt);
            }
        } catch (err) {
            console.error("Live polling failed", err);
        }
    }, 30000);
}

function initMap() {
    // Center to PT AMMAN Mineral NTB location
    map = L.map('map').setView([-8.82, 116.85], 11);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    // Initialize layer groups
    state.layers.monitoring = L.layerGroup().addTo(map);
    state.layers.sources = L.layerGroup().addTo(map);
    state.layers.aermod = L.layerGroup(); // Not added initially
    state.layers.calpuff = L.layerGroup(); // Not added initially

    // Add Layer Control
    L.control.layers(
        { "OSM Light": L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png') },
        {
            "AQMS Stations": state.layers.monitoring,
            "Emission Sources": state.layers.sources,
            "AERMOD Plume": state.layers.aermod,
            "CALPUFF Plume": state.layers.calpuff
        },
        { position: 'topright' }
    ).addTo(map);

    // Time updater
    setInterval(() => {
        document.getElementById('current-time').textContent = new Date().toLocaleString('en-US', {
            weekday: 'short', month: 'short', day: 'numeric',
            hour: '2-digit', minute: '2-digit', second: '2-digit'
        });
    }, 1000);
}

// -------------------------------------------------------------
// Event Listeners Setup
// -------------------------------------------------------------
function setupEventListeners() {
    // Module Tabs
    document.querySelectorAll('.module-tab').forEach(tab => {
        tab.addEventListener('click', (e) => {
            const moduleName = e.currentTarget.getAttribute('data-module');
            switchModule(moduleName);
        });
    });

    // Range Inputs text sync
    document.getElementById('aermod-wind-dir').addEventListener('input', (e) => {
        document.getElementById('aermod-wind-dir-val').textContent = `${e.target.value} deg`;
    });
    document.getElementById('aermod-wind-speed').addEventListener('input', (e) => {
        document.getElementById('aermod-wind-speed-val').textContent = `${e.target.value} m/s`;
    });
    document.getElementById('calpuff-duration').addEventListener('input', (e) => {
        document.getElementById('calpuff-duration-val').textContent = `${e.target.value} hrs`;
    });

    // OpenAir Type Toggle (show/hide pollutant)
    document.getElementById('openair-type').addEventListener('change', (e) => {
        const type = e.target.value;
        const pGroup = document.getElementById('openair-pollutant-group');
        pGroup.style.display = (type === 'windrose') ? 'none' : 'block';
    });

    // Run Buttons
    document.getElementById('openair-run').addEventListener('click', runOpenAir);
    document.getElementById('aermod-run').addEventListener('click', runAERMOD);
    document.getElementById('calpuff-run').addEventListener('click', runCALPUFF);

    // Panel Closers
    document.getElementById('chart-close').addEventListener('click', () => {
        document.getElementById('chart-panel').style.display = 'none';
    });
}

function switchModule(moduleName) {
    state.activeModule = moduleName;

    // Update tabs UI
    document.querySelectorAll('.module-tab').forEach(tab => tab.classList.remove('active'));
    document.getElementById(`tab-${moduleName}`).classList.add('active');

    // Update panels UI
    document.querySelectorAll('.module-panel').forEach(panel => panel.classList.remove('active'));
    document.getElementById(`panel-${moduleName}`).classList.add('active');

    // Layer management based on module
    if (moduleName === 'monitoring') {
        if (!map.hasLayer(state.layers.monitoring)) map.addLayer(state.layers.monitoring);
        if (map.hasLayer(state.layers.aermod)) map.removeLayer(state.layers.aermod);
        if (map.hasLayer(state.layers.calpuff)) map.removeLayer(state.layers.calpuff);
        document.getElementById('map-legend').style.display = 'none';
    }
    else if (moduleName === 'aermod') {
        if (!map.hasLayer(state.layers.aermod)) map.addLayer(state.layers.aermod);
        if (map.hasLayer(state.layers.calpuff)) map.removeLayer(state.layers.calpuff);
        document.getElementById('ispu-panel').style.display = 'none';
        document.getElementById('chart-panel').style.display = 'none';
    }
    else if (moduleName === 'calpuff') {
        if (!map.hasLayer(state.layers.calpuff)) map.addLayer(state.layers.calpuff);
        if (map.hasLayer(state.layers.aermod)) map.removeLayer(state.layers.aermod);
        document.getElementById('ispu-panel').style.display = 'none';
        document.getElementById('chart-panel').style.display = 'none';
    }
    else if (moduleName === 'openair') {
        document.getElementById('ispu-panel').style.display = 'none';
        document.getElementById('map-legend').style.display = 'none';
    }
}

// -------------------------------------------------------------
// Data Fetching
// -------------------------------------------------------------
async function fetchInitialData() {
    try {
        // Fetch Dashboard Data
        const dashRes = await fetch(getDashboardDataUrl());
        const dashData = await dashRes.json();
        if (dashData.status === 'success') {
            state.dashboardData = dashData.data;
            renderMonitoringList();
            renderMonitoringMarkers();
        }

        // Fetch Emission Sources
        const srcRes = await fetch(`${API_BASE}/api/emission-sources`);
        const srcData = await srcRes.json();
        state.emissionSources = srcData.sources;
        state.receptors = srcData.receptors;

        populateAERMODSources();
        renderSourceMarkers();

    } catch (err) {
        console.error("Failed to fetch initial data", err);
    }
}

function populateAERMODSources() {
    const select = document.getElementById('aermod-source');
    select.innerHTML = '';
    state.emissionSources.forEach(src => {
        const opt = document.createElement('option');
        opt.value = src.id;
        opt.textContent = `${src.icon} ${src.name}`;
        select.appendChild(opt);
    });
}

// -------------------------------------------------------------
// Monitoring Module
// -------------------------------------------------------------
function renderMonitoringList() {
    const listEl = document.getElementById('station-list');
    listEl.innerHTML = '';

    state.dashboardData.forEach(st => {
        const ispuObj = st.ispu || { value: 0, color: 'gray' };

        const li = document.createElement('li');
        li.className = 'station-item';
        li.innerHTML = `
            <div class="station-item-info">
                <strong>${st.location || 'Unknown Location'}</strong>
                <span>${st.city}</span>
            </div>
            <div class="station-ispu-badge" style="background-color: ${ispuObj.color}">
                ISPU ${ispuObj.value ?? '--'}
            </div>
        `;
        li.onclick = () => showMonitoringDetails(st);
        listEl.appendChild(li);
    });
}

function renderMonitoringMarkers() {
    state.layers.monitoring.clearLayers();

    state.dashboardData.forEach(st => {
        if (!st.latitude || !st.longitude) return;

        const ispuObj = st.ispu || { value: 0, color: 'gray' };
        const marker = L.circleMarker([st.latitude, st.longitude], {
            radius: 8,
            fillColor: ispuObj.color,
            color: '#fff',
            weight: 2,
            opacity: 1,
            fillOpacity: 0.8
        });

        marker.on('click', () => {
            if (state.activeModule !== 'monitoring') switchModule('monitoring');
            showMonitoringDetails(st);
            map.flyTo([st.latitude, st.longitude], 13);
        });

        state.layers.monitoring.addLayer(marker);
    });
}

function showMonitoringDetails(st) {
    document.getElementById('ispu-panel').style.display = 'block';
    document.getElementById('ispu-station-name').textContent = st.location;

    const ispu = st.ispu || {};
    const circle = document.getElementById('ispu-circle');

    document.getElementById('ispu-val').textContent = ispu.value ?? '--';
    document.getElementById('ispu-cat').textContent = ispu.category || 'N/A';
    document.getElementById('ispu-critical').textContent = ispu.critical_parameter || 'None';
    document.getElementById('ispu-time').textContent = `Updated: ${new Date(st.last_updated).toLocaleString()}`;

    circle.style.borderColor = ispu.color || 'gray';
    circle.style.boxShadow = `0 0 15px ${ispu.color || 'gray'}`;
}

// -------------------------------------------------------------
// Source Markers (Factory Icons)
// -------------------------------------------------------------
function renderSourceMarkers() {
    state.layers.sources.clearLayers();

    state.emissionSources.forEach(src => {
        // Create custom div icon for emoji
        const icon = L.divIcon({
            html: `<div style="font-size: 24px; text-shadow: 0 2px 4px rgba(0,0,0,0.5);">${src.icon}</div>`,
            className: 'custom-src-icon',
            iconSize: [30, 30],
            iconAnchor: [15, 15]
        });

        const marker = L.marker([src.lat, src.lon], { icon: icon });
        marker.bindPopup(`
            <div style="text-align: center; min-width: 150px;">
                <h4 style="margin:0; padding-bottom:5px; border-bottom:1px solid #444">${src.icon} ${src.name}</h4>
                <p style="margin:5px 0;"><strong>Type:</strong> ${src.type}</p>
                <p style="margin:5px 0;"><strong>PM10 Rate:</strong> ${src.emissions.pm10} g/s</p>
            </div>
        `);
        state.layers.sources.addLayer(marker);
    });
}

// -------------------------------------------------------------
// OpenAir Module
// -------------------------------------------------------------
async function runOpenAir() {
    const btn = document.getElementById('openair-run');
    const type = document.getElementById('openair-type').value;
    const pollutant = document.getElementById('openair-pollutant').value;

    btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Processing...';
    btn.disabled = true;

    try {
        let endpoint = `${API_BASE}/api/openair/${type}`;
        if (type !== 'windrose') endpoint += `?pollutant=${pollutant}`;

        const res = await fetch(endpoint);
        const data = await res.json();

        showChartPanel((type === 'windrose') ? 'Wind Rose Frequency' :
            (type === 'polarplot') ? `Polar Plot (${pollutant.toUpperCase()})` :
                `Time Series (${pollutant.toUpperCase()})`);

        if (type === 'windrose' || type === 'polarplot') {
            document.getElementById('chartCanvas').style.display = 'none';
            document.getElementById('analysisCanvas').style.display = 'block';
            drawWindRose(data); // Using same simple renderer for both visually
        } else {
            document.getElementById('analysisCanvas').style.display = 'none';
            document.getElementById('chartCanvas').style.display = 'block';
            renderTimeSeries(data, pollutant);
        }
    } catch (err) {
        console.error("OpenAir Error", err);
        showToast("Error", "Failed to generate OpenAir analysis.", "error");
    } finally {
        btn.innerHTML = '<i class="fas fa-play"></i> Run Analysis';
        btn.disabled = false;
    }
}

function showChartPanel(title) {
    const panel = document.getElementById('chart-panel');
    panel.style.display = 'block';
    document.getElementById('chart-title').textContent = title;
}

// Simple Canvas Wind Rose Renderer
function drawWindRose(data) {
    const canvas = document.getElementById('analysisCanvas');
    const ctx = canvas.getContext('2d');
    const cx = canvas.width / 2;
    const cy = canvas.height / 2;
    const radius = Math.min(cx, cy) - 40;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw grid rings
    ctx.strokeStyle = 'rgba(255,255,255,0.1)';
    ctx.lineWidth = 1;
    for (let i = 1; i <= 4; i++) {
        ctx.beginPath();
        ctx.arc(cx, cy, radius * (i / 4), 0, 2 * Math.PI);
        ctx.stroke();
    }

    // Draw axes
    ctx.textBaseline = 'middle';
    ctx.textAlign = 'center';
    ctx.fillStyle = '#9ca3af';
    ctx.font = '12px Inter';

    const labels = ['N', 'E', 'S', 'W'];
    for (let i = 0; i < 4; i++) {
        const angle = i * Math.PI / 2 - Math.PI / 2;
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(cx + Math.cos(angle) * radius, cy + Math.sin(angle) * radius);
        ctx.stroke();

        ctx.fillText(labels[i], cx + Math.cos(angle) * (radius + 15), cy + Math.sin(angle) * (radius + 15));
    }

    // Determine max length for scaling
    let maxTotal = 0.1;
    if (data.frequencies) {
        data.frequencies.forEach(speeds => {
            const sum = speeds.reduce((a, b) => a + b, 0);
            if (sum > maxTotal) maxTotal = sum;
        });
    }

    // Draw petals
    if (data.frequencies) {
        const nSectors = data.sectors.length;
        const angleStep = (2 * Math.PI) / nSectors;

        for (let i = 0; i < nSectors; i++) {
            const angleCenter = (i * angleStep) - Math.PI / 2;
            const sa = angleCenter - angleStep / 2.2;
            const ea = angleCenter + angleStep / 2.2;

            let currentR = 0;
            data.frequencies[i].forEach((val, j) => {
                if (val > 0) {
                    const r = (val / maxTotal) * radius;

                    ctx.beginPath();
                    ctx.moveTo(cx, cy);
                    ctx.arc(cx, cy, currentR + r, sa, ea);
                    ctx.arc(cx, cy, currentR, ea, sa, true);
                    ctx.closePath();

                    ctx.fillStyle = data.speed_bins[j].color;
                    ctx.fill();
                    ctx.strokeStyle = 'rgba(0,0,0,0.5)';
                    ctx.lineWidth = 0.5;
                    ctx.stroke();

                    currentR += r;
                }
            });
        }
    } else if (data.points) {
        // Simple polar plot scatter visualization
        const maxConc = Math.max(...data.points.map(p => p.concentration));
        const maxSpd = Math.max(...data.points.map(p => p.wind_speed));

        data.points.forEach(pt => {
            const angle = (pt.wind_dir - 90) * Math.PI / 180;
            const r = (pt.wind_speed / maxSpd) * radius;
            const x = cx + Math.cos(angle) * r;
            const y = cy + Math.sin(angle) * r;

            ctx.beginPath();
            ctx.arc(x, y, 4, 0, 2 * Math.PI);
            ctx.fillStyle = `hsla(${120 - (pt.concentration / maxConc) * 120}, 80%, 50%, 0.6)`;
            ctx.fill();
        });
    }
}

function renderTimeSeries(data, pollutant) {
    const ctx = document.getElementById('chartCanvas').getContext('2d');

    if (state.chartInstance) {
        state.chartInstance.destroy();
    }

    const series = data.series[pollutant];
    const labels = series.map(s => new Date(s.timestamp).getHours() + ':00');
    const values = series.map(s => s.value);

    Chart.defaults.color = '#9ca3af';

    state.chartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: `${pollutant.toUpperCase()} (${data.units[pollutant]})`,
                data: values,
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointRadius: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: { grid: { display: false } },
                y: { grid: { color: 'rgba(255,255,255,0.05)' } }
            }
        }
    });
}

// -------------------------------------------------------------
// AERMOD & CALPUFF (Map Overlays)
// -------------------------------------------------------------
async function runAERMOD() {
    const btn = document.getElementById('aermod-run');
    const srcId = document.getElementById('aermod-source').value;
    const pol = document.getElementById('aermod-pollutant').value;
    const wDir = document.getElementById('aermod-wind-dir').value;
    const wSpd = document.getElementById('aermod-wind-speed').value;
    const stab = document.getElementById('aermod-stability').value;

    btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Running...';
    btn.disabled = true;

    try {
        const res = await fetch(`${API_BASE}/api/aermod/dispersion?source_id=${srcId}&pollutant=${pol}&wind_dir=${wDir}&wind_speed=${wSpd}&stability=${stab}`);
        const geojson = await res.json();

        state.layers.aermod.clearLayers();

        L.geoJSON(geojson, {
            style: function (feature) {
                return {
                    color: feature.properties.color,
                    weight: 1,
                    fillColor: feature.properties.color,
                    fillOpacity: feature.properties.opacity
                };
            },
            onEachFeature: function (feature, layer) {
                layer.bindPopup(`Concentration: ${feature.properties.concentration} µg/m³`);
            }
        }).addTo(state.layers.aermod);

        const src = state.emissionSources.find(s => s.id === srcId);
        if (src) {
            map.flyTo([src.lat, src.lon], 12, { animate: true, duration: 2.0, easeLinearity: 0.25 });
        }

        renderLegend('AERMOD Dispersion', geojson.bands);
        showToast("Success", "AERMOD Dispersion model run complete.", "success");
    } catch (err) {
        console.error("AERMOD Error", err);
        showToast("Error", "Failed to run AERMOD Dispersion model.", "error");
    } finally {
        btn.innerHTML = '<i class="fas fa-play"></i> Run Dispersion';
        btn.disabled = false;
    }
}

async function runCALPUFF() {
    const btn = document.getElementById('calpuff-run');
    const dur = document.getElementById('calpuff-duration').value;
    const pol = document.getElementById('calpuff-pollutant').value;

    btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Transporting...';
    btn.disabled = true;

    try {
        const res = await fetch(`${API_BASE}/api/calpuff/plume?duration_hours=${dur}&pollutant=${pol}`);
        const geojson = await res.json();

        state.layers.calpuff.clearLayers();

        L.geoJSON(geojson, {
            style: function (feature) {
                return {
                    color: 'transparent',
                    weight: 0,
                    fillColor: feature.properties.color,
                    fillOpacity: feature.properties.opacity
                };
            },
            onEachFeature: function (feature, layer) {
                layer.bindPopup(`Conc: ${feature.properties.concentration} µg/m³<br>Source: ${feature.properties.source}`);
            }
        }).addTo(state.layers.calpuff);

        map.flyTo([-8.82, 116.85], 11, { animate: true, duration: 2.5, easeLinearity: 0.25 });

        renderLegend('CALPUFF Transport', geojson.bands);
        showToast("Success", "CALPUFF Transport model run complete.", "success");
    } catch (err) {
        console.error("CALPUFF Error", err);
        showToast("Error", "Failed to run CALPUFF Transport model.", "error");
    } finally {
        btn.innerHTML = '<i class="fas fa-play"></i> Run Transport';
        btn.disabled = false;
    }
}

function renderLegend(title, bands) {
    const lgd = document.getElementById('map-legend');
    lgd.style.display = 'block';
    document.getElementById('legend-title').textContent = title;

    const content = document.getElementById('legend-content');
    content.innerHTML = '';

    bands.forEach(b => {
        content.innerHTML += `
            <div class="legend-item">
                <div class="legend-color" style="background-color: ${b.color}; opacity: ${b.opacity || 0.8}"></div>
                <span>${b.label}</span>
            </div>
        `;
    });
}

// -------------------------------------------------------------
// UI Utilities (Toast Notifications)
// -------------------------------------------------------------
function showToast(title, message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    const icon = type === 'success' ? 'fa-check-circle' :
        type === 'error' ? 'fa-exclamation-circle' : 'fa-info-circle';

    toast.innerHTML = `
        <i class="fas ${icon} toast-icon"></i>
        <div class="toast-content">
            <div class="toast-title">${title}</div>
            <div class="toast-msg">${message}</div>
        </div>
        <button class="toast-close"><i class="fas fa-times"></i></button>
    `;

    container.appendChild(toast);

    // Fade in
    requestAnimationFrame(() => toast.classList.add('show'));

    // Setup close
    const closeBtn = toast.querySelector('.toast-close');
    closeBtn.onclick = () => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    };

    // Auto close
    setTimeout(() => {
        if (document.body.contains(toast)) {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }
    }, 4000);
}

// Run it!
document.addEventListener('DOMContentLoaded', initApp);

