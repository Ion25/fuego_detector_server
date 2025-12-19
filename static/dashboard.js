const API_URL = window.location.origin;
const UPDATE_INTERVAL = 2000;
const MAX_DATA_POINTS = 20;

const historialDatos = {
    timestamps: [],
    temperatura: [],
    luz: [],
    humedad: [],
    presion: []
};

const chartConfig = {
    type: 'line',
    options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
            intersect: false,
            mode: 'index'
        },
        plugins: {
            legend: {
                display: false
            },
            tooltip: {
                backgroundColor: 'rgba(255, 255, 255, 0.95)',
                titleColor: '#2c3e50',
                bodyColor: '#2c3e50',
                borderColor: '#e0e0e0',
                borderWidth: 1,
                padding: 12,
                displayColors: false,
                titleFont: {
                    size: 12,
                    weight: '500'
                },
                bodyFont: {
                    size: 14,
                    weight: '300'
                }
            }
        },
        scales: {
            x: {
                display: true,
                grid: {
                    display: false
                },
                ticks: {
                    color: '#95a5a6',
                    font: {
                        size: 10
                    },
                    maxRotation: 0
                }
            },
            y: {
                display: true,
                grid: {
                    color: '#f0f0f0',
                    drawBorder: false
                },
                ticks: {
                    color: '#95a5a6',
                    font: {
                        size: 11
                    }
                }
            }
        },
        animation: {
            duration: 750
        }
    }
};

const chartTemperatura = new Chart(
    document.getElementById('chartTemperatura').getContext('2d'),
    {
        ...chartConfig,
        data: {
            labels: [],
            datasets: [{
                label: 'Temperatura',
                data: [],
                borderColor: '#e74c3c',
                backgroundColor: 'rgba(231, 76, 60, 0.1)',
                borderWidth: 2,
                tension: 0.4,
                fill: true,
                pointRadius: 3,
                pointBackgroundColor: '#e74c3c',
                pointBorderColor: '#fff',
                pointBorderWidth: 2
            }]
        }
    }
);

const chartLuz = new Chart(
    document.getElementById('chartLuz').getContext('2d'),
    {
        ...chartConfig,
        data: {
            labels: [],
            datasets: [{
                label: 'Luz',
                data: [],
                borderColor: '#f39c12',
                backgroundColor: 'rgba(243, 156, 18, 0.1)',
                borderWidth: 2,
                tension: 0.4,
                fill: true,
                pointRadius: 3,
                pointBackgroundColor: '#f39c12',
                pointBorderColor: '#fff',
                pointBorderWidth: 2
            }]
        }
    }
);

const chartHumedad = new Chart(
    document.getElementById('chartHumedad').getContext('2d'),
    {
        ...chartConfig,
        data: {
            labels: [],
            datasets: [{
                label: 'Humedad',
                data: [],
                borderColor: '#3498db',
                backgroundColor: 'rgba(52, 152, 219, 0.1)',
                borderWidth: 2,
                tension: 0.4,
                fill: true,
                pointRadius: 3,
                pointBackgroundColor: '#3498db',
                pointBorderColor: '#fff',
                pointBorderWidth: 2
            }]
        }
    }
);

const chartPresion = new Chart(
    document.getElementById('chartPresion').getContext('2d'),
    {
        ...chartConfig,
        data: {
            labels: [],
            datasets: [{
                label: 'Presión',
                data: [],
                borderColor: '#9b59b6',
                backgroundColor: 'rgba(155, 89, 182, 0.1)',
                borderWidth: 2,
                tension: 0.4,
                fill: true,
                pointRadius: 3,
                pointBackgroundColor: '#9b59b6',
                pointBorderColor: '#fff',
                pointBorderWidth: 2
            }]
        }
    }
);

function actualizarGraficos(lectura) {
    if (!lectura) return;

    const now = new Date();
    const timeLabel = now.toLocaleTimeString('es-PE', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });

    historialDatos.timestamps.push(timeLabel);
    historialDatos.temperatura.push(lectura.temperatura);
    historialDatos.luz.push(lectura.luz);
    historialDatos.humedad.push(lectura.humedad);
    historialDatos.presion.push(lectura.presion);

    if (historialDatos.timestamps.length > MAX_DATA_POINTS) {
        historialDatos.timestamps.shift();
        historialDatos.temperatura.shift();
        historialDatos.luz.shift();
        historialDatos.humedad.shift();
        historialDatos.presion.shift();
    }

    chartTemperatura.data.labels = historialDatos.timestamps;
    chartTemperatura.data.datasets[0].data = historialDatos.temperatura;
    chartTemperatura.update('none');

    chartLuz.data.labels = historialDatos.timestamps;
    chartLuz.data.datasets[0].data = historialDatos.luz;
    chartLuz.update('none');

    chartHumedad.data.labels = historialDatos.timestamps;
    chartHumedad.data.datasets[0].data = historialDatos.humedad;
    chartHumedad.update('none');

    chartPresion.data.labels = historialDatos.timestamps;
    chartPresion.data.datasets[0].data = historialDatos.presion;
    chartPresion.update('none');
}

