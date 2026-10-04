import urllib.request
import json
import os
import re
from datetime import datetime, timezone

USERNAME = "svein05"
TOKEN = os.environ.get("METRICS_TOKEN") or os.environ.get("GITHUB_TOKEN")

def get_headers():
    headers = {"User-Agent": "Mozilla/5.0"}
    if TOKEN:
        headers["Authorization"] = f"token {TOKEN}"
    return headers

def time_ago(date_str):
    now = datetime.now(timezone.utc)
    event_time = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    diff = now - event_time
    hours = diff.total_seconds() / 3600
    if hours < 1:
        return "JUST NOW"
    elif hours < 24:
        return f"{int(hours)}H AGO"
    elif hours < 48:
        return "YESTERDAY"
    else:
        days = int(hours // 24)
        return f"{days}D AGO"

def fetch_events():
    url = f"https://api.github.com/users/{USERNAME}/events?per_page=40"
    req = urllib.request.Request(url, headers=get_headers())
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def fetch_commit_msg(repo, sha):
    url = f"https://api.github.com/repos/{repo}/commits/{sha}"
    req = urllib.request.Request(url, headers=get_headers())
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["commit"]["message"].split("\n")[0]
    except Exception:
        return "Pushed commits"

def process_events(events):
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
            if len(msg) > 42:
                msg = msg[:39] + "..."
            ref = payload.get("ref", "refs/heads/main").replace("refs/heads/", "")
            
            parsed.append({
                "tag": "[PUSH]",
                "repo": repo,
                "repo_label": f"{repo_short}:{ref}",
                "repo_url": f"https://github.com/{repo}",
                "detail": f'"{msg}"',
                "sub": f'HASH: <a href="https://github.com/{repo}/commit/{head}"><code>{short_sha}</code></a> &bull; {time_tag}'
            })

        elif etype == "PullRequestEvent":
            action = payload.get("action")
            pr = payload.get("pull_request", {})
            pr_num = pr.get("number", "")
            pr_title = pr.get("title", "")
            if len(pr_title) > 42:
                pr_title = pr_title[:39] + "..."
            pr_url = pr.get("html_url", f"https://github.com/{repo}/pull/{pr_num}")
            merged = pr.get("merged", False)
            tag = "[MERGE]" if merged or action == "closed" else "[PR]"
            
            parsed.append({
                "tag": tag,
                "repo": repo,
                "repo_label": f"{repo_short}#{pr_num}",
                "repo_url": pr_url,
                "detail": f'"{pr_title}"',
                "sub": f'PR: <a href="{pr_url}"><code>#{pr_num}</code></a> &bull; {time_tag}'
            })

        elif etype == "CreateEvent":
            ref_type = payload.get("ref_type")
            ref_name = payload.get("ref") or repo_short
            if ref_type == "repository":
                tag = "[INIT]"
                detail = '"Created public repository"'
            elif ref_type == "tag":
                tag = "[TAG]"
                detail = f'"Created tag {ref_name}"'
            else:
                tag = "[BRANCH]"
                detail = f'"Created branch {ref_name}"'

            parsed.append({
                "tag": tag,
                "repo": repo,
                "repo_label": repo_short,
                "repo_url": f"https://github.com/{repo}",
                "detail": detail,
                "sub": f'REF: <code>{ref_name}</code> &bull; {time_tag}'
            })

        elif etype == "ReleaseEvent":
            release = payload.get("release", {})
            tag_name = release.get("tag_name", "")
            name = release.get("name") or tag_name
            if len(name) > 42:
                name = name[:39] + "..."
            rel_url = release.get("html_url", f"https://github.com/{repo}/releases")

            parsed.append({
                "tag": "[RELEASE]",
                "repo": repo,
                "repo_label": f"{repo_short} {tag_name}",
                "repo_url": rel_url,
                "detail": f'"{name}"',
                "sub": f'TAG: <code>{tag_name}</code> &bull; {time_tag}'
            })

    return parsed

def render_table(items):
    # We want 3 rows of 2 columns:
    # Row 0: item 0, item 3
    # Row 1: item 1, item 4
    # Row 2: item 2, item 5
    if len(items) < 6:
        # pad if needed
        while len(items) < 6:
            items.append({
                "tag": "[IDLE]",
                "repo_label": "standby",
                "repo_url": "#",
                "detail": '"Awaiting next deploy"',
                "sub": "STATUS: <code>READY</code> • NOW"
            })

    rows = [
        (items[0], items[3]),
        (items[1], items[4]),
        (items[2], items[5]),
    ]

    html = ['<table width="100%">']
    for left, right in rows:
        html.append("  <tr>")
        html.append(f'    <td width="50%" valign="top">')
        html.append(f'      <b>{left["tag"]}</b> <a href="{left["repo_url"]}"><code>{left["repo_label"]}</code></a><br>')
        html.append(f'      <i>{left["detail"]}</i><br>')
        html.append(f'      <sub>{left["sub"]}</sub>')
        html.append(f'    </td>')
        html.append(f'    <td width="50%" valign="top">')
        html.append(f'      <b>{right["tag"]}</b> <a href="{right["repo_url"]}"><code>{right["repo_label"]}</code></a><br>')
        html.append(f'      <i>{right["detail"]}</i><br>')
        html.append(f'      <sub>{right["sub"]}</sub>')
        html.append(f'    </td>')
        html.append("  </tr>")
    html.append("</table>")
    return "\n".join(html)

def update_readme(table_html, readme_path="README.md"):
    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = r"<!-- START_ACTIVITY -->.*?<!-- END_ACTIVITY -->"
    replacement = f"<!-- START_ACTIVITY -->\n{table_html}\n<!-- END_ACTIVITY -->"
    if "<!-- START_ACTIVITY -->" in content:
        new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    else:
        # inject above stats widgets inside ## 📊 Github Stats
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
    table = render_table(items)
    print("Generated Table:\n", table)
    update_readme(table, "README.md")
