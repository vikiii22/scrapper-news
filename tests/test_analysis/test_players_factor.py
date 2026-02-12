"""Test para factor de jugadores (squad)."""
from src.models.player import Player
from src.analysis.factors.players import calculate_squad_impact

def test_calculate_squad_impact():
    p1 = Player(id=1, name="P1", position="FW", team_id=1, rating=8.0)
    p2 = Player(id=2, name="P2", position="MF", team_id=2, rating=6.0)
    
    # Home missing key player (P1), Away missing regular player (P2)
    home_missing = [p1]
    away_missing = [p2]
    
    key_players_home = [p1]
    key_players_away = [] # No key players for away in this test context
    
    impact = calculate_squad_impact(
        home_missing, 
        away_missing, 
        key_players_home, 
        key_players_away
    )
    
    # Home penalty should be higher because P1 is key player
    assert impact["home_penalty"] > impact["away_penalty"]
    # Total factor = away_penalty - home_penalty  (should be negative, favoring away team)
    assert impact["players_factor"] < 0
