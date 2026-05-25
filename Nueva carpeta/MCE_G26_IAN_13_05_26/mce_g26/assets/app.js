// ==================== CONFIGURACIÓN ====================
let currentMode = 'position';

// Socket.IO
const socket = io({
    transports: ['websocket'],
});

const realtimeChart = {
    canvas: null,
    chart: null,
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
    }
};

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

document.addEventListener('DOMContentLoaded', () => {

    realtimeChart.canvas =
        document.getElementById('chart');

});

function newChart(ctx, chartData) {

    return new Chart(ctx, {

        type: 'line',

        data: chartData,

        options: {

            responsive: true,

            animation: false,

            maintainAspectRatio: true,

            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

function renderChartData(obj, messages, maxPoints = 50) {

    if (!messages || messages.length === 0) {
        return;
    }

    for (const message of messages) {

        if (!message.ts) {
            continue;
        }

        const date = new Date(message.ts)
            .toLocaleTimeString();

        // Crear chart primera vez
        if (!obj.chart) {

            obj.data.labels.push(date);

            obj.data.datasets[0].data.push(message.value);

            obj.chart = newChart(
                obj.canvas.getContext('2d'),
                obj.data
            );

            continue;
        }

        // Actualizar chart existente
        obj.chart.data.labels.push(date);

        obj.chart.data.datasets[0].data.push(message.value);

        // Limitar puntos
        if (obj.chart.data.labels.length > maxPoints) {

            obj.chart.data.labels.shift();

            obj.chart.data.datasets[0].data.shift();
        }

        // Redibujar
        obj.chart.update();
    }
}
// ==================== SOCKET ====================

socket.on('data', (msg) => {
    console.log("DATA recibido:", msg);
    console.log("Chart en realtimeChart:", realtimeChart.chart);  // ¿es null?
    
    renderChartData(realtimeChart, [msg]);
    positionDiv.innerText = Number(msg.value).toFixed(2);
});


socket.on('disconnect', () => {
    statusSpan.innerText = 'DESCONECTADO';
    statusSpan.className = 'status disconnected';
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
window.renderChartData = renderChartData;
window.realtimeChart = realtimeChart;  // también expón el objeto