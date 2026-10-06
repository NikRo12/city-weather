"""Weather by cities: load list, query wttr.in, print per-city and per-country stats.

Usage:
    python weather.py                    # reads https://gistpad.com/raw/vk-task-14
    python weather.py cities.txt         # local file (one city per line)
    python weather.py https://...        # any URL with a list
Only the standard library is used.
"""
import json
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from urllib.parse import quote
from urllib.request import Request, urlopen

DEFAULT_SOURCE = "https://gistpad.com/raw/vk-task-14"
API = "https://wttr.in/{city}?format=j1"
HEADERS = {"User-Agent": "Mozilla/5.0 (weather-task)"}


@dataclass
class WeatherData:
    city: str
    temp_c: int
    country: str


def load_cities(source: str) -> list[str]:
    """Load the list into memory; unique cities, original order, case-insensitive."""
    if source.startswith(("http://", "https://")):
        req = Request(source, headers=HEADERS)
        with urlopen(req, timeout=20) as r:
            raw = r.read().decode("utf-8-sig")
    else:
        with open(source, encoding="utf-8-sig") as f:
            raw = f.read()

    seen, cities = set(), []
    for line in raw.splitlines():
        city = line.strip()
        if not city or city.startswith("#"):
            continue
        key = city.casefold()
        if key not in seen:
            seen.add(key)
            cities.append(city)
    return cities


def fetch_weather(city: str, retries: int = 3) -> WeatherData | None:
    url = API.format(city=quote(city))
    err: Exception | None = None
    for attempt in range(retries):
        try:
            with urlopen(Request(url, headers=HEADERS), timeout=20) as r:
                data = json.load(r)
            temp = int(float(data["current_condition"][0]["temp_C"]))
            country = data["nearest_area"][0]["country"][0]["value"]
            return WeatherData(city=city, temp_c=temp, country=country)
        except Exception as e:  # network error, bad JSON, unknown city...
            err = e
            time.sleep(1 + attempt)
    print(f"[skip] {city}: {err}", file=sys.stderr)
    return None


def fmt_temp(t: float) -> str:
    return f"{round(t):+d} °C"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    source = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SOURCE

    cities = load_cities(source)
    print(f"Unique cities: {len(cities)}\n")

    # small pool: wttr.in rate-limits aggressive clients
    with ThreadPoolExecutor(max_workers=5) as pool:
        results = [w for w in pool.map(fetch_weather, cities) if w]

    print("--- Cities ---")
    for w in results:
        print(f"{w.city}, {w.country} {fmt_temp(w.temp_c)}")

    by_country: dict[str, list[int]] = defaultdict(list)
    for w in results:
        by_country[w.country].append(w.temp_c)

    print("\n--- Countries ---")
    for country in sorted(by_country):
        temps = by_country[country]
        n = len(temps)
        print(
            f"{country} — {n} {'city' if n == 1 else 'cities'}, "
            f"avg: {fmt_temp(sum(temps) / n)}, "
            f"min: {fmt_temp(min(temps))}, "
            f"max: {fmt_temp(max(temps))}"
        )


if __name__ == "__main__":
    main()