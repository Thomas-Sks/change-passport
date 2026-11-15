#!/usr/bin/env python3
"""Build the demo site: the technical pipeline walkthrough (demo/flow.html, Mermaid diagrams).

  python3 build_demo.py     # → ../public/index.html (site root, e.g. for Vercel) and out/flow.html

The page is fully static: Mermaid is vendored in demo/vendor/, so it works offline.
"""
import shutil
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE / "out"
PUB = HERE.parent / "public"


def main():
    page = (HERE / "demo" / "flow.html").read_text(encoding="utf-8")
    for target in (OUT / "flow.html", PUB / "index.html"):
        target.parent.mkdir(exist_ok=True)
        target.write_text(page, encoding="utf-8")
        shutil.copytree(HERE / "demo" / "vendor", target.parent / "vendor", dirs_exist_ok=True)
        print(target)


if __name__ == "__main__":
    main()
