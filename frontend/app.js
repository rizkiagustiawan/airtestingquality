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
    document.getElementById('forecast-run').addEventListener('click', runForecast);
    document.getElementById('report-summary-btn').addEventListener('click', downloadSummaryReport);
    document.getElementById('report-hist-btn').addEventListener('click', downloadHistoricalReport);

    // NTB Monitoring
    document.getElementById('ntb-refresh').addEventListener('click', loadNTBData);
    document.getElementById('ntb-heatmap-btn').addEventListener('click', showNTBHeatmap);
    document.getElementById('ntb-island-filter').addEventListener('change', filterNTBStations);

    // ML Analysis
    document.getElementById('ml-tool-select').addEventListener('change', switchMLTool);
    document.getElementById('ml-forecast-run').addEventListener('click', runMLForecast);
    document.getElementById('ml-ispu-run').addEventListener('click', runMLISPU);
    document.getElementById('ml-health-run').addEventListener('click', runMLHealth);
    document.getElementById('ml-source-run').addEventListener('click', runMLSource);

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
    else if (moduleName === 'forecast') {
        document.getElementById('ispu-panel').style.display = 'none';
        document.getElementById('map-legend').style.display = 'none';
    }
    else if (moduleName === 'reports') {
        document.getElementById('ispu-panel').style.display = 'none';
        document.getElementById('map-legend').style.display = 'none';
        populateReportStations();
    }
    else if (moduleName === 'ntb') {
        document.getElementById('ispu-panel').style.display = 'none';
        document.getElementById('map-legend').style.display = 'none';
        loadNTBData();
    }
    else if (moduleName === 'ml') {
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

async function runForecast() {
    const btn = document.getElementById('forecast-run');
    const horizon = document.getElementById('forecast-horizon').value;

    btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Calculating...';
    btn.disabled = true;

    try {
        const res = await fetch(`${API_BASE}/api/forecast?hours=${horizon}`);
        const data = await res.json();

        showChartPanel(`Air Quality Forecast (${horizon} Hours)`);
        document.getElementById('analysisCanvas').style.display = 'none';
        document.getElementById('chartCanvas').style.display = 'block';

        renderForecastChart(data);

        // Update summary
        const peak = data.predictions.reduce((prev, current) => (prev.ispu.value > current.ispu.value) ? prev : current);
        document.getElementById('forecast-summary').style.display = 'block';
        document.getElementById('peak-ispu-val').textContent = peak.ispu.value;
        document.getElementById('peak-ispu-param').textContent = peak.ispu.critical_parameter.toUpperCase();

        showToast("Success", "Forecast generated based on current trends.", "success");
    } catch (err) {
        console.error("Forecast Error", err);
        showToast("Error", "Failed to generate air quality forecast.", "error");
    } finally {
        btn.innerHTML = '<i class="fas fa-bolt"></i> Generate Forecast';
        btn.disabled = false;
    }
}

function renderForecastChart(data) {
    const ctx = document.getElementById('chartCanvas').getContext('2d');

    if (state.chartInstance) {
        state.chartInstance.destroy();
    }

    const labels = data.predictions.map(p => {
        const date = new Date(p.timestamp);
        return date.getHours() + ':00';
    });
    
    const ispuValues = data.predictions.map(p => p.ispu.value);

    Chart.defaults.color = '#9ca3af';

    state.chartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Predicted ISPU Index',
                data: ispuValues,
                borderColor: '#10b981',
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                borderWidth: 3,
                fill: true,
                tension: 0.4,
                pointRadius: 2,
                pointBackgroundColor: '#10b981'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: true, position: 'top' },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const p = data.predictions[context.dataIndex];
                            return [
                                `ISPU: ${p.ispu.value} (${p.ispu.category})`,
                                `Driver: ${p.ispu.critical_parameter.toUpperCase()}`,
                                `Wind: ${p.met.wind_speed} m/s @ ${p.met.wind_direction}°`
                            ];
                        }
                    }
                }
            },
            scales: {
                x: { grid: { display: false } },
                y: { 
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    suggestedMin: 0,
                    suggestedMax: 100
                }
            }
        }
    });
}

