const API_URL = "";

let currentDevices = [];

document.addEventListener('DOMContentLoaded', () => {
    loadPage('devices');
});

function loadPage(pageName) {
    document.querySelectorAll('.nav-link').forEach(el => el.classList.remove('active'));
    const activeLink = document.querySelector(`[onclick="loadPage('${pageName}')"]`);
    if(activeLink) activeLink.classList.add('active');

    document.getElementById('view-devices').classList.add('d-none');
    document.getElementById('view-device-details').classList.add('d-none');
    document.getElementById('view-logs').classList.add('d-none');
    
    const mainContainer = document.getElementById('main-content');
    
    const existingIframe = mainContainer.querySelector('iframe');
    if(existingIframe) existingIframe.remove();
    
    const groupsView = document.getElementById('view-groups-placeholder');
    if(groupsView) groupsView.remove();

    if (pageName === 'devices') {
        document.getElementById('view-devices').classList.remove('d-none');
        fetchAndDisplayDevices();
    } 
    else if (pageName === 'groups') {
        const html = `
            <div id="view-groups-placeholder" class="text-center mt-5">
                <i class="fa-solid fa-layer-group fa-4x text-muted mb-3"></i>
                <h3>Zarządzanie Grupami</h3>
                <p class="text-muted">Funkcjonalność w trakcie wdrażania.</p>
                <button class="btn btn-primary" onclick="alert('Funkcja dostępna wkrótce!')">
                    <i class="fa-solid fa-plus"></i> Utwórz nową grupę
                </button>
            </div>
        `;
        mainContainer.insertAdjacentHTML('beforeend', html);
    } 
    else if (pageName === 'map') {
        const host = window.location.hostname; 
        const iframeHtml = `<iframe src="http://${host}:8080/#/network" width="100%" height="800px" style="border:none; border-radius:10px;"></iframe>`;
        mainContainer.insertAdjacentHTML('beforeend', iframeHtml);
    } 
    else if (pageName === 'logs') {
        document.getElementById('view-logs').classList.remove('d-none');
        fetchLogs();
    }
}

function showDeviceDetails(deviceId) {
    currentDetailId = deviceId;
    const device = currentDevices.find(d => d.id === deviceId);
    if(!device) return;

    document.getElementById('detail-name').innerText = device.name;
    document.getElementById('detail-id').innerText = device.id;
    document.getElementById('detail-new-name-input').value = device.name;

    const attrList = document.getElementById('detail-attributes');
    attrList.innerHTML = '';
    for (const [key, value] of Object.entries(device.state)) {
        if(typeof value === 'object') continue;
        const li = document.createElement('li');
        li.className = 'list-group-item d-flex justify-content-between align-items-center';
        li.innerHTML = `${key} <span class="badge bg-secondary rounded-pill">${value}</span>`;
        attrList.appendChild(li);
    }

    const controls = document.getElementById('detail-controls');
    controls.innerHTML = '';
    if(device.type === 'socket' || device.type === 'light') {
        const btn = document.createElement('button');
        const isOn = device.state.state === 'ON';
        btn.className = `btn w-100 btn-lg ${isOn ? 'btn-danger' : 'btn-success'}`;
        btn.innerText = isOn ? 'WYŁĄCZ' : 'WŁĄCZ';
        btn.onclick = () => toggleDevice(device.id, device.state.state, true);
        controls.appendChild(btn);
    } else {
        controls.innerHTML = '<p class="text-muted">Brak dostępnych akcji.</p>';
    }

    document.getElementById('view-devices').classList.add('d-none');
    document.getElementById('view-device-details').classList.remove('d-none');
}

async function fetchAndDisplayDevices() {
    try {
        const response = await fetch(`${API_URL}/devices`);
        const data = await response.json();
        currentDevices = data.devices;
        
        const listContainer = document.getElementById('devices-list');
        listContainer.innerHTML = '';

        if (currentDevices.length === 0) {
            listContainer.innerHTML = '<div class="col-12 text-center text-muted">Brak urządzeń.</div>';
            return;
        }

        currentDevices.forEach(device => {
            const col = document.createElement('div');
            col.className = 'col-md-4 col-sm-6';
            
            let icon = 'fa-question';
            let colorClass = 'text-secondary';
            const state = device.state?.state || 'UNKNOWN';

            if (device.type === 'socket') icon = 'fa-plug';
            else if (device.type === 'light') icon = 'fa-lightbulb';
            else if (device.type === 'sensor') icon = 'fa-temperature-half';

            if (state === 'ON') colorClass = 'text-warning';

            col.innerHTML = `
                <div class="card h-100 device-card shadow-sm">
                    <div class="card-body d-flex align-items-center">
                        <div class="me-3 text-center" style="width: 50px;">
                            <i class="fa-solid ${icon} fa-2x ${colorClass}"></i>
                        </div>
                        <div class="flex-grow-1" style="cursor: pointer;" onclick="showDeviceDetails('${device.id}')">
                            <h5 class="card-title mb-0">${device.name}</h5>
                            <small class="text-muted">${state}</small>
                        </div>
                        <div class="ms-2">
                            ${device.type !== 'sensor' ? `
                            <button class="btn btn-outline-primary btn-sm" onclick="toggleDevice('${device.id}', '${state}', false)">
                                <i class="fa-solid fa-power-off"></i>
                            </button>` : ''}
                        </div>
                    </div>
                </div>
            `;
            listContainer.appendChild(col);
        });
    } catch (error) { console.error("Błąd:", error); }
}

