import json
import numpy as np
from datetime import datetime
import requests
from bs4 import BeautifulSoup

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

def get_elo_from_casas_apuestas(casas_apuestas_url):
    if not casas_apuestas_url:
        return None

    try:
        response = requests.get(casas_apuestas_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Buscar el div con el JSON de cuotas
        mod_bet = soup.find('div', id='mod_bet')
        if not mod_bet:
            print("No se encontró el div de cuotas")
            return None

        data_odds = mod_bet.find('div', id='data-odds-tab')
        if not data_odds or not data_odds.has_attr('data_odds'):
            print("No se encontró el atributo data_odds")
            return None

        odds_json = json.loads(data_odds['data_odds'])
        cuotas = {}

        # Extraer cuotas 1X2 del partido completo (ft)
        for house_odds in odds_json['scopes']['ft'][0]['housesOdds']:
            casa = house_odds['houseName']
            bets = house_odds['bets']
            cuota_1 = bets[0]['value']
            cuota_x = bets[1]['value']
            cuota_2 = bets[2]['value']
            cuotas[casa] = {
                "1": float(cuota_1.replace(',', '.')),
                "X": float(cuota_x.replace(',', '.')),
                "2": float(cuota_2.replace(',', '.'))
            }

        # Calcular probabilidad implícita media para cada resultado
        probs = {"1": [], "X": [], "2": []}
        for casa, vals in cuotas.items():
            inv_1 = 1 / vals["1"]
            inv_x = 1 / vals["X"]
            inv_2 = 1 / vals["2"]
            overround = inv_1 + inv_x + inv_2
            probs["1"].append(inv_1 / overround)
            probs["X"].append(inv_x / overround)
            probs["2"].append(inv_2 / overround)

        avg_probs = {k: round(100 * sum(v) / len(v), 2) for k, v in probs.items() if v}

        return {
            "cuotas": cuotas,
            "probabilidades": avg_probs
        }

    except Exception as e:
        print(f"Error obteniendo cuotas: {e}")
        return None

# Función para calcular el promedio de "elo" de los jugadores destacados de un equipo
def calculate_team_elo(team_name):
    for team, data in teams_data.items():
        if team_name.lower() in team.lower():
            players = data.get("players_data", [])
            additional_data = data.get("top_players", {}).get("additional_data", {})
            league_perfomance = additional_data.get("league_performance", [])
            european_competition = data.get("top_players", {}).get("european_competition", {})
            # casas_apuestas = data.get("top_players", {}).get("casas_apuestas", {})

            # elo_from_casas_apuestas = get_elo_from_casas_apuestas(casas_apuestas)
            
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
    team_a_elo += 5  # Bono local
    team_b_elo = calculate_team_elo(team_b)

    # Obtener la url de apuestas del partido
    url_apuestas = match.get("url_apuestas")
    apuestas = get_elo_from_casas_apuestas(url_apuestas) if url_apuestas else None

    # Árbol de decisiones por ELO
    elo_diff = team_a_elo - team_b_elo
    pred_elo = "X" if np.abs(elo_diff) < 1 else ("1" if elo_diff > 0 else "2")

    # Árbol de decisiones por casas de apuestas (probabilidad más alta)
    pred_apuestas = None
    if apuestas and "probabilidades" in apuestas:
        probs = apuestas["probabilidades"]
        print(f"Probabilidades: {probs} para {team_a} vs {team_b}")
        pred_apuestas = max(probs, key=probs.get)  # "1", "X" o "2"

    # Combinación: si ambos coinciden, usar ese resultado; si no, priorizar ELO pero marcar la diferencia
    if pred_apuestas and pred_elo == pred_apuestas:
        final_pred = pred_elo
        fuente = "ELO+APUESTAS"
    elif pred_apuestas:
        final_pred = pred_elo + "/" + pred_apuestas
        fuente = "ELO/APUESTAS"
    else:
        final_pred = pred_elo
        fuente = "ELO"

    quiniela_results.append({
        "match": f"{team_a} vs {team_b}",
        "elo_team_a": team_a_elo,
        "elo_team_b": team_b_elo,
        "result": final_pred,
        "fuente": fuente,
        "analysis_url": match["analysis_url"],
        "apuesta_url": url_apuestas
    })

# Mostrar los resultados
for result in quiniela_results:
    print(f"Partido: {result['match']}")
    print(f"Elo Equipo A: {result['elo_team_a']}")
    print(f"Elo Equipo B: {result['elo_team_b']}")
    print(f"Resultado Quiniela: {result['result']} (Fuente: {result['fuente']})")
    print(f"Análisis: {result['analysis_url']}"),
    print(f"URL Apuestas: {result['apuesta_url']}")
    print("-" * 40)

# Guardar los resultados en un archivo de texto
with open("quiniela_results.txt", "w", encoding="utf-8") as f:
    for result in quiniela_results:
        f.write(f"Partido: {result['match']}\n")
        f.write(f"Elo Equipo A: {result['elo_team_a']}\n")
        f.write(f"Elo Equipo B: {result['elo_team_b']}\n")
        f.write(f"Resultado Quiniela: {result['result']} (Fuente: {result['fuente']})\n")
        f.write(f"Análisis: {result['analysis_url']}\n")
        f.write(f"URL Apuestas: {result['apuesta_url']}\n")
        f.write("-" * 40 + "\n")