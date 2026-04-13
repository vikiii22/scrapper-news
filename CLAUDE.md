Contexto:
Actúa como un Senior Python Developer y Data Scientist experto en apuestas deportivas. Crea un script profesional llamado quiniela_pro.py que automatice todo el flujo de predicción para la Quiniela española.

Requisitos Funcionales:

Módulo de Descarga de Datos:

Implementa una función para descargar vía GET (usando requests) los archivos SP1.csv y SP2.csv desde https://www.football-data.co.uk/mmz4281/2526/.

Debe verificar si el archivo ya existe localmente para no saturar el servidor, pero permitir una descarga forzada para actualizar datos.

Módulo de Web Scraping (Eduardo Losilla):

Usa BeautifulSoup para extraer la lista de los 15 partidos de la jornada actual desde https://www.eduardolosilla.es/.

Necesito que limpies los nombres de los equipos (ej: transformar "AT.MADRID" a "Ath Madrid" para que coincida con el CSV) usando un diccionario de mapeo inteligente.

Modelo Estadístico de Alta Resolución:

Time-Weighting (Decaimiento Exponencial): Los partidos más recientes deben tener más peso en el cálculo de la Fuerza de Ataque (AS) y Defensa (DS).

Distribución de Poisson + Ajuste Dixon-Coles: Calcula probabilidades para 1, X, 2. Aplica un factor de corrección de empates (aumentando un 10% la probabilidad de X en partidos con xG sumado bajo).

Ajuste por Competición Europea: Permite pasar un parámetro manual (ej: "Barcelona": -10% ataque) para simular cansancio tras Champions.

Lógica de Apuesta:

Genera una columna sencilla (1, X, 2).

Elige 8: El script debe identificar automáticamente los 8 partidos con mayor probabilidad de acierto (menor entropía).

Interfaz de Salida:

Muestra en la terminal una tabla formateada con tabulate o pandas.

Guarda el resultado en un archivo jornada_prediccion.csv.

Stack Tecnológico:
Python 3.10+, pandas, numpy, scipy, requests, beautifulsoup4.

Instrucción Adicional:
Escribe el código siguiendo principios SOLID, con comentarios claros en español y manejo de excepciones (try-except) para el scraping por si cambia la estructura de la web de Losilla.