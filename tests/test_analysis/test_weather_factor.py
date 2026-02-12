"""Test para factor de clima."""
from datetime import datetime
from src.models.match import Match, Team, MatchStatus
from src.scrapers.weather_api import WeatherCondition
from src.analysis.factors.weather import calculate_weather_impact

def test_calculate_weather_impact_no_data():
    match = Match(
        id=1, 
        home_team=Team(1, "Home"), 
        away_team=Team(2, "Away"), 
        date=datetime.now(), 
        league="Test"
    )
    result = calculate_weather_impact(match, None)
    assert result["weather_factor"] == 0.0

def test_calculate_weather_impact_heavy_rain():
    match = Match(
        id=1, 
        home_team=Team(1, "Home"), 
        away_team=Team(2, "Away"), 
        date=datetime.now(), 
        league="Test"
    )
    weather = WeatherCondition(temp=20, rain_mm=10.0, wind_speed=5.0, condition="Rain")
    result = calculate_weather_impact(match, weather)
    assert result["weather_factor"] < 0.0
    assert "rain_heavy" in result["impacts"]
