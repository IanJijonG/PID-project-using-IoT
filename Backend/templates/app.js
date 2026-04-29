// ==================== CONFIGURACIÓN ====================
let currentMode = 'position';

// Socket.IO
const socket = io({
    transports: ['websocket'],
});

// DOM
const statusSpan = document.getElementById('status');
const positionDiv = document.getElementById('position');
const modeIndicator = document.getElementById('modeIndicator');
const modeValueLabel = document.getElementById('modeValueLabel');
const setpointLabel = document.getElementById('setpointLabel');
const setpointInput = document.getElementById('setpoint');
const graphModeLabel = document.getElementById('graphModeLabel');
const modePositionBtn = document.getElementById('modePositionBtn');
const modeVelocityBtn = document.getElementById('modeVelocityBtn');

// ==================== MODO ====================
function setControlMode(mode) {
    if (mode === currentMode) return;

    currentMode = mode;

    if (mode === 'position') {
        modeIndicator.innerHTML = '🎯 Modo POSICIÓN activo';
        modeIndicator.className = 'mode-indicator mode-position-indicator';
        setpointLabel.innerHTML = 'Setpoint (posición deseada)';
        setpointInput.placeholder = 'Ingrese posición deseada';
        modeValueLabel.innerHTML = 'Posición actual';
        graphModeLabel.innerHTML = 'Posición';

        modePositionBtn.classList.add('active');
        modeVelocityBtn.classList.remove('active');

        positionDiv.style.background = '#e0e7ff';
    } else {
        modeIndicator.innerHTML = '⚡ Modo VELOCIDAD activo';
        modeIndicator.className = 'mode-indicator mode-velocity-indicator';
        setpointLabel.innerHTML = 'Setpoint (velocidad deseada)';
        setpointInput.placeholder = 'Ingrese velocidad deseada';
        modeValueLabel.innerHTML = 'Velocidad actual';
        graphModeLabel.innerHTML = 'Velocidad';

        modeVelocityBtn.classList.add('active');
        modePositionBtn.classList.remove('active');

        positionDiv.style.background = '#d1fae5';
    }

    socket.emit('command', {
        cmd: 'control_mode',
        mode: mode,
        timestamp: Date.now()
    });

    positionDiv.style.transform = 'scale(1.02)';
    setTimeout(() => positionDiv.style.transform = 'scale(1)', 200);
}

// ==================== CHART ====================
const ctx = document.getElementById('chart').getContext('2d');

const chart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: [],
        datasets: [{
            label: 'Valor Actual',
            data: [],
            borderColor: '#1e6bff',
            backgroundColor: 'rgba(30,107,255,0.1)',
            tension: 0.2,
            pointRadius: 2,
            fill: false
        }]
    },
    options: {
        animation: false,
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            y: {
                beginAtZero: true,
                title: { display: true, text: 'Valor' }
            },
            x: {
                title: { display: true, text: 'Muestras' }
            }
        }
    }
});

// ==================== SOCKET ====================
socket.on('connect', () => {
    statusSpan.innerText = 'CONECTADO';
    statusSpan.className = 'status connected';

    socket.emit('command', { cmd: 'get_mode' });
});

socket.on('disconnect', () => {
    statusSpan.innerText = 'DESCONECTADO';
    statusSpan.className = 'status disconnected';
});

// Datos
socket.on('data', (msg) => {

    if (msg && msg.positions) {
        msg.positions.forEach((pos) => {

            positionDiv.innerText = parseFloat(pos).toFixed(2);

            chart.data.labels.push('');
            chart.data.datasets[0].data.push(pos);

            if (chart.data.labels.length > 50) {
                chart.data.labels.shift();
                chart.data.datasets[0].data.shift();
            }
        });

        chart.update();
    }

    else if (msg && msg.position !== undefined) {
        const value = parseFloat(msg.position).toFixed(2);
        positionDiv.innerText = value;

        chart.data.labels.push('');
        chart.data.datasets[0].data.push(msg.position);

        if (chart.data.labels.length > 50) {
            chart.data.labels.shift();
            chart.data.datasets[0].data.shift();
        }

        chart.update();
    }
});

// Cambio de modo desde servidor
socket.on('mode_changed', (data) => {
    if (data && data.mode && data.mode !== currentMode) {
        setControlMode(data.mode);
    }
});

// ==================== FUNCIONES ====================
function sendSetpoint() {
    const sp = setpointInput.value;

    if (sp === '' || isNaN(sp)) {
        alert('Ingrese valor válido');
        return;
    }

    socket.emit('command', {
        cmd: 'setpoint',
        value: parseFloat(sp),
        mode: currentMode
    });
}

function sendPID() {
    const kp = document.getElementById('kp').value;
    const ki = document.getElementById('ki').value;
    const kd = document.getElementById('kd').value;

    socket.emit('command', {
        cmd: 'pid',
        kp: parseFloat(kp),
        ki: parseFloat(ki),
        kd: parseFloat(kd),
        mode: currentMode
    });
}

function sendManualStart() {
    socket.emit('command', { cmd: 'manual', action: 'start' });
}

function sendManualStop() {
    socket.emit('command', { cmd: 'manual', action: 'stop' });
}

function sendManualReset() {
    socket.emit('command', { cmd: 'manual', action: 'reset' });
    setpointInput.value = '0';
}

function sendCodeToMicro() {
    const language = document.getElementById('codeLanguage').value;
    const code = document.getElementById('codeArea').value;

    socket.emit('code', {
        language: language,
        code: code,
        mode: currentMode
    });

    document.getElementById('codeFeedback').innerText = 'Código enviado';
}

function clearCode() {
    document.getElementById('codeArea').value = '';
}

function downloadCSV() {
    window.open('/export_csv', '_blank');
}

// ==================== GLOBAL ====================
window.setControlMode = setControlMode;
window.sendSetpoint = sendSetpoint;
window.sendPID = sendPID;
window.sendManualStart = sendManualStart;
window.sendManualStop = sendManualStop;
window.sendManualReset = sendManualReset;
window.sendCodeToMicro = sendCodeToMicro;
window.clearCode = clearCode;
window.downloadCSV = downloadCSV;