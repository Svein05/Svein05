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
            # Strictly limit to 30 chars so it NEVER wraps onto 2 lines
            if len(msg) > 30:
                msg = msg[:27].strip() + "..."
            ref = payload.get("ref", "refs/heads/main").replace("refs/heads/", "")
            commit_url = f"https://github.com/{repo}/commit/{head}"
            icon_url = "https://api.iconify.design/octicon/git-commit-16.svg?color=white"
            
            parsed.append({
                "icon_html": f'<img src="{icon_url}" width="14" height="14" valign="middle" alt="commit" />',
                "action": "Push",
                "repo_label": f"{repo_short}:{ref}",
                "repo_url": f"https://github.com/{repo}/tree/{ref}",
                "detail_html": f'<a href="{commit_url}"><i>"{msg}"</i></a>',
                "sub": time_tag
            })

        elif etype == "PullRequestEvent":
            action = payload.get("action")
            pr = payload.get("pull_request", {})
            pr_num = pr.get("number", "")
            pr_title = pr.get("title", "")
            if len(pr_title) > 30:
                pr_title = pr_title[:27].strip() + "..."
            pr_url = pr.get("html_url", f"https://github.com/{repo}/pull/{pr_num}")
            merged = pr.get("merged", False)
            if merged or action == "closed":
                icon_url = "https://api.iconify.design/octicon/git-merge-16.svg?color=white"
                act_name = "Merge"
            else:
                icon_url = "https://api.iconify.design/octicon/git-pull-request-16.svg?color=white"
                act_name = "PR"
            
            parsed.append({
                "icon_html": f'<img src="{icon_url}" width="14" height="14" valign="middle" alt="{act_name}" />',
                "action": act_name,
                "repo_label": f"{repo_short}#{pr_num}",
                "repo_url": pr_url,
                "detail_html": f'<a href="{pr_url}"><i>"{pr_title}"</i></a>',
                "sub": time_tag
            })

        elif etype == "CreateEvent":
            ref_type = payload.get("ref_type")
            ref_name = payload.get("ref") or repo_short
            if ref_type == "repository":
                icon_url = "https://api.iconify.design/octicon/repo-16.svg?color=white"
                act_name = "New Repo"
                detail = '"Created public repo"'
                link = f"https://github.com/{repo}"
            elif ref_type == "tag":
                icon_url = "https://api.iconify.design/octicon/tag-16.svg?color=white"
                act_name = "Tag"
                detail = f'"Tag {ref_name}"'
                link = f"https://github.com/{repo}/releases/tag/{ref_name}"
            else:
                icon_url = "https://api.iconify.design/octicon/git-branch-16.svg?color=white"
                act_name = "Branch"
                detail = f'"Branch {ref_name}"'
                link = f"https://github.com/{repo}/tree/{ref_name}"

            if len(detail) > 30:
                detail = detail[:27].strip() + '..."'

            parsed.append({
                "icon_html": f'<img src="{icon_url}" width="14" height="14" valign="middle" alt="{act_name}" />',
                "action": act_name,
                "repo_label": repo_short,
                "repo_url": f"https://github.com/{repo}",
                "detail_html": f'<a href="{link}"><i>{detail}</i></a>',
                "sub": time_tag
            })

        elif etype == "ReleaseEvent":
            release = payload.get("release", {})
            tag_name = release.get("tag_name", "")
            name = release.get("name") or tag_name
            if len(name) > 30:
                name = name[:27].strip() + "..."
            rel_url = release.get("html_url", f"https://github.com/{repo}/releases")
            icon_url = "https://api.iconify.design/octicon/tag-16.svg?color=white"

            parsed.append({
                "icon_html": f'<img src="{icon_url}" width="14" height="14" valign="middle" alt="release" />',
                "action": "Release",
                "repo_label": f"{repo_short} {tag_name}",
                "repo_url": rel_url,
                "detail_html": f'<a href="{rel_url}"><i>"{name}"</i></a>',
                "sub": time_tag
            })

    return parsed

def render_table(items):
    # 3 rows x 2 columns:
    # Row 0: item 0, item 3
    # Row 1: item 1, item 4
    # Row 2: item 2, item 5
    if len(items) < 6:
        while len(items) < 6:
            items.append({
                "icon_html": '<img src="https://api.iconify.design/octicon/git-commit-16.svg?color=white" width="14" height="14" valign="middle" alt="commit" />',
                "action": "Idle",
                "repo_label": "standby",
                "repo_url": "#",
                "detail_html": '<i>"Awaiting next deploy"</i>',
                "sub": "READY"
            })

    rows = [
        (items[0], items[3]),
        (items[1], items[4]),
        (items[2], items[5]),
    ]

    html = [
        '<div align="center">',
        '  <h3 align="center">Recent Git Activity</h3>',
        '  <table width="100%">',
    ]
    for left, right in rows:
        html.append("    <tr>")
        html.append(f'      <td width="50%" valign="top" align="center">')
        html.append(f'        {left["icon_html"]} <b>{left["action"]}</b> &nbsp; <a href="{left["repo_url"]}"><code>{left["repo_label"]}</code></a><br>')
        html.append(f'        {left["detail_html"]}<br>')
        html.append(f'        <sub>{left["sub"]}</sub>')
        html.append(f'      </td>')
        html.append(f'      <td width="50%" valign="top" align="center">')
        html.append(f'        {right["icon_html"]} <b>{right["action"]}</b> &nbsp; <a href="{right["repo_url"]}"><code>{right["repo_label"]}</code></a><br>')
        html.append(f'        {right["detail_html"]}<br>')
        html.append(f'        <sub>{right["sub"]}</sub>')
        html.append(f'      </td>')
        html.append("    </tr>")
    html.append("  </table>")
    html.append("</div>")
    return "\n".join(html)

def update_readme(table_html, readme_path="README.md"):
    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = r"<!-- START_ACTIVITY -->.*?<!-- END_ACTIVITY -->"
    replacement = f"<!-- START_ACTIVITY -->\n{table_html}\n<!-- END_ACTIVITY -->"
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
    table = render_table(items)
    update_readme(table, "README.md")
