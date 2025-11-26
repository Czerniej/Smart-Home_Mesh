const API_URL = "";
let currentDetailId = null;
let currentGroupDetails = null;
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
    document.getElementById('view-groups').classList.add('d-none');
    document.getElementById('view-group-details').classList.add('d-none');
    document.getElementById('view-logs').classList.add('d-none');
    
    const mainContainer = document.getElementById('main-content');
    
    const existingIframe = mainContainer.querySelector('iframe');
    if(existingIframe) existingIframe.remove();
    
    const groupsView = document.getElementById('view-groups-placeholder');
    if(groupsView) groupsView.remove();

    if(pageName === 'devices') {
        document.getElementById('view-devices').classList.remove('d-none');
        fetchAndDisplayDevices();
    } 
    else if(pageName === 'groups') {
        document.getElementById('view-groups').classList.remove('d-none');
        fetchAndDisplayGroups();
    }
    else if(pageName === 'map') {
        const host = window.location.hostname; 
        const iframeHtml = `<iframe src="http://${host}:8080/#/network" width="100%" height="800px" style="border:none; border-radius:10px;"></iframe>`;
        mainContainer.insertAdjacentHTML('beforeend', iframeHtml);
    } 
    else if(pageName === 'logs') {
        document.getElementById('view-logs').classList.remove('d-none');
        fetchLogs();
    }
}