function populateReportStations() {
    const select = document.getElementById('report-hist-station');
    if (!select) return;
    select.innerHTML = '';
    state.dashboardData.forEach(st => {
        const opt = document.createElement('option');
        opt.value = st.id;
        opt.textContent = st.location;
        select.appendChild(opt);
    });
}

async function downloadSummaryReport() {
    const format = document.getElementById('report-summary-format').value;
    const url = `${API_BASE}/api/reports/summary?format=${format}&source=${encodeURIComponent(DEFAULT_DATA_SOURCE)}`;
    window.open(url, '_blank');
    showToast("Download Started", `Preparing ${format.toUpperCase()} summary...`, "success");
}

async function downloadHistoricalReport() {
    const stationId = document.getElementById('report-hist-station').value;
    const pollutant = document.getElementById('report-hist-pollutant').value;
    if (!stationId) {
        showToast("Error", "Please select a station first.", "error");
        return;
    }
    const url = `${API_BASE}/api/reports/historical?station_id=${stationId}&pollutant=${pollutant}`;
    window.open(url, '_blank');
    showToast("Download Started", "Preparing historical trend CSV...", "success");
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
// NTB Regional Monitoring
// -------------------------------------------------------------
let ntbData = { stations: [], summary: null, alerts: [] };

async function loadNTBData() {
    try {
        showToast('Loading', 'Fetching NTB station data...', 'info');

        // Load stations
        const stationsRes = await fetch(`${API_BASE}/api/ntb/stations`);
        const stationsData = await stationsRes.json();

        // Load regional summary
        const summaryRes = await fetch(`${API_BASE}/api/ntb/regional-summary?source=${DEFAULT_DATA_SOURCE}`);
        const summaryData = await summaryRes.json();

        // Load alerts
        const alertsRes = await fetch(`${API_BASE}/api/ntb/alerts?source=${DEFAULT_DATA_SOURCE}`);
        const alertsData = await alertsRes.json();

        ntbData.stations = stationsData.stations || [];
        ntbData.summary = summaryData;
        ntbData.alerts = alertsData.alerts || [];

        renderNTBStations();
        renderNTBSummary();
        renderNTBAlerts();

        showToast('Success', `Loaded ${ntbData.stations.length} NTB stations`, 'success');
    } catch (err) {
        console.error('NTB data load failed:', err);
        showToast('Error', 'Failed to load NTB data', 'error');
    }
}

function renderNTBStations() {
    const list = document.getElementById('ntb-station-list');
    const filter = document.getElementById('ntb-island-filter').value;

    const filtered = filter === 'all'
        ? ntbData.stations
        : ntbData.stations.filter(s => s.island === filter);

    list.innerHTML = filtered.map(s => {
        const ispuVal = getStationISPU(s.id);
        const ispuColor = getISPUColor(ispuVal);
        return `
            <li class="ntb-station-item ${s.type}">
                <div>
                    <div class="station-name">${s.name}</div>
                    <div class="station-city">${s.city} · ${s.island}</div>
                </div>
                <div class="station-ispu" style="color:${ispuColor}">${ispuVal || '--'}</div>
            </li>
        `;
    }).join('');
}

function getStationISPU(stationId) {
    if (!ntbData.summary || !ntbData.summary.stations) return null;
    const station = ntbData.summary.stations.find(s => s.station_id === stationId);
    return station ? station.ispu?.value : null;
}

function getISPUColor(ispu) {
    if (!ispu) return '#94a3b8';
    if (ispu <= 50) return '#10b981';
    if (ispu <= 100) return '#3b82f6';
    if (ispu <= 200) return '#f59e0b';
    if (ispu <= 300) return '#ef4444';
    return '#000000';
}

function renderNTBSummary() {
    if (!ntbData.summary) return;

    const summaryDiv = document.getElementById('ntb-summary');
    summaryDiv.style.display = 'block';

    const ntb = ntbData.summary.ntb_summary || {};
    const lombok = ntbData.summary.islands?.lombok || {};
    const sumbawa = ntbData.summary.islands?.sumbawa || {};

    document.getElementById('ntb-ispu-avg').textContent = ntb.mean_ispu || '--';
    document.getElementById('ntb-lombok-ispu').textContent = lombok.mean_ispu || '--';
    document.getElementById('ntb-sumbawa-ispu').textContent = sumbawa.mean_ispu || '--';
}

function renderNTBAlerts() {
    const alertsDiv = document.getElementById('ntb-alerts');
    const contentDiv = document.getElementById('ntb-alerts-content');

    if (!ntbData.alerts || ntbData.alerts.length === 0) {
        alertsDiv.style.display = 'none';
        return;
    }

    alertsDiv.style.display = 'block';
    contentDiv.innerHTML = ntbData.alerts.slice(0, 5).map(a => `
        <p style="font-size:0.8rem;margin:4px 0">
            <strong>${a.station_name}</strong>: ${a.pollutant}=${a.value} (${a.severity})
        </p>
    `).join('');
}

function filterNTBStations() {
    renderNTBStations();
}

async function showNTBHeatmap() {
    const pollutant = document.getElementById('ntb-pollutant').value;
    try {
        showToast('Loading', 'Generating NTB heatmap...', 'info');

        const res = await fetch(`${API_BASE}/api/ntb/heatmap?pollutant=${pollutant}&source=${DEFAULT_DATA_SOURCE}&resolution=0.1`);
        const data = await res.json();

        // Clear existing heatmap layers
        if (state.layers.ntbHeatmap) {
            map.removeLayer(state.layers.ntbHeatmap);
        }
        state.layers.ntbHeatmap = L.layerGroup().addTo(map);

        // Add heatmap grid points
        const grid = data.grid?.grid || [];
        grid.forEach(point => {
            if (point.value > 0) {
                const color = getHeatmapColor(point.value, pollutant);
                L.circleMarker([point.lat, point.lon], {
                    radius: 4,
                    fillColor: color,
                    fillOpacity: 0.6,
                    stroke: false
                }).addTo(state.layers.ntbHeatmap);
            }
        });

        // Add station markers
        data.stations?.forEach(s => {
            L.marker([s.lat, s.lon])
                .bindPopup(`<b>${s.name || s.id}</b><br>${pollutant}: ${s.value} ug/m3`)
                .addTo(state.layers.ntbHeatmap);
        });

        // Show legend
        showHeatmapLegend(pollutant, data.regional_stats);

        showToast('Success', `Heatmap generated: ${grid.length} grid points`, 'success');
    } catch (err) {
        console.error('Heatmap failed:', err);
        showToast('Error', 'Failed to generate heatmap', 'error');
    }
}

function getHeatmapColor(value, pollutant) {
    const limits = { pm10: [45, 75, 150], pm25: [15, 55, 150], so2: [40, 75, 150], no2: [25, 65, 200], co: [4000, 10000, 30000] };
    const [who, pp22, critical] = limits[pollutant] || [45, 75, 150];

    if (value < who) return '#10b981';
    if (value < pp22) return '#f59e0b';
    if (value < critical) return '#ef4444';
    return '#7c2d12';
}

function showHeatmapLegend(pollutant, stats) {
    const legend = document.getElementById('map-legend');
    const title = document.getElementById('legend-title');
    const content = document.getElementById('legend-content');

    legend.style.display = 'block';
    title.textContent = `${pollutant.toUpperCase()} Heatmap`;

    content.innerHTML = `
        <div class="heatmap-legend">
            <div class="legend-item"><div class="legend-color" style="background:#10b981"></div> Below WHO</div>
            <div class="legend-item"><div class="legend-color" style="background:#f59e0b"></div> WHO - PP22</div>
            <div class="legend-item"><div class="legend-color" style="background:#ef4444"></div> PP22 - Critical</div>
            <div class="legend-item"><div class="legend-color" style="background:#7c2d12"></div> Above Critical</div>
        </div>
        <div style="margin-top:8px;font-size:0.75rem;color:var(--text-muted)">
            Station mean: ${stats?.station_mean || '--'} ug/m3<br>
            Max: ${stats?.station_max || '--'} ug/m3
        </div>
    `;
}

// -------------------------------------------------------------
// ML-Powered Analysis
// -------------------------------------------------------------
function switchMLTool() {
    const tool = document.getElementById('ml-tool-select').value;
    document.getElementById('ml-forecast-controls').style.display = tool === 'forecast-v2' ? 'block' : 'none';
    document.getElementById('ml-ispu-controls').style.display = tool === 'ispu-classify' ? 'block' : 'none';
    document.getElementById('ml-health-controls').style.display = tool === 'health-impact' ? 'block' : 'none';
    document.getElementById('ml-source-controls').style.display = tool === 'source-apportion' ? 'block' : 'none';
    document.getElementById('ml-results').style.display = 'none';
}

async function runMLForecast() {
    const hours = document.getElementById('ml-forecast-horizon').value;
    try {
        showToast('Forecasting', `Running v2 forecast for ${hours}h...`, 'info');

        const res = await fetch(`${API_BASE}/api/forecast/v2?hours=${hours}`);
        const data = await res.json();

        const resultsDiv = document.getElementById('ml-results');
        resultsDiv.style.display = 'block';

        const peak = data.predictions?.reduce((max, p) => p.ispu?.value > max.ispu?.value ? p : max, data.predictions[0]);
        const summary = data.summary || {};

        document.getElementById('ml-results-content').innerHTML = `
            <div class="ml-result-card">
                <h5>Forecast v2 Results</h5>
                <div class="result-value" style="color:${getISPUColor(peak?.ispu?.value)}">${peak?.ispu?.value || '--'}</div>
                <div class="result-label">Peak ISPU (${peak?.ispu?.category || 'N/A'})</div>
                <div style="font-size:0.75rem;color:var(--text-muted);margin-top:8px">
                    Method: ${data.method || 'N/A'}<br>
                    Data: ${data.data_source || 'N/A'}<br>
                    Smoothing: Kalman + RoC clamp
                </div>
            </div>
            <div class="ml-result-card">
                <h5>PM10 Summary</h5>
                <div style="font-size:0.85rem">
                    Mean: ${summary.pm10?.mean || '--'} ug/m3<br>
                    Max: ${summary.pm10?.max || '--'} ug/m3<br>
                    Max jump: ${summary.pm10?.max_hourly_change || '--'} ug/m3/hr
                </div>
            </div>
        `;

        showToast('Success', 'Forecast v2 completed', 'success');
    } catch (err) {
        console.error('ML Forecast failed:', err);
        showToast('Error', 'Forecast failed', 'error');
    }
}

async function runMLISPU() {
    const pm10 = document.getElementById('ml-ispu-pm10').value;
    const pm25 = document.getElementById('ml-ispu-pm25').value;
    const so2 = document.getElementById('ml-ispu-so2').value;
    const no2 = document.getElementById('ml-ispu-no2').value;
    const co = document.getElementById('ml-ispu-co').value;

    try {
        showToast('Classifying', 'Running ISPU ML classifier...', 'info');

        const res = await fetch(`${API_BASE}/api/ispu/classify?pm10=${pm10}&pm25=${pm25}&so2=${so2}&no2=${no2}&co=${co}`);
        const data = await res.json();

        const resultsDiv = document.getElementById('ml-results');
        resultsDiv.style.display = 'block';

        const bp = data.ispu_breakpoint || {};
        const ens = data.ml_ensemble || {};

        document.getElementById('ml-results-content').innerHTML = `
            <div class="ml-result-card">
                <h5>ISPU Classification</h5>
                <div class="result-value" style="color:${getISPUColor(bp.value)}">${bp.value || '--'}</div>
                <div class="result-label">${bp.category || 'N/A'} (Breakpoint method)</div>
            </div>
            <div class="ml-result-card">
                <h5>ML Ensemble Result</h5>
                <div style="font-size:0.85rem">
                    <strong>${data.ml_category || 'N/A'}</strong> (${(data.ml_confidence * 100).toFixed(1)}% confidence)<br>
                    SVM: ${ens.svm || '--'}<br>
                    RF: ${ens.random_forest || '--'}<br>
                    XGBoost: ${ens.xgboost || '--'}
                </div>
                <div style="font-size:0.75rem;color:var(--text-muted);margin-top:4px">
                    Data: ${data.ml_data_source || 'N/A'} (${data.ml_n_training_samples || 0} samples)
                </div>
            </div>
        `;

        showToast('Success', `Classified as ${data.ml_category}`, 'success');
    } catch (err) {
        console.error('ML ISPU failed:', err);
        showToast('Error', 'Classification failed', 'error');
    }
}

async function runMLHealth() {
    try {
        showToast('Assessing', 'Running health impact assessment...', 'info');

        const res = await fetch(`${API_BASE}/api/health-impact?source=${DEFAULT_DATA_SOURCE}`);
        const data = await res.json();

        const resultsDiv = document.getElementById('ml-results');
        resultsDiv.style.display = 'block';

        const pm25 = data.pollutant_impacts?.pm25 || {};
        const maxAP = Math.max(...Object.values(pm25.attributable_proportions || {}).map(v => v.ap_pct));

        document.getElementById('ml-results-content').innerHTML = `
            <div class="ml-result-card">
                <h5>Health Impact Assessment</h5>
                <div class="result-value">${data.risk_level || 'N/A'}</div>
                <div class="result-label">Risk Level (Score: ${data.overall_risk_score || 0})</div>
            </div>
            <div class="ml-result-card">
                <h5>PM2.5 Impact</h5>
                <div style="font-size:0.85rem">
                    Concentration: ${pm25.concentration || '--'} ug/m3<br>
                    Exceeds WHO: ${pm25.exceeds_who ? 'Yes' : 'No'}<br>
                    Max AP: ${maxAP.toFixed(2)}%<br>
                    HQ: ${pm25.hazard_quotient || '--'}
                </div>
                <div style="font-size:0.75rem;color:var(--text-muted);margin-top:4px">
                    Method: WHO AirQ+ (Conti 2017, Liu 2019, Chen 2020)
                </div>
            </div>
        `;

        showToast('Success', `Risk: ${data.risk_level}`, 'success');
    } catch (err) {
        console.error('ML Health failed:', err);
        showToast('Error', 'Assessment failed', 'error');
    }
}

async function runMLSource() {
    const pollutant = document.getElementById('ml-source-pollutant').value;
    try {
        showToast('Analyzing', 'Running source apportionment...', 'info');

        const res = await fetch(`${API_BASE}/api/openair/source-apportionment?pollutant=${pollutant}`);
        const data = await res.json();

        const resultsDiv = document.getElementById('ml-results');
        resultsDiv.style.display = 'block';

        const dominant = data.dominant_source_direction || {};
        const sourceType = data.source_type_estimation || {};

        document.getElementById('ml-results-content').innerHTML = `
            <div class="ml-result-card">
                <h5>Source Apportionment</h5>
                <div class="result-value">${dominant.sector || 'N/A'}</div>
                <div class="result-label">Dominant Source Direction (${dominant.direction_deg || '--'}deg)</div>
            </div>
            <div class="ml-result-card">
                <h5>Source Type</h5>
                <div style="font-size:0.85rem">
                    <strong>${sourceType.dominant || 'N/A'}</strong><br>
                    Low speed: ${sourceType.low_speed_pct || 0}%<br>
                    High speed: ${sourceType.high_speed_pct || 0}%<br>
                    <em>${sourceType.interpretation || ''}</em>
                </div>
                <div style="font-size:0.75rem;color:var(--text-muted);margin-top:4px">
                    Data: ${data.data_source || 'N/A'}
                </div>
            </div>
        `;

        showToast('Success', `Source: ${sourceType.dominant || 'N/A'}`, 'success');
    } catch (err) {
        console.error('ML Source failed:', err);
        showToast('Error', 'Analysis failed', 'error');
    }
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

