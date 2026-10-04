import urllib.request
import json
import os
import re
import html
from datetime import datetime, timezone

USERNAME = "svein05"

ICONS = {
    "git": '<path d="M13.09 23.549a1.54 1.54 0 0 1-2.18 0L.451 13.089a1.54 1.54 0 0 1 0-2.179l7.191-7.19 2.733 2.733a1.85 1.85 0 0 0 .964 2.326v6.66a1.849 1.849 0 1 0 1.54 0V8.957l2.508 2.508a1.85 1.85 0 1 0 1.09-1.09l-2.634-2.634a1.85 1.85 0 0 0-2.378-2.377L8.73 2.63 10.91.451a1.54 1.54 0 0 1 2.179 0l10.459 10.46a1.54 1.54 0 0 1 0 2.179z" fill="#ffffff"/>',
    "commit": '<path fill-rule="evenodd" d="M10.5 7.75a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0zm1.43.75a4.002 4.002 0 01-7.86 0H.75a.75.75 0 110-1.5h3.32a4.002 4.002 0 017.86 0h3.32a.75.75 0 110 1.5h-3.32z" fill="#ffffff"/>',
    "merge": '<path fill-rule="evenodd" d="M5 3.254V3.25v.004a2.25 2.25 0 11-1.5 2.118v5.256a2.251 2.251 0 101.5 0V7.71a4.267 4.267 0 002.5 1.04v.878a2.25 2.25 0 101.5 0v-4.13a2.25 2.25 0 10-1.5 0v1.752a2.766 2.766 0 01-2.5-.996V5.372A2.25 2.25 0 015 3.254zM3.75 2.5a.75.75 0 100 1.5.75.75 0 000-1.5zm0 9.5a.75.75 0 100 1.5.75.75 0 000-1.5zm5.5-5a.75.75 0 100 1.5.75.75 0 000-1.5zm0-4.5a.75.75 0 100 1.5.75.75 0 000-1.5z" fill="#ffffff"/>',
    "pr": '<path fill-rule="evenodd" d="M7.177 3.073L9.573.677A.25.25 0 0110 .854v4.792a.25.25 0 01-.427.177L7.177 3.427a.25.25 0 010-.354zM3.75 2.5a.75.75 0 100 1.5.75.75 0 000-1.5zm-2.25.75a2.25 2.25 0 113 2.122v5.256a2.251 2.251 0 11-1.5 0V5.372A2.25 2.25 0 011.5 3.25zM11 2.5h-1V4h1a1 1 0 011 1v5.628a2.251 2.251 0 101.5 0V5A2.5 2.5 0 0011 2.5zm1 10.25a.75.75 0 111.5 0 .75.75 0 01-1.5 0zM3.75 12a.75.75 0 100 1.5.75.75 0 000-1.5z" fill="#ffffff"/>',
    "repo": '<path fill-rule="evenodd" d="M2 2.5A2.5 2.5 0 014.5 0h8.75a.75.75 0 01.75.75v12.5a.75.75 0 01-.75.75h-2.5a.75.75 0 110-1.5h1.75v-2h-8a1 1 0 00-.714 1.7.75.75 0 01-1.072 1.05A2.495 2.495 0 012 11.5v-9zm10.5-1V9h-8c-.356 0-.694.074-1 .208V2.5a1 1 0 011-1h8zM5 12.25v3.25a.25.25 0 00.4.2l1.45-1.087a.25.25 0 01.3 0L8.6 15.7a.25.25 0 00.4-.2v-3.25a.25.25 0 00-.25-.25h-3.5a.25.25 0 00-.25.25z" fill="#ffffff"/>',
    "branch": '<path fill-rule="evenodd" d="M11.75 2.5a.75.75 0 100 1.5.75.75 0 000-1.5zm-2.25.75a2.25 2.25 0 113 2.122V6A2.5 2.5 0 0110 8.5H6a1 1 0 00-1 1v1.128a2.251 2.251 0 11-1.5 0V5.372a2.25 2.25 0 111.5 0v1.836A2.492 2.492 0 016 7h4a1 1 0 001-1v-.628A2.25 2.25 0 019.5 3.25zM4.25 12a.75.75 0 100 1.5.75.75 0 000-1.5zM3.5 3.25a.75.75 0 111.5 0 .75.75 0 01-1.5 0z" fill="#ffffff"/>',
    "tag": '<path fill-rule="evenodd" d="M2.5 7.775V2.75a.25.25 0 01.25-.25h5.025a.25.25 0 01.177.073l6.25 6.25a.25.25 0 010 .354l-5.025 5.025a.25.25 0 01-.354 0l-6.25-6.25a.25.25 0 01-.073-.177zm-1.5 0V2.75C1 1.784 1.784 1 2.75 1h5.025c.464 0 .91.184 1.238.513l6.25 6.25a1.75 1.75 0 010 2.474l-5.026 5.026a1.75 1.75 0 01-2.474 0l-6.25-6.25A1.75 1.75 0 011 7.775zM6 5a1 1 0 100 2 1 1 0 000-2z" fill="#ffffff"/>',
    "fork": '<path fill-rule="evenodd" d="M5 3.25a.75.75 0 11-1.5 0 .75.75 0 011.5 0zm0 2.122a2.25 2.25 0 10-1.5 0v.878A2.25 2.25 0 005.75 8.5h4.5A2.25 2.25 0 0012.5 6.25v-.878a2.25 2.25 0 10-1.5 0V6.25a.75.75 0 01-.75.75h-4.5a.75.75 0 01-.75-.75v-.878zM12.5 3.25a.75.75 0 11-1.5 0 .75.75 0 011.5 0zM8.75 12.75a.75.75 0 100 1.5.75.75 0 000-1.5zM8 11.25a2.25 2.25 0 101.5 2.122V10.25a3.75 3.75 0 00-.75-2.25H7.25a3.75 3.75 0 00-.75 2.25v3.122A2.25 2.25 0 008 11.25z" fill="#ffffff"/>',
}

