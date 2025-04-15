import json
import numpy as np
from datetime import datetime

with open('../data/teams_analysis_results.json', 'r', encoding='utf-8') as teams_file:
    teams_data = json.load(teams_file)

with open('../data/big-data.json', 'r', encoding='utf-8') as matches_file:
    matches_data = json.load(matches_file)

def get_date(date_str):
    dictionary_months = {
        "ENE": "01",
        "FEB": "02",
        "MAR": "03",
        "ABR": "04",
        "MAY": "05",
        "JUN": "06",
        "JUL": "07",
        "AGO": "08",
        "SEP": "09",
        "OCT": "10",
        "NOV": "11",
        "DIC": "12"
    }
    month = date_str.split(" ")[1]
    month_number = dictionary_months.get(month, "01")  # Default to January if not found
    day = date_str.split(" ")[0]
    year = date_str.split(" ")[2]
    return f"{day}-{month_number}-{year}"

# Función para calcular el promedio de "elo" de los jugadores destacados de un equipo
def calculate_team_elo(team_name):
    for team, data in teams_data.items():
        if team_name.lower() in team.lower():
            players = data.get("players_data", [])
            additional_data = data.get("top_players", {}).get("additional_data", {})
            league_perfomance = additional_data.get("league_performance", [])
            european_competition = data.get("top_players", {}).get("european_competition", {})
            
            get_date_match = get_date(european_competition.get("match_date", "N/A"))

            # Obtener la fecha del último partido
            last_match_date_str = get_date_match
            if last_match_date_str != "N/A":
                try:
                    # Ajustar el formato para que coincida con el formato devuelto por get_date
                    last_match_date = datetime.strptime(last_match_date_str, "%d-%m-%Y")
                    days_since_last_match = (datetime.now() - last_match_date).days
                except ValueError:
                    print(f"Error al procesar la fecha: {last_match_date_str}")
                    days_since_last_match = 7  # Asumir 7 días si no hay datos válidos
            else:
                days_since_last_match = 7  # Asumir 7 días si no hay datos

            # Penalización por descanso insuficiente
            rest_penalty = max(0, 5 - days_since_last_match) * 2  # Penalizar si menos de 5 días de descanso

            league_position = 0
            league_points = 0
            if league_perfomance:
                for performance in league_perfomance:
                    league_position = int(performance[0])
                    league_points = int(performance[3])
                    break
            common_eleven = additional_data.get("common_eleven", [])
            injured_players = additional_data.get("injuries", [])

            total_elo = 0
            player_count = 0

            for player in players:
                # Calcular el "elo" para cada jugador
                matches = int(player.get("matches", 0))
                goals = int(player.get("goals", 0))
                assists = int(player.get("assists", 0))
                cards = int(player.get("cards", 0))
                name = player.get("name", "")

                # Si es portero, considerar "goals" como "paradas"
                if player.get("position", "").lower() == "portero":
                    elo = matches * 2 + goals * 3 - cards
                else:
                    elo = matches * 2 + goals * 4 + assists * 2 - cards

                # Incrementar el ELO si el jugador aparece en el once más repetido
                if name in common_eleven:
                    elo += 10

                # Penalizar si el jugador está lesionado
                if any(injury.get("left_content", "").lower() == name.lower() for injury in injured_players):
                    elo -= 5

                total_elo += elo
                player_count += 1

            # Ajustar el ELO del equipo según la posición en liga y puntos
            team_elo = total_elo / player_count if player_count > 0 else 0
            team_elo += league_points * 0.1  # Incrementar por puntos en liga
            team_elo -= league_position * 0.5  # Penalizar por posición en liga (más alto = peor posición)

            # Aplicar penalización por descanso insuficiente
            team_elo -= rest_penalty

            return team_elo
    return 0  # Si no hay datos del equipo, devolver 0

# Función para obtener los datos de los jugadores de un equipo
def get_players_data(team_name):
    for team, data in teams_data.items():
        if team_name.lower() in team.lower():
            players = data.get("players_data", [])
            return [{
                "name": player.get("name"),
                "position": player.get("position"),
                "elo": calculate_team_elo(player.get("name"))
            } for player in players]
    return []  # Si no hay datos del equipo, devolver lista vacía

# Generar el análisis en formato quiniela usando un árbol de decisiones
quiniela_results = []

for match in matches_data:
    team_a = match["team_a_name"]
    team_b = match["team_b_name"]

    # Calcular el promedio de "elo" para ambos equipos
    team_a_elo = calculate_team_elo(team_a)
    # Se añade un bono de 5 puntos al equipo local
    team_a_elo += 5
    team_b_elo = calculate_team_elo(team_b)

    # Crear un árbol de decisiones con NumPy
    elo_diff = team_a_elo - team_b_elo

    # Condiciones del árbol de decisiones
    result = np.select(
        condlist=[
            np.abs(elo_diff) < 1,  # Si la diferencia de ELO es menor a 1
            elo_diff > 0,          # Si el ELO del equipo A es mayor
            elo_diff < 0           # Si el ELO del equipo B es mayor
        ],
        choicelist=["X", "1", "2"],  # Resultados correspondientes
        default="X"                  # Valor por defecto (empate)
    )

    # Agregar el resultado al análisis
    quiniela_results.append({
        "match": f"{team_a} vs {team_b}",
        "elo_team_a": team_a_elo,
        "elo_team_b": team_b_elo,
        "result": result,
        "analysis_url": match["analysis_url"]
    })

# Mostrar los resultados
for result in quiniela_results:
    print(f"Partido: {result['match']}")
    print(f"Elo Equipo A: {result['elo_team_a']}")
    print(f"Elo Equipo B: {result['elo_team_b']}")
    print(f"Resultado Quiniela: {result['result']}")
    print(f"Análisis: {result['analysis_url']}")
    print("-" * 40)