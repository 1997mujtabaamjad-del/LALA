"""
Spoken weather via Open-Meteo (free, no API key) with a wttr.in IP fallback
for “weather” without a city.
"""

import requests

WMO = {
    0: "clear skies", 1: "mostly clear", 2: "partly cloudy", 3: "overcast",
    45: "foggy", 48: "foggy",
    51: "light drizzle", 53: "drizzle", 55: "heavy drizzle",
    61: "light rain", 63: "rain", 65: "heavy rain", 66: "freezing rain", 67: "freezing rain",
    71: "light snow", 73: "snow", 75: "heavy snow", 77: "snow grains",
    80: "rain showers", 81: "rain showers", 82: "violent showers",
    85: "snow showers", 86: "snow showers",
    95: "thunderstorms", 96: "thunderstorms with hail", 99: "thunderstorms with hail",
}


def describe(code):
    return WMO.get(int(code), "cloudy")


def geocode(city):
    r = requests.get("https://geocoding-api.open-meteo.com/v1/search",
                     params={"name": city, "count": 1}, timeout=10)
    r.raise_for_status()
    results = r.json().get("results")
    if not results:
        return None
    g = results[0]
    return g["latitude"], g["longitude"], g.get("name", city)


def current_for_city(city=""):
    """One speakable sentence, or None when offline/unknown."""
    city = (city or "").strip()
    if not city:
        try:  # IP-based location
            r = requests.get("https://wttr.in/?format=j1", timeout=10)
            j = r.json()
            cur = j["current_condition"][0]
            place = j["nearest_area"][0]["areaName"][0]["value"]
            return (f"It's {cur['temp_C']}°C in {place}, "
                    f"{cur['weatherDesc'][0]['value'].lower()}, humidity {cur['humidity']}%.")
        except Exception:  # noqa: BLE001
            return None
    try:
        g = geocode(city)
        if not g:
            return None
        lat, lon, name = g
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={"latitude": lat, "longitude": lon,
                    "current": "temperature_2m,relative_humidity_2m,apparent_temperature,"
                               "weather_code,wind_speed_10m"},
            timeout=10,
        )
        r.raise_for_status()
        c = r.json()["current"]
        return (f"It's {round(c['temperature_2m'])}°C in {name}, {describe(c['weather_code'])}, "
                f"feels like {round(c['apparent_temperature'])}°, "
                f"wind {round(c['wind_speed_10m'])} km/h, humidity {c['relative_humidity_2m']}%.")
    except Exception:  # noqa: BLE001
        return None