function showDeviceDetails(deviceId, source = 'devices') {
    currentDetailId = deviceId;
    const device = currentDevices.find(d => d.id === deviceId);
    if(!device) return;
    const backBtn = document.getElementById('btn-device-back');
    if(source === 'group_details') {
        backBtn.onclick = () => showGroupDetails(currentGroupDetails.id);
        backBtn.innerHTML = '<i class="fa-solid fa-arrow-left"></i> Powrót do grupy';
    } else {
        backBtn.onclick = () => loadPage('devices');
        backBtn.innerHTML = '<i class="fa-solid fa-arrow-left"></i> Powrót do listy';
    }
    document.getElementById('detail-name').innerText = device.name;
    document.getElementById('detail-id').innerText = device.id;
    document.getElementById('detail-new-name-input').value = device.name;

    const attrList = document.getElementById('detail-attributes');
    attrList.innerHTML = '';
    if(device.state) {
        for (const [key, value] of Object.entries(device.state)) {
            if(typeof value === 'object') continue;
            const li = document.createElement('li');
            li.className = 'list-group-item d-flex justify-content-between align-items-center';
            li.innerHTML = `${key} <span class="badge bg-secondary rounded-pill">${value}</span>`;
            attrList.appendChild(li);
        }
    }
    const controls = document.getElementById('detail-controls');
    controls.innerHTML = '';
    if(device.type === 'socket' || device.type === 'light') {
        const btn = document.createElement('button');
        const isOn = device.state && device.state.state === 'ON';
        btn.className = `btn w-100 btn-lg ${isOn ? 'btn-danger' : 'btn-success'}`;
        btn.innerText = isOn ? 'WYŁĄCZ' : 'WŁĄCZ';
        btn.onclick = () => toggleDevice(device.id, device.state?.state, true, source);
        controls.appendChild(btn);
    } else {
        controls.innerHTML = '<p class="text-muted">Brak dostępnych akcji sterujących.</p>';
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

        if(currentDevices.length === 0) {
            listContainer.innerHTML = '<div class="col-12 text-center text-muted">Brak urządzeń.</div>';
            return;
        }

        currentDevices.forEach(device => {
            const col = document.createElement('div');
            col.className = 'col-md-4 col-sm-6';
            
            let icon = 'fa-question';
            let colorClass = 'text-secondary';
            const state = device.state?.state || 'UNKNOWN';

            if(device.type === 'socket') icon = 'fa-plug';
            else if(device.type === 'light') icon = 'fa-lightbulb';
            else if(device.type === 'sensor') icon = 'fa-temperature-half';

            if(state === 'ON') colorClass = 'text-warning';

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

    if(device.type === 'socket') icon = 'fa-plug';
    else if(device.type === 'light') icon = 'fa-lightbulb';
    else if(device.type === 'sensor') icon = 'fa-temperature-half';

    if(state === 'ON') colorClass = 'text-warning';

    col.innerHTML = `
        <div class="card h-100 device-card shadow-sm">
            <div class="card-body d-flex align-items-center">
                <!-- Ikona -->
                <div class="me-3 text-center" style="width: 50px;">
                    <i class="fa-solid ${icon} fa-2x ${colorClass}"></i>
                </div>
                
                <!-- Tekst (Klikalny -> Szczegóły) -->
                <div class="flex-grow-1" style="cursor: pointer;" onclick="showDeviceDetails('${device.id}', 'devices')">
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

async function toggleDevice(deviceId, currentState, refreshDetails = false, sourceView = 'devices') {
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
                    showDeviceDetails(deviceId, sourceView);
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
            if(timeLeft <= 0) {
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

async function fetchAndDisplayGroups() {
    const listContainer = document.getElementById('groups-list');
    listContainer.innerHTML = '<div class="spinner-border"></div>';

    try {
        const response = await fetch(`${API_URL}/groups`);
        const data = await response.json();
        const groups = data.groups;
        listContainer.innerHTML = '';

        if(groups.length === 0) {
            listContainer.innerHTML = '<div class="col-12 text-center text-muted">Brak grup. Utwórz pierwszą.</div>';
            return;
        }

        groups.forEach(group => {
            const col = document.createElement('div');
            col.className = 'col-md-6 col-lg-4';
            const count = group.members.length;

            col.innerHTML = `
                <div class="card shadow-sm h-100" onclick="showGroupDetails('${group.id}')" style="cursor: pointer;">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h5 class="card-title mb-0">
                                <i class="fa-solid fa-layer-group text-primary me-2"></i>
                                ${group.name}
                            </h5>
                            <span class="badge bg-secondary">${count} urz.</span>
                        </div>
                        <p class="text-muted small">ID: ${group.id}</p>
                        
                        <div class="d-flex gap-2 mt-3">
                            <!-- stopPropagation zapobiega wejściu w szczegóły przy kliknięciu ON/OFF -->
                            <button class="btn btn-success flex-grow-1" onclick="event.stopPropagation(); toggleGroup('${group.id}', 'turn_on')">ON</button>
                            <button class="btn btn-danger flex-grow-1" onclick="event.stopPropagation(); toggleGroup('${group.id}', 'turn_off')">OFF</button>
                        </div>
                        <button class="btn btn-outline-danger btn-sm w-100 mt-2" onclick="event.stopPropagation(); deleteGroup('${group.id}')">
                            <i class="fa-solid fa-trash"></i> Usuń grupę
                        </button>
                    </div>
                </div>
            `;
            listContainer.appendChild(col);
        });

    } catch (error) {
        console.error(error);
        listContainer.innerHTML = `<div class="alert alert-danger">Błąd: ${error}</div>`;
    }
}

async function openAddGroupModal() {
    const container = document.getElementById('group-devices-selection');
    container.innerHTML = 'Pobieranie...';
    
    const modal = new bootstrap.Modal(document.getElementById('addGroupModal'));
    modal.show();

    try {
        const res = await fetch(`${API_URL}/devices`);
        const data = await res.json();
        
        container.innerHTML = '';
        if(data.devices.length === 0) {
            container.innerHTML = 'Brak urządzeń w systemie.';
            return;
        }

        data.devices.forEach(dev => {
            const label = document.createElement('label');
            label.className = 'list-group-item d-flex gap-2';
            label.innerHTML = `
                <input class="form-check-input flex-shrink-0 device-select-checkbox" type="checkbox" value="${dev.id}">
                <span>
                    ${dev.name} 
                    <small class="text-muted">(${dev.type})</small>
                </span>
            `;
            container.appendChild(label);
        });
    } catch(e) {
        container.innerText = "Błąd pobierania listy urządzeń.";
    }
}

async function createGroup() {
    const name = document.getElementById('new-group-name').value;
    if(!name) return alert("Podaj nazwę grupy!");

    const checkboxes = document.querySelectorAll('.device-select-checkbox:checked');
    const members = Array.from(checkboxes).map(cb => cb.value);

    if(members.length === 0) return alert("Wybierz przynajmniej jedno urządzenie.");

    const groupId = 'group_' + name.toLowerCase().replace(/\s+/g, '_') + '_' + Math.floor(Math.random()*1000);

    try {
        const res = await fetch(`${API_URL}/groups`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                id: groupId,
                name: name,
                members: members
            })
        });

        if(res.ok) {
            alert("Grupa utworzona!");
            const modalEl = document.getElementById('addGroupModal');
            bootstrap.Modal.getInstance(modalEl).hide();
            fetchAndDisplayGroups();
        } else {
            alert("Błąd tworzenia grupy.");
        }
    } catch(e) { alert("Błąd: " + e); }
}

async function deleteGroup(groupId) {
    if(confirm("Usunąć tę grupę?")) {
        try {
            await fetch(`${API_URL}/groups/${groupId}`, { method: 'DELETE' });
            fetchAndDisplayGroups();
        } catch(e) { alert("Błąd: " + e); }
    }
}

async function toggleGroup(groupId, action) {
    try {
        await fetch(`${API_URL}/devices/action`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                device_id: groupId,
                action: action
            })
        });
        alert("Wysłano polecenie do grupy.");
    } catch(e) { alert("Błąd: " + e); }
}

async function showGroupDetails(groupId) {
    try {
        const [resGroups, resDevices] = await Promise.all([
            fetch(`${API_URL}/groups`),
            fetch(`${API_URL}/devices`)
        ]);
        const dataGroups = await resGroups.json();
        const dataDevices = await resDevices.json();
        
        const group = dataGroups.groups.find(g => g.id === groupId);
        if(!group) return;

        currentGroupDetails = group;
        const allDevices = dataDevices.devices;

        document.getElementById('g-detail-name').innerText = group.name;
        document.getElementById('g-detail-id').innerText = group.id;

        document.getElementById('g-btn-on').onclick = () => toggleGroup(group.id, 'turn_on');
        document.getElementById('g-btn-off').onclick = () => toggleGroup(group.id, 'turn_off');

        const listContainer = document.getElementById('group-members-list');
        listContainer.innerHTML = '';

        if(group.members.length === 0) {
            listContainer.innerHTML = '<div class="col-12 text-center text-muted p-4">Ta grupa jest pusta.</div>';
        } else {
            group.members.forEach(memberId => {
                const deviceData = allDevices.find(d => d.id === memberId);
                if(deviceData) {
                    const card = createGroupMemberCard(deviceData, group.id);
                    listContainer.appendChild(card);
                }
            });
        }

        document.getElementById('view-groups').classList.add('d-none');
        document.getElementById('view-group-details').classList.remove('d-none');

    } catch(e) { console.error(e); alert("Błąd ładowania szczegółów grupy."); }
}

function createGroupMemberCard(device, groupId) {
    const col = document.createElement('div');
    col.className = 'col-md-6';
    
    let icon = 'fa-question';
    let colorClass = 'text-secondary';
    const state = device.state?.state || 'UNKNOWN';

    if (device.type === 'socket') icon = 'fa-plug';
    else if (device.type === 'light') icon = 'fa-lightbulb';
    else if (device.type === 'sensor') icon = 'fa-temperature-half';
    if (state === 'ON') colorClass = 'text-warning';

    col.innerHTML = `
        <div class="card h-100 shadow-sm border-0 bg-white device-in-group-card" 
             onclick="showDeviceDetails('${device.id}', 'group_details')"
             style="cursor: pointer; transition: transform 0.2s;">
             
            <div class="card-body d-flex align-items-center p-2">
                <div class="me-3 text-center" style="width: 40px;">
                    <i class="fa-solid ${icon} fa-lg ${colorClass}"></i>
                </div>
                <div class="flex-grow-1">
                    <h6 class="card-title mb-0">${device.name}</h6>
                    <small class="text-muted" style="font-size: 0.8rem">${state}</small>
                </div>
                
                <!-- Przycisk usuwania z grupy -->
                <!-- event.stopPropagation() jest kluczowe, żeby nie uruchamiać onclick rodzica -->
                <button class="btn btn-outline-danger btn-sm" 
                        onclick="event.stopPropagation(); removeMemberFromGroup('${groupId}', '${device.id}')" 
                        title="Usuń z grupy">
                    <i class="fa-solid fa-minus"></i>
                </button>
            </div>
        </div>
    `;
    return col;
}

async function openAddMemberModal() {
    const container = document.getElementById('available-devices-list');
    container.innerHTML = '<div class="text-center p-3"><div class="spinner-border"></div></div>';
    const modalEl = document.getElementById('addMemberModal');
    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();

    try {
        const res = await fetch(`${API_URL}/devices`);
        const data = await res.json();
        const allDevices = data.devices;
        
        if (!currentGroupDetails || !currentGroupDetails.members) return;
        const available = allDevices.filter(d => !currentGroupDetails.members.includes(d.id));

        container.innerHTML = '';
        if(available.length === 0) {
            container.innerHTML = '<div class="p-3 text-center text-muted">Brak dostępnych urządzeń do dodania.</div>';
            return;
        }

        available.forEach(dev => {
            const btn = document.createElement('button');
            btn.type = "button";
            btn.className = 'list-group-item list-group-item-action d-flex justify-content-between align-items-center';
            btn.innerHTML = `
                <span>
                    <i class="fa-solid fa-plus circle-icon me-2 text-primary"></i>
                    ${dev.name}
                </span>
                <small class="text-muted">${dev.type}</small>
            `;
            btn.onclick = () => addMemberToGroup(currentGroupDetails.id, dev.id);
            container.appendChild(btn);
        });

    } catch(e) { 
        container.innerText = "Błąd pobierania listy urządzeń."; 
        console.error(e);
    }
}

async function addMemberToGroup(groupId, deviceId) {
    try {
        const res = await fetch(`${API_URL}/groups/${groupId}/devices/${deviceId}`, { method: 'POST' });
        
        if(res.ok) {
            const modalEl = document.getElementById('addMemberModal');
            const modal = bootstrap.Modal.getInstance(modalEl);
            if(modal) modal.hide();
            showGroupDetails(groupId);
        } else {
            const err = await res.json();
            alert("Nie udało się dodać urządzenia: " + (err.detail || res.statusText));
        }
    } catch(e) { 
        alert("Błąd sieci: " + e); 
    }
}

async function removeMemberFromGroup(groupId, deviceId) {
    if(!confirm("Czy na pewno usunąć to urządzenie z grupy?")) return;
    try {
        const res = await fetch(`${API_URL}/groups/${groupId}/devices/${deviceId}`, { method: 'DELETE' });
        if(res.ok) {
            showGroupDetails(groupId); 
        } else {
            alert("Błąd usuwania z grupy.");
        }
    } catch(e) { alert("Błąd: " + e); }
}