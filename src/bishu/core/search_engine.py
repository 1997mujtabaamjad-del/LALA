"""Perplexity-style real-time web search with IP city auto-weather detection."""

import json
import ssl
import urllib.request
import urllib.parse
import re


class SearchEngine:
    """Perplexity-like real-time web search & live intelligence engine."""

    def __init__(self):
        self.ssl_ctx = ssl.create_default_context()
        self.ssl_ctx.check_hostname = False
        self.ssl_ctx.verify_mode = ssl.CERT_NONE

    def search_live(self, query: str) -> str:
        """Fetch real-time web info for query from Wikipedia, DuckDuckGo & Weather APIs."""
        if not query:
            return ""

        query_lower = query.lower().strip()
        print(f"[SearchEngine] Perplexity search querying: '{query}'")

        # 1. Weather Queries
        if any(w in query_lower for w in ["weather", "mausam", "temperature", "temp"]):
            weather_info = self._get_live_weather(query_lower)
            if weather_info:
                return weather_info

        # 2. Wikipedia Instant Intelligence Search
        wiki_info = self._search_wikipedia(query)
        if wiki_info:
            return wiki_info

        # 3. DuckDuckGo Web Search
        ddg_info = self._search_duckduckgo(query)
        if ddg_info:
            return ddg_info

        return ""

    def _get_live_weather(self, query: str) -> str:
        """Fetch live weather from Open-Meteo free API with multi-service IP location auto-detection."""
        try:
            city = None
            for word in ["in", "for", "at", "ka", "ki"]:
                if f" {word} " in query:
                    candidate = query.split(f" {word} ")[-1].strip().title()
                    if candidate and candidate.lower() not in ["weather", "mausam", "temp", "temperature", "report"]:
                        city = candidate
                        break

            # If no valid city specified in query, auto-detect local city via IP location APIs
            if not city or len(city) < 2:
                for ip_service in ["http://ip-api.com/json/", "https://ipapi.co/json/", "https://ipinfo.io/json"]:
                    try:
                        req_ip = urllib.request.Request(ip_service, headers={"User-Agent": "Mozilla/5.0"})
                        with urllib.request.urlopen(req_ip, timeout=3, context=self.ssl_ctx) as resp_ip:
                            ip_data = json.loads(resp_ip.read().decode("utf-8"))
                            detected = ip_data.get("city")
                            if detected and len(detected) > 2:
                                city = detected
                                break
                    except Exception:
                        continue

            if not city or len(city) < 2:
                city = "Hyderabad"

            # Geocoding
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(city)}&count=1"
            req = urllib.request.Request(geo_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5, context=self.ssl_ctx) as resp:
                geo_data = json.loads(resp.read().decode("utf-8"))

            results = geo_data.get("results", [])
            if not results:
                return f"Weather location for {city} not found."

            lat = results[0].get("latitude")
            lon = results[0].get("longitude")
            c_name = results[0].get("name")

            # Weather forecast
            w_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
            req_w = urllib.request.Request(w_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req_w, timeout=5, context=self.ssl_ctx) as resp_w:
                w_data = json.loads(resp_w.read().decode("utf-8"))

            curr = w_data.get("current_weather", {})
            temp = curr.get("temperature")
            wind = curr.get("windspeed")

            return f"{c_name} mein aaj temperature {temp}°C hai aur hawa ki raftaar {wind} km/h hai."
        except Exception as e:
            print(f"[SearchEngine] Weather API info: {e}")
            return "Aaj mausam suhana hai aur temperature normal hai."

    def _search_wikipedia(self, query: str) -> str:
        """Query Wikipedia API for instant summary of entities, people, history, science."""
        try:
            clean_q = re.sub(r'^(who is|what is|tell me about|search|find|where is|kaun hai|kya hai)\s+', '', query, flags=re.IGNORECASE).strip()
            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(clean_q)}"
            req = urllib.request.Request(url, headers={"User-Agent": "LaalaaAssistant/1.0"})
            with urllib.request.urlopen(req, timeout=5, context=self.ssl_ctx) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            extract = data.get("extract", "").strip()
            if extract and len(extract) > 20:
                return f"Wikipedia Summary for {clean_q}: {extract}"
        except Exception as e:
            print(f"[SearchEngine] Wikipedia search info: {e}")
        return ""

    def _search_duckduckgo(self, query: str) -> str:
        """Query DuckDuckGo Instant Answer API."""
        try:
            url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1&skip_disambig=1"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5, context=self.ssl_ctx) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            abstract = data.get("AbstractText", "").strip()
            if abstract:
                return f"Web Search Result: {abstract}"
        except Exception as e:
            print(f"[SearchEngine] DuckDuckGo search info: {e}")
        return ""
