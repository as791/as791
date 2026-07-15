"""Generate the light and dark SVGs used by the GitHub profile README.

The script uses only Python's standard library and is run daily by GitHub
Actions. ACCESS_TOKEN is optional; when present, private contribution data is
included. The repository's GITHUB_TOKEN is enough for all public statistics.
"""

import html
import json
import os
import shutil
import subprocess
import urllib.request
from datetime import datetime, timezone


USER = "as791"
JOINED_YEAR = 2018
WIDTH = 58

ART = r"""
          @@@@@@       @@@@@@@@
         @@    @@     @@
         @@    @@     @@
         @@@@@@@@      @@@@@@@
         @@    @@            @@
         @@    @@            @@
         @@    @@     @@@@@@@@

        7777777      99999       11
             77     99   99     111
            77       999999      11
           77            99      11
          77            99       11
         77        99999       111111

       build · learn · distribute
"""

PALETTES = {
    "dark": {
        "bg": "#0d1117", "border": "#30363d", "art": "#8b949e",
        "heading": "#58a6ff", "key": "#ffa657", "value": "#c9d1d9",
        "dim": "#484f58", "green": "#3fb950", "red": "#f85149",
    },
    "light": {
        "bg": "#ffffff", "border": "#d0d7de", "art": "#57606a",
        "heading": "#0969da", "key": "#953800", "value": "#24292f",
        "dim": "#afb8c1", "green": "#1a7f37", "red": "#cf222e",
    },
}

TOKEN = os.environ.get("ACCESS_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""


def graphql(query, variables=None):
    payload = {"query": query, "variables": variables or {}}
    if not TOKEN:
        # Convenient local fallback; GitHub Actions always takes the path below.
        command = ["gh", "api", "graphql", "-f", f"query={query}"]
        for key, value in (variables or {}).items():
            if value is not None:
                command.extend(["-F", f"{key}={value}"])
        if shutil.which("rtk"):
            command.insert(0, "rtk")
        response = subprocess.run(
            command,
            text=True,
            capture_output=True,
            check=True,
        )
        result = json.loads(response.stdout)
        if result.get("errors"):
            raise RuntimeError(result["errors"])
        return result["data"]

    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "User-Agent": f"{USER}-profile-readme",
        },
    )
    with urllib.request.urlopen(request) as response:
        payload = json.load(response)
    if payload.get("errors"):
        raise RuntimeError(payload["errors"])
    return payload["data"]


def fetch_stats():
    current_year = datetime.now(timezone.utc).year
    yearly = "\n".join(
        f'y{year}: contributionsCollection(from: "{year}-01-01T00:00:00Z", '
        f'to: "{year + 1}-01-01T00:00:00Z") '
        "{ totalCommitContributions restrictedContributionsCount }"
        for year in range(JOINED_YEAR, current_year + 1)
    )
    contribution_data = graphql(
        f'query {{ user(login: "{USER}") {{ {yearly} }} }}'
    )["user"]
    commits = sum(
        item["totalCommitContributions"] + item["restrictedContributionsCount"]
        for item in contribution_data.values()
    )

    user = graphql(
        f"""
        query {{
          user(login: "{USER}") {{
            id
            followers {{ totalCount }}
            repositories(first: 100, ownerAffiliations: OWNER) {{
              totalCount
              nodes {{ name stargazerCount isFork languages(first: 100) {{ totalSize }} }}
            }}
            repositoriesContributedTo(
              first: 1,
              contributionTypes: [COMMIT, PULL_REQUEST, REPOSITORY]
            ) {{ totalCount }}
          }}
        }}
        """
    )["user"]
    repositories = user["repositories"]["nodes"]
    stats = {
        "followers": user["followers"]["totalCount"],
        "repos": user["repositories"]["totalCount"],
        "contributed": user["repositoriesContributedTo"]["totalCount"],
        "stars": sum(repo["stargazerCount"] for repo in repositories),
        "commits": commits,
        "code_bytes": sum(
            repo["languages"]["totalSize"]
            for repo in repositories
            if not repo["isFork"]
        ),
    }
    return stats


def key_value(key, value, width=WIDTH):
    dots = "." * max(width - len(key) - len(str(value)) - 3, 1)
    return [(f"{key}: ", "key"), (f"{dots} ", "dim"), (str(value), "value")]


def double_value(key1, value1, key2, value2):
    return key_value(key1, value1, 31) + [(" | ", "dim")] + key_value(key2, value2, 24)


def rule(title):
    label = f"─ {title} "
    return [(label, "heading"), ("─" * (WIDTH - len(label)), "dim")]


def info_lines(stats):
    number = lambda value: f"{value:,}"
    code_size = f"{stats['code_bytes'] / 1024 / 1024:.1f} MiB across owned repositories"
    return [
        [(f"{USER}@github ", "heading"), ("─" * (WIDTH - len(USER) - 8), "dim")],
        [],
        key_value("Role", "Senior Software Engineer"),
        key_value("Company", "MerQube"),
        key_value("Location", "Bangalore, India"),
        key_value("Focus", "Data, Distributed Systems, ML / GenAI"),
        [],
        key_value("Languages", "Java, Python, Go, TypeScript"),
        key_value("Backend", "Spring, Microservices, Data Platforms"),
        key_value("Research", "Computer Vision, Robust ML"),
        [],
        rule("Contact"),
        key_value("Web", "sites.google.com/view/as791/home"),
        key_value("LinkedIn", "in/as791"),
        [],
        rule("GitHub Stats"),
        double_value("Repos", f"{stats['repos']} {{Contributed: {stats['contributed']}}}", "Stars", number(stats["stars"])),
        double_value("Commits", number(stats["commits"]), "Followers", number(stats["followers"])),
        key_value("Public code", code_size),
    ]


def render(mode, stats):
    palette = PALETTES[mode]
    output = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="900" height="500" '
        'viewBox="0 0 900 500" font-family="Consolas, Menlo, monospace" font-size="13px">',
        f'<rect x="0.5" y="0.5" width="899" height="499" rx="10" '
        f'fill="{palette["bg"]}" stroke="{palette["border"]}"/>',
    ]
    for index, line in enumerate(ART.strip("\n").split("\n")):
        output.append(
            f'<text x="25" y="{82 + index * 20}" fill="{palette["art"]}" '
            f'xml:space="preserve">{html.escape(line)}</text>'
        )
    for index, segments in enumerate(info_lines(stats)):
        if not segments:
            continue
        spans = "".join(
            f'<tspan fill="{palette[color]}">{html.escape(text)}</tspan>'
            for text, color in segments
        )
        output.append(
            f'<text x="390" y="{45 + index * 22}" xml:space="preserve">{spans}</text>'
        )
    output.append("</svg>")
    return "\n".join(output)


def self_check():
    assert len("".join(text for text, _ in key_value("Role", "Senior Software Engineer"))) == WIDTH
    assert set(PALETTES) == {"dark", "light"}


if __name__ == "__main__":
    self_check()
    profile_stats = fetch_stats()
    print("Stats:", profile_stats)
    for color_mode in PALETTES:
        with open(f"{color_mode}_mode.svg", "w", encoding="utf-8") as svg:
            svg.write(render(color_mode, profile_stats))
    print("Wrote dark_mode.svg and light_mode.svg")
