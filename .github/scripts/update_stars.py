"""Generate the monthly profile chart from public repository stars and daily snapshots."""
import calendar
import html
import json
import os
from pathlib import Path
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
HISTORY = ROOT / "assets/data/stars-history.json"
OUTPUT = ROOT / "assets/svg/stargazers.svg"
MONTHS = ("", "January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December")
TIMEZONE = ZoneInfo("America/Santiago")


def get_token():
    token = os.environ.get("METRICS_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    return None


def pages(path, token, accept="application/vnd.github+json"):
    """Fetch every page. Fail without publishing a partial chart on any API error."""
    result = []
    for page in range(1, 10001):
        separator = "&" if "?" in path else "?"
        request = urllib.request.Request(
            f"https://api.github.com{path}{separator}per_page=100&page={page}",
            headers={"User-Agent": "Svein05-profile-stars", "Accept": accept,
                     **({"Authorization": f"Bearer {token}"} if token else {})},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            batch = json.load(response)
        if not isinstance(batch, list):
            raise ValueError("Unexpected GitHub API response")
        result.extend(batch)
        if len(batch) < 100:
            return result
    raise ValueError("Pagination limit exceeded")


def fetch_stars(username, token):
    repos = pages(f"/users/{username}/repos?type=owner&sort=full_name", token)
    repos = [r for r in repos if not r["private"]]
    events = []
    counts = {}
    for repo in repos:
        name = repo["name"]
        stars = pages(f'/repos/{repo["full_name"]}/stargazers', token,
                      "application/vnd.github.star+json") if repo["stargazers_count"] else []
        # Use one consistent source for counts and dates, even if stars change mid-fetch.
        counts[name] = len(stars)
        for star in stars:
            date = datetime.fromisoformat(star["starred_at"].replace("Z", "+00:00"))
            events.append((date.astimezone(TIMEZONE), name))
    return counts, sorted(events)


def build_month(history, counts, events, now):
    """Bootstrap from surviving stars, then preserve observed daily totals and baselines."""
    today = now.date()
    start = today.replace(day=1)
    month = start.strftime("%Y-%m")
    months = history.setdefault("months", {})
    total = sum(counts.values())
    gains = {}
    for date, _ in events:
        if start <= date.date() <= today:
            key = date.date().isoformat()
            gains[key] = gains.get(key, 0) + 1
    if month not in months:
        # Prefer an actual observation on the last day of the preceding month.
        previous_day = start - timedelta(days=1)
        previous = months.get(previous_day.strftime("%Y-%m"), {})
        observed_close = previous.get("days", {}).get(previous_day.isoformat())
        baseline = observed_close if observed_close is not None else total - sum(gains.values())
        months[month] = {"baseline": baseline, "days": {}, "observed": []}
    record = months[month]
    running = record["baseline"]
    observed = set(record["observed"])
    for day in range(1, today.day + 1):
        key = start.replace(day=day).isoformat()
        if key in observed:
            running = record["days"][key]
        else:
            running += gains.get(key, 0)
            record["days"][key] = running
    record["days"][today.isoformat()] = total
    record["observed"] = sorted(observed | {today.isoformat()})
    history["updated_at"] = now.isoformat()
    most = min(counts, key=lambda name: (-counts[name], name)) if total else "—"
    latest = events[-1][1] if events else "—"
    return record, most, latest


def integer_ticks(low, high):
    if low == high:
        return [low]
    # Keep exact endpoints with up to five distinct integer ticks.
    return sorted({low + (high - low) * i // 4 for i in range(5)})


def chart_svg(record, most, latest, now):
    # Match the approved 736px preview's logical dimensions, then render at 840px.
    # This preserves its typography and proportions when embedded in the README.
    width, height = 736, 360
    left, right, top, bottom = 56, 696, 138, 304
    baseline = record["baseline"]
    daily = sorted((int(date[-2:]), value) for date, value in record["days"].items())
    total = daily[-1][1]
    # Normally baseline..current. Preserve truthful history if stars were removed.
    low = min(baseline, *(value for _, value in daily))
    high = max(baseline, *(value for _, value in daily))
    left = max(left, 28 + len(str(high)) * 8)
    last_day = calendar.monthrange(now.year, now.month)[1]
    x = lambda day: left + (day - 1) * (right - left) / (last_day - 1)
    y = lambda value: (top + bottom) / 2 if high == low else bottom - (value - low) * (bottom - top) / (high - low)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="840" height="411" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
           f'<title id="title">Stargazers - {MONTHS[now.month]}</title>',
           f'<desc id="desc">{total} total stars. Daily cumulative stars in {MONTHS[now.month]} {now.year}, starting at {baseline}. Updated {now.date()} in America/Santiago.</desc>',
           '<style>text{font-family:"Segoe UI",sans-serif;fill:#eee}.meta{font-size:13px}.axis,.delta{font-family:Consolas,monospace;font-size:12px;fill:#aaa}.delta{fill:#fff;font-weight:600}</style>',
           '<rect x=".5" y=".5" width="735" height="359" rx="9" fill="#000" stroke="#444"/>',
           f'<text x="24" y="49" font-size="17" font-weight="600">Stargazers - {MONTHS[now.month]}</text>',
           f'<text x="700" y="52" text-anchor="end" font-weight="600"><tspan font-size="36">☆</tspan><tspan dx="9" font-size="30">{total}</tspan></text>']
    # Native inline text flow reproduces the preview's 24px gap, rather than
    # spreading the two summaries into separate fixed columns.
    def short_name(name):
        return html.escape(name if len(name) <= 28 else name[:27] + "…")

    out.append(f'<text x="24" y="92" class="meta"><title>{html.escape(f"Most starred: {most}; Latest starred: {latest}")}</title>'
               f'<tspan fill="#999">Most starred:</tspan> {short_name(most)}'
               f'<tspan dx="24" fill="#999">Latest starred:</tspan> {short_name(latest)}</text>')
    for tick in integer_ticks(low, high):
        yy = y(tick)
        out.extend([f'<line x1="{left}" y1="{yy:.2f}" x2="{right}" y2="{yy:.2f}" stroke="#222"/>',
                    f'<text x="{left - 14}" y="{yy + 4:.2f}" text-anchor="end" class="axis">{tick}</text>'])
    points = [(1, baseline)] + daily
    path = " ".join(f'{"M" if i == 0 else "L"}{x(day):.2f},{y(value):.2f}' for i, (day, value) in enumerate(points))
    out.append(f'<path d="{path} L{x(daily[-1][0]):.2f},{bottom} L{left},{bottom} Z" fill="#fff" opacity=".035"/>')
    out.append(f'<path d="{path}" fill="none" stroke="#eee" stroke-width="2" stroke-linejoin="round"/>')
    previous = baseline
    changed_days = []
    for day, value in daily:
        delta = value - previous
        previous = value
        if not delta:
            continue
        changed_days.append(day)
        px, py = x(day), y(value)
        out.extend([f'<line x1="{px:.2f}" y1="{py + 7:.2f}" x2="{px:.2f}" y2="{bottom + 6}" stroke="#333" stroke-dasharray="2 4"/>',
                    f'<circle cx="{px:.2f}" cy="{py:.2f}" r="4" fill="#000" stroke="#fff" stroke-width="2"><title>{MONTHS[now.month]} {day}: {delta:+d}; {value} total stars</title></circle>',
                    f'<text x="{px:.2f}" y="{py - 14:.2f}" text-anchor="middle" class="delta">{delta:+d}</text>',
                    f'<text x="{px:.2f}" y="{bottom + 25}" text-anchor="middle" class="axis">{day:02d}</text>'])
    if not changed_days:
        out.append(f'<text x="{left}" y="{bottom + 25}" class="axis">No changes this month</text>')
    out.append('</svg>')
    return "\n".join(out) + "\n"


def main():
    now = datetime.now(TIMEZONE)
    username = os.environ.get("PROFILE_USERNAME", "Svein05")
    counts, events = fetch_stars(username, get_token())
    history = json.loads(HISTORY.read_text(encoding="utf-8")) if HISTORY.exists() else {"version": 1, "months": {}}
    record, most, latest = build_month(history, counts, events, now)
    svg = chart_svg(record, most, latest, now)
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(svg, encoding="utf-8")
    HISTORY.write_text(json.dumps(history, indent=2) + "\n", encoding="utf-8")
    print(f"Updated monthly stargazers: {sum(counts.values())} stars across {len(counts)} public repositories")


if __name__ == "__main__":
    main()
