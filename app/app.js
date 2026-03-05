// Cargar y renderizar predicciones de la quiniela

// Datos de ejemplo para pruebas (será reemplazado por la carga del JSON)
let quinielaData = [];

// Función para cargar los datos del JSON (ahora desde la API MongoDB)
async function loadQuinielaData() {
    try {
        // En desarrollo usamos el servidor local de FastAPI.
        // En producción (GitHub Pages), usamos el JSON estático servido desde la misma web
        const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';

        // Determinar URL de datos según si estamos en local o remoto
        const API_URL = isLocalhost
            ? 'http://localhost:8000/api/predictions'
            : 'api/predictions.json';

        console.log(`Cargando predicciones desde: ${API_URL}`);
        const response = await fetch(API_URL);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        quinielaData = await response.json();

        if (quinielaData.error) {
            console.error('API Error:', quinielaData.error);
            showError();
            return;
        }

        renderMatches();
    } catch (error) {
        console.error('Error cargando datos:', error);
        showError();
    }
}

// Función para obtener el nivel de confianza
function getConfidenceLevel(confidence) {
    if (confidence >= 40) return 'high';
    if (confidence >= 35) return 'medium';
    return 'low';
}

// Función para formatear la fecha
function formatDate(dateString) {
    const date = new Date(dateString);
    const days = ['DOM', 'LUN', 'MAR', 'MIÉ', 'JUE', 'VIE', 'SÁB'];
    const dayName = days[date.getDay()];
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    return { day: dayName, hour: `${hours}:${minutes}` };
}

// Función para renderizar un partido
function renderMatch(match, index) {
    const { day, hour } = formatDate(match.match_info.date);
    const confidenceLevel = getConfidenceLevel(match.confidence);

    const matchHTML = `
        <div class="match">
            <div class="match-header">
                <div class="match-number">${index + 1}</div>
                <div class="match-teams">
                    ${match.match_info.home_team} - ${match.match_info.away_team}
                </div>
                <div class="match-time">
                    <div class="match-day">${day}</div>
                    <div class="match-hour">${hour}</div>
                </div>
            </div>
            
            <div class="predictions">
                <button class="prediction-btn ${match.prediction === '1' ? 'selected' : ''}" 
                        data-match="${index}" data-bet="1">
                    1
                </button>
                <button class="prediction-btn ${match.prediction === 'X' ? 'selected' : ''}" 
                        data-match="${index}" data-bet="X">
                    X
                </button>
                <button class="prediction-btn ${match.prediction === '2' ? 'selected' : ''}" 
                        data-match="${index}" data-bet="2">
                    2
                </button>
            </div>
            
            <div class="probabilities">
                <div class="prob-item">
                    <div class="prob-label">Local (1)</div>
                    <div class="prob-value">${match.probabilities.home.toFixed(1)}%</div>
                </div>
                <div class="prob-item">
                    <div class="prob-label">Empate (X)</div>
                    <div class="prob-value">${match.probabilities.draw.toFixed(1)}%</div>
                </div>
                <div class="prob-item">
                    <div class="prob-label">Visitante (2)</div>
                    <div class="prob-value">${match.probabilities.away.toFixed(1)}%</div>
                </div>
                <div class="prob-item">
                    <div class="prob-label">Confianza</div>
                    <div class="prob-value">
                        <span class="confidence ${confidenceLevel}">
                            ${match.confidence.toFixed(1)}%
                        </span>
                    </div>
                </div>
            </div>
        </div>
    `;

    return matchHTML;
}

// Función para renderizar todos los partidos
function renderMatches() {
    const container = document.getElementById('matches-container');

    if (quinielaData.length === 0) {
        container.innerHTML = '<p style="text-align: center; padding: 40px;">No hay datos de quiniela disponibles</p>';
        return;
    }

    container.innerHTML = quinielaData.map((match, index) => renderMatch(match, index)).join('');

    // Agregar event listeners para los botones (opcional, para interactividad)
    addButtonListeners();
}

// Agregar interactividad a los botones
function addButtonListeners() {
    const buttons = document.querySelectorAll('.prediction-btn');
    buttons.forEach(button => {
        button.addEventListener('click', (e) => {
            const matchIndex = e.target.dataset.match;
            const bet = e.target.dataset.bet;

            // Remover selección previa de este partido
            const matchButtons = document.querySelectorAll(`[data-match="${matchIndex}"]`);
            matchButtons.forEach(btn => btn.classList.remove('selected'));

            // Agregar selección al botón clickeado
            e.target.classList.add('selected');

            // Actualizar predicción en los datos
            quinielaData[matchIndex].prediction = bet;

            console.log(`Partido ${parseInt(matchIndex) + 1}: ${bet} seleccionado`);
        });
    });
}

// Mostrar error si no se pueden cargar los datos
function showError() {
    const container = document.getElementById('matches-container');
    container.innerHTML = `
        <div style="text-align: center; padding: 40px; color: #dc3545;">
            <h3>⚠️ Error al cargar los datos</h3>
            <p>No se pudieron cargar las predicciones de la quiniela.</p>
            <p style="font-size: 0.9em; margin-top: 10px;">
                Asegúrate de ejecutar <code>python scripts/analyze_quiniela.py</code> para generar el JSON y de que el backend local esté activo (si aplicas en local).
            </p>
        </div>
    `;
}

// Actualizar timestamp en el header
function updateTimestamp() {
    const timestampElement = document.getElementById('timestamp');
    const now = new Date();
    const options = {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    };
    timestampElement.textContent = `Actualizado: ${now.toLocaleDateString('es-ES', options)}`;
}

// Inicializar la aplicación
document.addEventListener('DOMContentLoaded', () => {
    updateTimestamp();
    loadQuinielaData();
});

// Función para exportar/copiar el boleto (opcional)
function exportTicket() {
    const selections = quinielaData.map((match, index) => {
        return `${index + 1}. ${match.match_info.home_team} - ${match.match_info.away_team}: ${match.prediction} (${match.confidence.toFixed(1)}%)`;
    }).join('\n');

    console.log('Boleto de Quiniela:\n', selections);
    return selections;
}