#!/usr/bin/env python3
"""Monitor StubHub's publicly visible all-in price for Ed Sheeran at Levi's Stadium."""
import html
import json
import os
import re
import sys
import urllib.request

EVENT_URL = "https://www.stubhub.com/ed-sheeran-santa-clara-tickets-7-25-2026/event/159434958"
THRESHOLD = float(os.getenv("PRICE_THRESHOLD", "150"))
BLOCKED_VIEW = re.compile(r"(obstructed|limited|restricted|side view|partial view)", re.I)

request = urllib.request.Request(
    EVENT_URL,
    headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 Chrome/126 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    },
)
try:
    with urllib.request.urlopen(request, timeout=30) as response:
        page = response.read().decode("utf-8", "replace")
except Exception as exc:
    print(f"ERROR: StubHub request failed: {exc}", file=sys.stderr)
    sys.exit(2)

text = html.unescape(page.replace("\\u0024", "$").replace("\\/", "/"))
patterns = [
    re.compile(r"\$\s*([0-9][0-9,]*(?:\.\d{1,2})?)\s*(?:incl\.?|including)\s+fees", re.I),
    re.compile(r"(?:incl\.?|including)\s+fees.{0,100}?\$\s*([0-9][0-9,]*(?:\.\d{1,2})?)", re.I | re.S),
]
candidates = []
for pattern in patterns:
    for match in pattern.finditer(text):
        start, end = max(0, match.start() - 350), min(len(text), match.end() + 350)
        context = re.sub(r"\s+", " ", text[start:end])
        if BLOCKED_VIEW.search(context):
            continue
        candidates.append(float(match.group(1).replace(",", "")))

if not candidates:
    # A red workflow is intentional: it prevents a false "working" signal when the site blocks parsing.
    print("ERROR: No non-obstructed 'fees included' price could be parsed.", file=sys.stderr)
    sys.exit(2)

lowest = min(candidates)
result = {
    "event": "Ed Sheeran: LOOP Tour — Levi's Stadium — 2026-07-25",
    "quantity": 1,
    "lowest_all_in_price": lowest,
    "threshold": THRESHOLD,
    "url": EVENT_URL,
    "eligible": lowest <= THRESHOLD,
}
print(json.dumps(result, ensure_ascii=False))
with open(os.environ.get("GITHUB_OUTPUT_FILE", "ticket-result.json"), "w", encoding="utf-8") as fh:
    json.dump(result, fh)

sys.exit(0 if lowest <= THRESHOLD else 1)
