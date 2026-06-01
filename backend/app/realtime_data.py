import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


USER_AGENT = "ms-tech-demo-router/1.0"
TIMEOUT_SECONDS = 3

WEATHER_TERMS = ("weather", "temperature", "forecast")
FINANCE_TERMS = ("stock price", "share price", "crypto price", "price of", "market price")
NEWS_EXPLICIT_TERMS = ("news", "latest", "recent", "current events", "this week")
DATE_TIME_TERMS = (
    "what date",
    "which date",
    "today's date",
    "date today",
    "what day",
    "which day",
    "what year",
    "which year",
    "current year",
    "what time",
    "current time",
)

COMPANY_TICKERS = {
    "microsoft": "MSFT",
    "apple": "AAPL",
    "nvidia": "NVDA",
    "tesla": "TSLA",
    "amazon": "AMZN",
    "google": "GOOGL",
    "alphabet": "GOOGL",
    "meta": "META",
    "openai": "MSFT",
    "bitcoin": "BTC-USD",
    "btc": "BTC-USD",
    "ethereum": "ETH-USD",
    "eth": "ETH-USD",
}

WEATHER_CODES = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "depositing rime fog",
    51: "light drizzle",
    53: "moderate drizzle",
    55: "dense drizzle",
    61: "slight rain",
    63: "moderate rain",
    65: "heavy rain",
    71: "slight snow",
    73: "moderate snow",
    75: "heavy snow",
    80: "slight rain showers",
    81: "moderate rain showers",
    82: "violent rain showers",
    95: "thunderstorm",
}

NEWS_FEEDS = (
    ("Microsoft Azure Blog", "https://azure.microsoft.com/en-us/blog/feed/"),
    ("Microsoft Azure Updates", "https://azure.microsoft.com/en-us/updates/feed/"),
    ("OpenAI News", "https://openai.com/news/rss.xml"),
)


def build_realtime_context(prompt: str) -> str:
    text = prompt.lower()
    sections = []
    wants_weather = _contains_any(text, WEATHER_TERMS)
    wants_finance = _contains_any(text, FINANCE_TERMS)
    wants_date_time = _contains_any(text, DATE_TIME_TERMS)
    wants_news = _contains_any(text, NEWS_EXPLICIT_TERMS) and not wants_weather and not wants_finance

    if wants_date_time:
        sections.append(_date_time_context())

    if wants_weather:
        weather = _safe_fetch("Weather lookup", lambda: _fetch_weather(prompt))
        if weather:
            sections.append(weather)

    if wants_finance:
        quote = _safe_fetch("Finance lookup", lambda: _fetch_quote(prompt))
        if quote:
            sections.append(quote)

    if wants_news:
        news = _safe_fetch("News lookup", lambda: _fetch_news(prompt))
        if news:
            sections.append(news)

    if not sections:
        return ""

    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return (
        f"Realtime data fetched at {fetched_at}.\n\n"
        + "\n\n".join(sections)
        + "\n\nUse this retrieved context when relevant. Mention source names and timestamps/links when available. "
        + "If the retrieved context does not fully answer the user, say what is missing instead of guessing."
    )


def direct_realtime_answer(prompt: str) -> str | None:
    text = prompt.lower()
    if not _contains_any(text, DATE_TIME_TERMS):
        return None

    now_utc = datetime.now(timezone.utc)
    now_warsaw = now_utc.astimezone(ZoneInfo("Europe/Warsaw"))

    if "year" in text:
        return (
            f"The current year is {now_warsaw.year}. "
            f"Source: backend system clock, Europe/Warsaw time, {now_warsaw:%Y-%m-%d %H:%M:%S %Z}."
        )

    if "time" in text:
        return (
            f"The current time is {now_warsaw:%H:%M:%S} in Europe/Warsaw "
            f"on {now_warsaw:%Y-%m-%d}. Source: backend system clock."
        )

    return (
        f"Today's date is {now_warsaw:%Y-%m-%d} in Europe/Warsaw "
        f"({now_utc:%Y-%m-%d} UTC). Source: backend system clock."
    )


def _date_time_context() -> str:
    now_utc = datetime.now(timezone.utc)
    now_warsaw = now_utc.astimezone(ZoneInfo("Europe/Warsaw"))
    return (
        "Date/time source: backend system clock.\n"
        f"UTC time: {now_utc:%Y-%m-%d %H:%M:%S %Z}.\n"
        f"Europe/Warsaw time: {now_warsaw:%Y-%m-%d %H:%M:%S %Z}.\n"
        f"Current year in Europe/Warsaw: {now_warsaw.year}."
    )