function createDeviceCard(device) {
    const col = document.createElement('div');
    col.className = 'col-md-4 col-sm-6';
    
    let icon = 'fa-question';
    let colorClass = 'text-secondary';
    const state = device.state?.state || 'UNKNOWN';

    if (device.type === 'socket') icon = 'fa-plug';
    else if (device.type === 'light') icon = 'fa-lightbulb';
    else if (device.type === 'sensor') icon = 'fa-temperature-half';

    if (state === 'ON') colorClass = 'text-warning';

    col.innerHTML = `
        <div class="card h-100 device-card shadow-sm">
            <div class="card-body d-flex align-items-center">
                <!-- Ikona -->
                <div class="me-3 text-center" style="width: 50px;">
                    <i class="fa-solid ${icon} fa-2x ${colorClass}"></i>
                </div>
                
                <!-- Tekst (Klikalny -> Szczegóły) -->
                <div class="flex-grow-1" style="cursor: pointer;" onclick="showDeviceDetails('${device.id}')">
                    <h5 class="card-title mb-0">${device.name}</h5>
                    <small class="text-muted">${state}</small>
                </div>
                
                <!-- Szybki przycisk (tylko dla sterowalnych) -->
                <div class="ms-2">
                    ${device.type !== 'sensor' ? `
                    <button class="btn btn-outline-primary btn-sm" onclick="toggleDevice('${device.id}', '${state}', false)">
                        <i class="fa-solid fa-power-off"></i>
                    </button>` : ''}
                </div>
            </div>
        </div>
    `;
    return col;
}

async function toggleDevice(deviceId, currentState, refreshDetails = false) {
    const action = (currentState === 'ON') ? 'turn_off' : 'turn_on';
    try {
        await fetch(`${API_URL}/devices/action`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ device_id: deviceId, action: action })
        });
        setTimeout(() => {
            fetchAndDisplayDevices();
            if(refreshDetails) {
                fetch(`${API_URL}/devices`).then(r => r.json()).then(d => {
                    currentDevices = d.devices;
                    showDeviceDetails(deviceId);
                });
            }
        }, 500);
    } catch (e) { alert("Błąd: " + e); }
}

async function renameCurrentDevice() {
    if(!currentDetailId) return;
    const newName = document.getElementById('detail-new-name-input').value;
    if(!newName) return alert("Podaj nazwę!");
    if(confirm(`Zmienić nazwę na "${newName}"?`)) {
        try {
            await fetch(`${API_URL}/devices/${currentDetailId}/rename`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ new_name: newName })
            });
            alert("Wysłano żądanie zmiany nazwy.");
            loadPage('devices');
        } catch(e) { console.error(e); }
    }
}

async function deleteCurrentDevice() {
    if(!currentDetailId) return;
    if(confirm("Usunąć urządzenie?")) {
        try {
            await fetch(`${API_URL}/devices/${currentDetailId}`, { method: 'DELETE' });
            alert("Usunięto.");
            loadPage('devices');
        } catch(e) { console.error(e); }
    }
}

async function fetchLogs() {
    const container = document.getElementById('logs-container');
    container.innerText = "Pobieranie...";
    try {
        const res = await fetch(`${API_URL}/logs?lines=100`);
        const data = await res.json();
        container.innerText = data.logs.reverse().join("");
    } catch(e) { container.innerText = "Błąd pobierania logów."; }
}

async function startPairing() {
    document.getElementById('pairing-status').classList.add('d-none');
    document.getElementById('pairing-active').classList.remove('d-none');
    try {
        await fetch(`${API_URL}/system/pairing/true`, { method: 'POST' });
        let timeLeft = 60;
        const counterEl = document.getElementById('countdown');
        const interval = setInterval(() => {
            timeLeft--;
            counterEl.innerText = timeLeft;
            if (timeLeft <= 0) {
                clearInterval(interval);
                finishPairing();
            }
        }, 1000);
    } catch (e) { alert("Błąd: " + e); }
}

async function finishPairing() {
    await fetch(`${API_URL}/system/pairing/false`, { method: 'POST' });
    bootstrap.Modal.getInstance(document.getElementById('addDeviceModal')).hide();
    document.getElementById('pairing-status').classList.remove('d-none');
    document.getElementById('pairing-active').classList.add('d-none');
    document.getElementById('countdown').innerText = "60";
    fetchAndDisplayDevices();
    alert("Wyszukiwanie zakończone.");
}