async function actualizarDashboard() {
    try {
        const responseEstado = await fetch(`${API_URL}/api/estado`);
        const estado = await responseEstado.json();

        actualizarEstado(estado);
        actualizarSensores(estado.ultima_lectura);
        actualizarGraficos(estado.ultima_lectura);

        const responseEventos = await fetch(`${API_URL}/api/eventos?limit=10`);
        const eventos = await responseEventos.json();
        actualizarEventos(eventos.eventos);

        if (estado.ultima_foto) {
            mostrarImagen(estado.ultima_foto);
        }

        document.getElementById('updateTime').textContent =
            `Última actualización: ${new Date().toLocaleTimeString('es-PE')}`;

    } catch (error) {
        console.error('Error al actualizar dashboard:', error);
    }
}

function actualizarEstado(estado) {
    const indicator = document.getElementById('statusIndicator');
    const estadoActual = estado.estado_actual;

    indicator.className = 'status-indicator';

    switch(estadoActual) {
        case 'Normal':
            indicator.classList.add('status-normal');
            indicator.innerHTML = 'NORMAL<br><small style="font-size: 0.6em; font-weight: 300;">Sistema operando correctamente</small>';
            break;
        case 'Alerta':
            indicator.classList.add('status-alerta');
            indicator.innerHTML = 'ALERTA<br><small style="font-size: 0.6em; font-weight: 300;">Valores elevados detectados</small>';
            break;
        case 'Peligro':
            indicator.classList.add('status-peligro');
            indicator.innerHTML = 'PELIGRO<br><small style="font-size: 0.6em; font-weight: 300;">Umbrales críticos superados</small>';
            break;
        case 'Fuego_Confirmado':
            indicator.classList.add('status-fuego');
            indicator.innerHTML = 'FUEGO CONFIRMADO<br><small style="font-size: 0.6em; font-weight: 300;">Presencia de fuego detectada</small>';
            break;
        default:
            indicator.innerHTML = 'DESCONOCIDO';
    }
}

function actualizarSensores(lectura) {
    if (!lectura) {
        return;
    }

    document.getElementById('temperatura').textContent = `${lectura.temperatura.toFixed(1)}°C`;
    document.getElementById('luz').textContent = `${lectura.luz.toFixed(0)} lux`;
    document.getElementById('humedad').textContent = `${lectura.humedad.toFixed(1)}%`;
    document.getElementById('presion').textContent = `${lectura.presion.toFixed(1)} hPa`;
}

function actualizarEventos(eventos) {
    const eventLog = document.getElementById('eventLog');

    if (!eventos || eventos.length === 0) {
        eventLog.innerHTML = '<div style="text-align: center; color: #999;">No hay eventos registrados</div>';
        return;
    }

    let html = '';
    eventos.forEach(evento => {
        const timestamp = new Date(evento.timestamp).toLocaleString('es-PE');
        html += `
            <div class="event-item">
                <span class="event-timestamp">${timestamp}</span><br>
                <span class="event-tipo">${evento.tipo}:</span> ${evento.descripcion}
            </div>
        `;
    });

    eventLog.innerHTML = html;
}

function mostrarImagen(rutaImagen) {
    const img = document.getElementById('imagenPreview');
    const noImage = document.getElementById('noImage');

    img.src = `${API_URL}/${rutaImagen}`;
    img.style.display = 'block';
    noImage.style.display = 'none';
}

async function actualizarUltimasFotos() {
    try {
        const resp = await fetch(`${API_URL}/api/ultimas-fotos?limit=5`);
        const data = await resp.json();
        const fotosList = document.getElementById('fotosList');
        const noFotos = document.getElementById('noFotos');
        fotosList.innerHTML = '';

        if (!data || !data.fotos || data.fotos.length === 0) {
            noFotos.style.display = 'block';
            return;
        }

        noFotos.style.display = 'none';

        data.fotos.forEach((ruta, idx) => {
            const img = document.createElement('img');
            img.src = `${API_URL}/${ruta}`;
            img.className = 'thumb';
            img.alt = `Captura ${idx+1}`;
            img.dataset.full = `${API_URL}/${ruta}`;
            img.addEventListener('click', () => openModal(img.dataset.full));
            fotosList.appendChild(img);
        });
    } catch (e) {
        console.error('Error cargando últimas fotos:', e);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const list = document.getElementById('fotosList');
    document.getElementById('prevFoto').addEventListener('click', () => {
        list.scrollBy({ left: -200, behavior: 'smooth' });
    });
    document.getElementById('nextFoto').addEventListener('click', () => {
        list.scrollBy({ left: 200, behavior: 'smooth' });
    });

    const modal = document.getElementById('fotoModal');
    const modalImg = document.getElementById('modalImage');
    const closeBtn = document.getElementById('closeModal');

    window.openModal = (src) => {
        modal.style.display = 'flex';
        modalImg.src = src;
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    closeBtn.addEventListener('click', () => {
        modal.style.display = 'none';
        modalImg.src = '';
    });

    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.style.display = 'none';
            modalImg.src = '';
        }
    });
});

async function actualizarDashboardWrapper() {
    await actualizarDashboard();
    await actualizarUltimasFotos();
}

actualizarDashboardWrapper();
setInterval(actualizarDashboardWrapper, UPDATE_INTERVAL);

console.log('Dashboard iniciado - Actualización cada', UPDATE_INTERVAL/1000, 'segundos');