def _fetch_weather(prompt: str) -> str:
    location = _extract_location(prompt) or "Warsaw"
    geocode_url = "https://geocoding-api.open-meteo.com/v1/search?" + urllib.parse.urlencode(
        {"name": location, "count": 1, "language": "en", "format": "json"}
    )
    geocode = _get_json(geocode_url)
    results = geocode.get("results") or []
    if not results:
        return f"Weather lookup: no location match found for '{location}' via Open-Meteo."

    place = results[0]
    forecast_url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(
        {
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
            "timezone": "auto",
        }
    )
    forecast = _get_json(forecast_url)
    current = forecast.get("current") or {}
    units = forecast.get("current_units") or {}
    source_timezone = forecast.get("timezone", "source local timezone")
    code = current.get("weather_code")
    condition = WEATHER_CODES.get(code, f"weather code {code}") if code is not None else "unknown"
    name_parts = [place.get("name"), place.get("admin1"), place.get("country")]
    display_name = ", ".join(part for part in name_parts if part)

    return (
        "Weather source: Open-Meteo.\n"
        f"Location: {display_name}.\n"
        f"Observation time ({source_timezone}): {current.get('time', 'unknown')}.\n"
        f"Temperature: {current.get('temperature_2m')} {units.get('temperature_2m', '')}.\n"
        f"Humidity: {current.get('relative_humidity_2m')} {units.get('relative_humidity_2m', '')}.\n"
        f"Wind: {current.get('wind_speed_10m')} {units.get('wind_speed_10m', '')}.\n"
        f"Condition: {condition}."
    )


def _fetch_quote(prompt: str) -> str:
    ticker = _extract_ticker(prompt)
    if not ticker:
        return "Finance lookup: no ticker/company symbol was detected."

    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(ticker)}?range=1d&interval=1m"
    data = _get_json(url)
    result = ((data.get("chart") or {}).get("result") or [None])[0]
    if not result:
        return f"Finance lookup: no quote data returned for {ticker}."

    meta = result.get("meta") or {}
    price = meta.get("regularMarketPrice")
    previous_close = meta.get("chartPreviousClose")
    currency = meta.get("currency", "")
    market_time = meta.get("regularMarketTime")
    timestamp = (
        datetime.fromtimestamp(market_time, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        if market_time
        else "unknown"
    )
    change_text = ""
    if isinstance(price, (int, float)) and isinstance(previous_close, (int, float)):
        change = price - previous_close
        change_pct = (change / previous_close) * 100 if previous_close else 0
        change_text = f"\nChange from previous close: {change:.2f} ({change_pct:.2f}%)."

    return (
        "Finance source: Yahoo Finance chart endpoint.\n"
        f"Symbol: {meta.get('symbol', ticker)}.\n"
        f"Exchange: {meta.get('exchangeName', 'unknown')}.\n"
        f"Market time: {timestamp}.\n"
        f"Regular market price: {price} {currency}."
        f"{change_text}"
    )


def _fetch_news(prompt: str) -> str:
    keywords = _news_keywords(prompt)
    items = []

    for source_name, feed_url in NEWS_FEEDS:
        try:
            xml_text = _get_text(feed_url)
            root = ET.fromstring(xml_text)
        except Exception:
            continue

        for item in root.findall(".//item"):
            title = _clean_text(item.findtext("title"))
            link = _clean_text(item.findtext("link"))
            published = _clean_text(item.findtext("pubDate"))
            haystack = f"{title} {link}".lower()
            if keywords and not any(keyword in haystack for keyword in keywords):
                continue
            items.append(
                {
                    "source": source_name,
                    "title": title,
                    "link": link,
                    "published": published,
                }
            )
            if len(items) >= 5:
                break
        if len(items) >= 5:
            break

    if not items:
        return "News lookup: no matching RSS items found from configured Microsoft/OpenAI feeds."

    lines = ["News sources: Microsoft/OpenAI RSS feeds."]
    for index, item in enumerate(items, 1):
        lines.append(
            f"{index}. {item['title']} | {item['source']} | {item['published']} | {item['link']}"
        )
    return "\n".join(lines)


def _extract_location(prompt: str) -> str | None:
    patterns = (
        r"(?:weather|forecast|temperature)\s+(?:in|for|at)\s+([A-Za-z .'-]{2,60})",
        r"(?:in|for|at)\s+([A-Za-z .'-]{2,60})\s+(?:weather|forecast|temperature)",
    )
    for pattern in patterns:
        match = re.search(pattern, prompt, flags=re.IGNORECASE)
        if match:
            return _trim_capture(match.group(1))
    return None


def _extract_ticker(prompt: str) -> str | None:
    text = prompt.lower()
    for name, ticker in COMPANY_TICKERS.items():
        if name in text:
            return ticker

    ticker_match = re.search(r"\b[A-Z]{1,5}(?:-[A-Z]{3})?\b", prompt)
    if ticker_match:
        return ticker_match.group(0)

    quoted = re.search(r"(?:stock price|share price|price of)\s+([A-Za-z.\-]{2,20})", prompt, flags=re.IGNORECASE)
    if quoted:
        return quoted.group(1).upper()
    return None


def _news_keywords(prompt: str) -> list[str]:
    known = ("azure", "openai", "gpt", "microsoft", "ai", "foundry", "app service", "aks")
    text = prompt.lower()
    return [keyword for keyword in known if keyword in text]


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _safe_fetch(label: str, fetcher) -> str:
    try:
        return fetcher()
    except Exception as exc:
        return f"{label}: unavailable ({exc.__class__.__name__})."


def _get_json(url: str) -> dict:
    return json.loads(_get_text(url))


def _get_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return response.read().decode("utf-8", errors="replace")


def _clean_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _trim_capture(value: str) -> str:
    value = re.split(r"[?.!,;]", value, maxsplit=1)[0]
    value = re.sub(
        r"\b(today|now|right now|currently|current|this morning|this afternoon|this evening|tonight)\b",
        "",
        value,
        flags=re.IGNORECASE,
    )
    return _clean_text(value)