def get_token():
    token = os.environ.get("METRICS_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    try:
        import subprocess
        p = subprocess.run(
            ["git", "credential", "fill"],
            input="protocol=https\nhost=github.com\n",
            capture_output=True, text=True, check=True
        )
        for line in p.stdout.splitlines():
            if line.startswith("password="):
                return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return None

TOKEN = get_token()

def get_headers():
    headers = {"User-Agent": "Mozilla/5.0"}
    if TOKEN:
        headers["Authorization"] = f"token {TOKEN}"
    return headers

def time_ago(date_str):
    now = datetime.now(timezone.utc)
    event_time = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    diff = now - event_time
    seconds = diff.total_seconds()
    minutes = int(seconds // 60)
    hours = int(seconds // 3600)
    days = int(seconds // 86400)

    if minutes < 2:
        return "JUST NOW"
    elif minutes < 60:
        return f"{minutes}M AGO"
    elif hours < 24:
        return f"{hours}H AGO"
    elif hours < 48:
        return "YESTERDAY"
    else:
        return f"{days}D AGO"

def fetch_events():
    url = f"https://api.github.com/users/{USERNAME}/events?per_page=40"
    req = urllib.request.Request(url, headers=get_headers())
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as err:
        print(f"Warning: Could not fetch from GitHub API ({err}), will use fallback.")
        return []

def fetch_commit_msg(repo, sha):
    url = f"https://api.github.com/repos/{repo}/commits/{sha}"
    req = urllib.request.Request(url, headers=get_headers())
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["commit"]["message"].split("\n")[0]
    except Exception:
        return "Pushed commits"

def fallback_from_git():
    import subprocess
    try:
        res = subprocess.run(
            ["git", "log", "-n", "6", "--pretty=format:%h|%s|%ct"],
            capture_output=True, text=True, check=True
        )
        items = []
        now = datetime.now(timezone.utc).timestamp()
        for line in res.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("|")
            if len(parts) >= 3:
                sha, msg, ts = parts[0], parts[1], int(parts[2])
                hours = (now - ts) / 3600
                if hours < 1:
                    time_tag = "JUST NOW"
                elif hours < 24:
                    time_tag = f"{int(hours)}H AGO"
                elif hours < 48:
                    time_tag = "YESTERDAY"
                else:
                    time_tag = f"{int(hours // 24)}D AGO"
                items.append({
                    "icon_type": "commit",
                    "action": "Push",
                    "repo_label": "Svein05:main",
                    "detail": msg,
                    "sub": time_tag
                })
        return items
    except Exception as e:
        print(f"Git fallback error: {e}")
        return []

def process_events(events):
    if not events:
        return fallback_from_git()

    events.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    parsed = []
    seen = set()

    for e in events:
        if len(parsed) >= 6:
            break

        etype = e["type"]
        repo = e["repo"]["name"]
        repo_short = repo.split("/")[-1]
        created_at = e["created_at"]
        time_tag = time_ago(created_at)
        payload = e.get("payload", {})

        if etype == "PushEvent":
            head = payload.get("head")
            if not head:
                continue
            short_sha = head[:7]
            unique_key = (repo, short_sha)
            if unique_key in seen:
                continue
            seen.add(unique_key)
            msg = fetch_commit_msg(repo, head)
            ref = payload.get("ref", "refs/heads/main").replace("refs/heads/", "")
            
            parsed.append({
                "icon_type": "commit",
                "action": "Push",
                "repo_label": f"{repo_short}:{ref}",
                "detail": msg,
                "sub": time_tag
            })

        elif etype == "PullRequestEvent":
            action = payload.get("action")
            pr = payload.get("pull_request", {})
            pr_num = pr.get("number", "")
            pr_title = pr.get("title", "")
            merged = pr.get("merged", False)
            if merged or action == "closed":
                icon_type = "merge"
                act_name = "Merge"
            else:
                icon_type = "pr"
                act_name = "PR"
            
            parsed.append({
                "icon_type": icon_type,
                "action": act_name,
                "repo_label": f"{repo_short}#{pr_num}",
                "detail": pr_title,
                "sub": time_tag
            })

        elif etype == "CreateEvent":
            ref_type = payload.get("ref_type")
            ref_name = payload.get("ref") or repo_short
            if ref_type == "repository":
                icon_type = "repo"
                act_name = "New Repo"
                detail = "Created public repository"
            elif ref_type == "tag":
                icon_type = "tag"
                act_name = "Tag"
                detail = f"Tag {ref_name}"
            else:
                icon_type = "branch"
                act_name = "Branch"
                detail = f"Branch {ref_name}"

            parsed.append({
                "icon_type": icon_type,
                "action": act_name,
                "repo_label": repo_short,
                "detail": detail,
                "sub": time_tag
            })

        elif etype == "ReleaseEvent":
            release = payload.get("release", {})
            tag_name = release.get("tag_name", "")
            name = release.get("name") or tag_name

            parsed.append({
                "icon_type": "tag",
                "action": "Release",
                "repo_label": f"{repo_short} {tag_name}",
                "detail": name,
                "sub": time_tag
            })

        elif etype == "ForkEvent":
            forkee = payload.get("forkee", {})
            fork_name = forkee.get("name") or repo_short

            parsed.append({
                "icon_type": "fork",
                "action": "Fork",
                "repo_label": repo_short,
                "detail": f"Forked repository",
                "sub": time_tag
            })

    return parsed

def generate_svg(items, output_path="assets/git-activity.svg"):
    # Ensure 6 items
    while len(items) < 6:
        items.append({
            "icon_type": "commit",
            "action": "Idle",
            "repo_label": "standby",
            "detail": "Awaiting next deploy",
            "sub": "READY"
        })

    # 3 rows x 2 cols (col 0: 0, 1, 2; col 1: 3, 4, 5)
    cols = [
        [items[0], items[1], items[2]],
        [items[3], items[4], items[5]]
    ]

    width = 840
    height = 230
    
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" fill="none">',
        '  <style>',
        '    .title { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; font-size: 15px; font-weight: 600; fill: #ffffff; letter-spacing: 0.5px; }',
        '    .action { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; font-size: 13px; font-weight: 600; fill: #ffffff; }',
        '    .badge { font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace; font-size: 10.5px; fill: #58a6ff; font-weight: 500; }',
        '    .time { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; font-size: 10px; font-weight: 600; fill: #8b949e; }',
        '    .detail { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; font-size: 12px; font-style: italic; fill: #c9d1d9; }',
        '  </style>',
        f'  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="6" fill="#000000" stroke="#ffffff" stroke-width="1" />',
        '',
        '  <!-- Header -->',
        f'  <svg x="326" y="15" width="16" height="16" viewBox="0 0 24 24">{ICONS["git"]}</svg>',
        '  <text x="424" y="29" text-anchor="middle" class="title">Recent Git Activity</text>',
        '  <line x1="20" y1="45" x2="820" y2="45" stroke="#21262d" stroke-width="1" />',
        '',
        '  <!-- Middle Vertical Divider -->',
        '  <line x1="420" y1="45" x2="420" y2="220" stroke="#21262d" stroke-width="1" />',
        '',
        '  <!-- Horizontal Row Dividers -->',
        '  <line x1="25" y1="103" x2="405" y2="103" stroke="#161b22" stroke-width="1" />',
        '  <line x1="435" y1="103" x2="815" y2="103" stroke="#161b22" stroke-width="1" />',
        '  <line x1="25" y1="161" x2="405" y2="161" stroke="#161b22" stroke-width="1" />',
        '  <line x1="435" y1="161" x2="815" y2="161" stroke="#161b22" stroke-width="1" />',
    ]

    row_y_top = [73, 131, 189]
    row_y_bot = [91, 149, 207]

    col_config = [
        {"x_start": 35, "x_time": 405},
        {"x_start": 445, "x_time": 805}
    ]

    for col_idx in range(2):
        cfg = col_config[col_idx]
        x_start = cfg["x_start"]
        x_time = cfg["x_time"]

        for row_idx in range(3):
            item = cols[col_idx][row_idx]
            y_top = row_y_top[row_idx]
            y_bot = row_y_bot[row_idx]

            icon_path = ICONS.get(item["icon_type"], ICONS["commit"])
            action = html.escape(item["action"])
            repo_label = html.escape(item["repo_label"])
            time_tag = html.escape(item["sub"])

            detail = item["detail"]
            if len(detail) > 46:
                detail = detail[:43].strip() + "..."
            detail_escaped = html.escape(f'"{detail}"')

            # Dynamic pill positioning
            action_width = len(action) * 7.5 + 4
            x_action = x_start + 22
            x_pill = x_action + action_width + 6
            pill_width = len(repo_label) * 6.5 + 12

            lines.append(f'  <!-- Item Col {col_idx} Row {row_idx} -->')
            lines.append(f'  <svg x="{x_start}" y="{y_top - 12}" width="14" height="14" viewBox="0 0 16 16">{icon_path}</svg>')
            lines.append(f'  <text x="{x_action}" y="{y_top}" class="action">{action}</text>')
            lines.append(f'  <rect x="{x_pill}" y="{y_top - 11}" width="{pill_width:.1f}" height="16" rx="4" fill="#161b22" stroke="#30363d" stroke-width="1" />')
            lines.append(f'  <text x="{x_pill + pill_width/2:.1f}" y="{y_top + 1}" text-anchor="middle" class="badge">{repo_label}</text>')
            lines.append(f'  <text x="{x_time}" y="{y_top}" text-anchor="end" class="time">{time_tag}</text>')
            lines.append(f'  <text x="{x_action}" y="{y_bot}" class="detail">{detail_escaped}</text>')

    lines.append('</svg>')

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"SVG generated successfully at {output_path}!")

def update_readme(svg_rel_path="assets/git-activity.svg", readme_path="README.md"):
    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()

    replacement = (
        '<!-- START_ACTIVITY -->\n'
        '<p align="center">\n'
        '  <img src="https://raw.githubusercontent.com/Svein05/Svein05/main/assets/git-activity.svg" alt="Recent Git Activity" />\n'
        '</p>\n'
        '<!-- END_ACTIVITY -->'
    )

    pattern = r"<!-- START_ACTIVITY -->.*?<!-- END_ACTIVITY -->"
    if "<!-- START_ACTIVITY -->" in content:
        new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    else:
        target = "## 📊 Github Stats"
        if target in content:
            new_content = content.replace(target, f"{target}\n{replacement}")
        else:
            new_content = content + f"\n\n{replacement}\n"

    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("README.md updated successfully!")

if __name__ == "__main__":
    print("Fetching GitHub activity...")
    events = fetch_events()
    items = process_events(events)
    print(f"Processed {len(items)} items")
    generate_svg(items, "assets/git-activity.svg")
    update_readme("assets/git-activity.svg", "README.md")
