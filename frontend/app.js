const API_URL = "";

let currentDevices = [];

document.addEventListener('DOMContentLoaded', () => {
    loadPage('devices');
});

function loadPage(pageName) {
    document.querySelectorAll('.nav-link').forEach(el => el.classList.remove('active'));
    const activeLink = document.querySelector(`[onclick="loadPage('${pageName}')"]`);
    if(activeLink) activeLink.classList.add('active');

    const container = document.getElementById('main-content');

    if (pageName === 'devices') {
        renderDevicesPage(container);
    } else if (pageName === 'groups') {
        container.innerHTML = '<h2>Grupy</h2><p>Tutaj będzie zarządzanie grupami.</p>';
    } else if (pageName === 'map') {
        const host = window.location.hostname; 
        container.innerHTML = `<iframe src="http://${host}:8080" width="100%" height="800px" style="border:none; border-radius:10px;"></iframe>`;
    } else if (pageName === 'logs') {
        container.innerHTML = '<h2>Logi systemowe</h2><pre class="bg-dark text-white p-3 rounded">Ładowanie...</pre>';
    }
}

async function renderDevicesPage(container) {
    container.innerHTML = `
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h2>Twoje Urządzenia</h2>
            <button class="btn btn-success" data-bs-toggle="modal" data-bs-target="#addDeviceModal">
                <i class="fa-solid fa-plus"></i> Dodaj urządzenie
            </button>
        </div>
        <div id="devices-list" class="row g-4">
            <div class="col-12 text-center"><div class="spinner-border"></div></div>
        </div>
    `;

    await fetchAndDisplayDevices();
}

async function fetchAndDisplayDevices() {
    try {
        const response = await fetch(`${API_URL}/devices`);
        const data = await response.json();
        currentDevices = data.devices;
        
        const listContainer = document.getElementById('devices-list');
        listContainer.innerHTML = '';

        if (currentDevices.length === 0) {
            listContainer.innerHTML = '<div class="col-12 text-center text-muted">Brak urządzeń. Kliknij "Dodaj urządzenie".</div>';
            return;
        }

        currentDevices.forEach(device => {
            const card = createDeviceCard(device);
            listContainer.appendChild(card);
        });

    } catch (error) {
        console.error("Błąd pobierania urządzeń:", error);
        document.getElementById('devices-list').innerHTML = `<div class="alert alert-danger">Błąd połączenia z API: ${error}</div>`;
    }
}

function createDeviceCard(device) {
    const col = document.createElement('div');
    col.className = 'col-md-4 col-sm-6';

    let icon = 'fa-question';
    let statusClass = 'status-unknown';
    let isOne = false;

    const state = device.state?.state || 'UNKNOWN';

    if (device.type === 'socket') icon = 'fa-plug';
    else if (device.type === 'light') icon = 'fa-lightbulb';
    else if (device.type === 'sensor') icon = 'fa-temperature-half';

    if (state === 'ON') {
        statusClass = 'status-on';
        isOne = true;
    } else if (state === 'OFF') {
        statusClass = 'status-off';
    }

    let extras = '';
    if(device.state?.power) extras += `<small class="text-muted me-2">${device.state.power} W</small>`;
    if(device.state?.temperature) extras += `<small class="text-muted me-2">${device.state.temperature} °C</small>`;

    col.innerHTML = `
        <div class="card h-100 device-card ${isOne ? 'device-on' : ''}">
            <div class="card-body d-flex align-items-center">
                <div class="me-3 text-center" style="width: 50px;">
                    <i class="fa-solid ${icon} device-icon"></i>
                </div>
                <div class="flex-grow-1">
                    <h5 class="card-title mb-1">${device.name}</h5>
                    <div class="mb-2">
                        <span class="status-indicator ${statusClass}"></span>
                        <span class="text-muted small">${state}</span>
                    </div>
                    <div>${extras}</div>
                </div>
                <div class="ms-2">
                    ${device.type !== 'sensor' ? `
                    <button class="btn btn-outline-primary btn-sm" onclick="toggleDevice('${device.id}', '${state}')">
                        <i class="fa-solid fa-power-off"></i>
                    </button>` : ''}
                </div>
            </div>
        </div>
    `;
    return col;
}

async function toggleDevice(deviceId, currentState) {
    const action = (currentState === 'ON') ? 'turn_off' : 'turn_on';
    
    try {
        const response = await fetch(`${API_URL}/devices/action`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                device_id: deviceId,
                action: action
            })
        });

        if (response.ok) {
            setTimeout(fetchAndDisplayDevices, 500);
        } else {
            alert("Błąd sterowania urządzeniem!");
        }
    } catch (error) {
        console.error("Błąd:", error);
    }
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

    } catch (e) {
        alert("Błąd uruchamiania parowania: " + e);
    }
}

async function finishPairing() {
    await fetch(`${API_URL}/system/pairing/false`, { method: 'POST' });
    
    const modalEl = document.getElementById('addDeviceModal');
    const modal = bootstrap.Modal.getInstance(modalEl);
    modal.hide();

    document.getElementById('pairing-status').classList.remove('d-none');
    document.getElementById('pairing-active').classList.add('d-none');
    document.getElementById('countdown').innerText = "60";

    fetchAndDisplayDevices();
    alert("Wyszukiwanie zakończone. Sprawdź listę urządzeń.");
}