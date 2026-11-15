#!/usr/bin/env python3
"""Build livrable.html: every Markdown page of the deliverable in one self-contained HTML file
(images embedded as base64, internal links turned into in-page anchors). Opens in any browser."""
import base64, re
from pathlib import Path
from markdown_it import MarkdownIt

HERE = Path(__file__).parent
PAGES = ["00-concept-card.md", "README.md", "01-problem.md", "02-workflow.md",
         "03-steps/a-requirement-and-claims.md", "03-steps/b-split-and-reading-contract.md",
         "03-steps/c-evidence.md", "03-steps/d-ai-review-and-refusals.md", "03-steps/e-lanes-and-signature.md",
         "04-principles-and-tradeoffs.md", "05-measurement.md", "06-limits-and-failure-modes.md",
         "07-decision-log.md", "08-sources.md", "09-adoption-on-an-existing-project.md", "10-lessons-log.md"]
md = MarkdownIt("commonmark", {"html": True}).enable("table")
anchor = lambda p: "page-" + re.sub(r"[^a-z0-9]+", "-", p.lower()).strip("-")


def render(page):
    text = (HERE / page).read_text(encoding="utf-8")
    html = md.render(text)

    def img(m):
        path = (HERE / page).parent / m.group(1)
        data = base64.b64encode(path.read_bytes()).decode()
        return f'src="data:image/png;base64,{data}"'
    html = re.sub(r'src="([^"]+\.png)"', img, html)

    def link(m):
        target = (Path(page).parent / m.group(1)).as_posix()
        target = re.sub(r"[^/]+/\.\./", "", target)
        if target.endswith("/"):
            target = next((p for p in PAGES if p.startswith(target)), target)
        return f'href="#{anchor(target)}"' if target in PAGES or target.endswith("/") else m.group(0)
    html = re.sub(r'href="([^"#:]+\.md|03-steps/|\.\./[^"#:]+\.md)"', link, html)
    return f'<section id="{anchor(page)}">{html}</section>'


css = """
:root{--fg:#1f2328;--mut:#57606a;--line:#d0d7de;--soft:#f6f8fa;--acc:#1f5fbf;--bg:#fff}
@media (prefers-color-scheme:dark){:root{--fg:#e6edf3;--mut:#9da7b3;--line:#30363d;--soft:#161b22;--acc:#58a6ff;--bg:#0d1117}}
body{background:var(--bg);color:var(--fg);font:16px/1.6 -apple-system,Segoe UI,Helvetica,Arial,sans-serif;margin:0}
main{max-width:1000px;margin:0 auto;padding:24px 20px 80px}
nav{position:sticky;top:0;background:var(--soft);border-bottom:1px solid var(--line);padding:8px 20px;font-size:13px;z-index:2;overflow-x:auto;white-space:nowrap}
nav a{color:var(--acc);text-decoration:none;margin-right:14px}
section{border-bottom:2px solid var(--line);padding-bottom:28px;margin-bottom:28px}
h1{font-size:30px;border-bottom:1px solid var(--line);padding-bottom:6px} h2{font-size:22px;margin-top:28px} h3{font-size:18px}
table{border-collapse:collapse;display:block;overflow-x:auto;font-size:14px;margin:12px 0}
td,th{border:1px solid var(--line);padding:6px 10px;vertical-align:top} th{background:var(--soft)}
img{max-width:100%;height:auto;display:block;margin:16px auto;background:#fff;border-radius:6px}
blockquote{border-left:4px solid var(--acc);margin:12px 0;padding:2px 14px;color:var(--mut)}
code{background:var(--soft);padding:1px 5px;border-radius:4px;font-size:90%} a{color:var(--acc)}
"""
nav = " ".join(f'<a href="#{anchor(p)}">{"Overview" if p == "README.md" else "Concept card" if p.startswith("00") else Path(p).stem.split("-", 1)[-1].replace("-", " ").capitalize()}</a>' for p in PAGES)
body = "\n".join(render(p) for p in PAGES)
out = HERE / "livrable.html"
out.write_text(f'<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
               f'<title>The Change Passport</title><style>{css}</style><nav>{nav}</nav><main>{body}</main></html>', encoding="utf-8")
print(out, round(out.stat().st_size / 1024), "KB")


# Standalone one-page concept card (A4, print-ready)
card_css = """
:root{--fg:#1f2328;--mut:#57606a;--line:#d8dee4;--soft:#f6f8fa;--acc:#1f5fbf;--bg:#fff}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--fg:#e6edf3;--mut:#9da7b3;--line:#30363d;--soft:#161b22;--acc:#58a6ff;--bg:#0d1117}}
@page{size:A4;margin:10mm}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--fg);font:12.5px/1.45 -apple-system,Segoe UI,Helvetica,Arial,sans-serif;margin:0}
main{max-width:1100px;margin:0 auto;padding:22px 16px;columns:2 340px;column-gap:28px}
h1{column-span:all;font-size:26px;margin:0 0 2px} h1+p{column-span:all;color:var(--mut);margin:0 0 10px}
h2{font-size:14px;text-transform:uppercase;letter-spacing:.04em;color:var(--acc);margin:12px 0 4px;break-after:avoid}
p,ul,ol,table,blockquote{margin:0 0 6px;break-inside:avoid} ul,ol{padding-left:18px} li{margin:1px 0}
table{border-collapse:collapse;width:100%;font-size:11.5px} td,th{border:1px solid var(--line);padding:3px 6px;vertical-align:top;text-align:left} th{background:var(--soft)}
blockquote{border-left:4px solid var(--acc);padding:4px 10px;background:var(--soft);font-size:14px}
code{background:var(--soft);padding:0 4px;border-radius:3px}
@media print{body{font-size:10.4px} main{padding:0;columns:2;column-gap:7mm} h1{font-size:20px} blockquote{font-size:12px} table{font-size:9.6px}}
"""
card = HERE / "concept-card.html"
card.write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
                f'<title>Change Passport Card</title><style>{card_css}</style><main>{md.render((HERE / "00-concept-card.md").read_text(encoding="utf-8"))}</main></html>', encoding="utf-8")
print(card, round(card.stat().st_size / 1024), "KB")
