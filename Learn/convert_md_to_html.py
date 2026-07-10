#!/usr/bin/env python3
"""Convert .md articles in Learn/ to .html for GitHub Pages.
Preserves .md files, outputs .html with dark theme + OG tags + JSON-LD per article."""

import os, re, json
import markdown
from markdown.extensions import fenced_code, codehilite, tables, toc

LEARN_DIR = "/Users/npdat132/Works/kiro-claude-cursor/Learn"
BASE_URL = "https://devnpdat.github.io/kiro-claude-cursor"
LINKEDIN = "https://www.linkedin.com/in/phudatnguyen-dotnet-developer/"
AUTHOR = "Phú Đạt Nguyễn"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} | {author}</title>
    <meta name="description" content="{description}">
    <meta name="author" content="{author}">
    <meta property="og:title" content="{og_title}">
    <meta property="og:description" content="{description}">
    <meta property="og:url" content="{url}">
    <meta property="og:type" content="article">
    <meta property="og:site_name" content="{author} — .NET Developer">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{og_title}">
    <meta name="twitter:description" content="{description}">
    <link rel="canonical" href="{url}">
    <script type="application/ld+json">
    {jsonld}
    </script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&family=Fira+Code:wght@400;500&display=swap');
        :root {{
            --bg-main: #0d0d14;
            --bg-card: #1a1a24;
            --text-main: #e2e8f0;
            --text-muted: #94a3b8;
            --accent-primary: #8b5cf6;
            --accent-secondary: #06b6d4;
            --accent-success: #10b981;
            --border-color: rgba(255,255,255,0.1);
            --font-sans: 'Inter', sans-serif;
            --font-mono: 'Fira Code', monospace;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: var(--font-sans);
            background-color: var(--bg-main);
            color: var(--text-main);
            line-height: 1.8;
            background-image: linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
                              linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px);
            background-size: 30px 30px;
        }}
        .container {{ max-width: 800px; margin: 0 auto; padding: 2rem; }}
        /* Article content */
        .article {{ background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 16px; padding: 2.5rem; }}
        .article h1 {{ font-size: 2rem; font-weight: 800; line-height: 1.3; margin-bottom: 1rem; }}
        .article h1 .gradient {{ background: linear-gradient(135deg, var(--accent-secondary), var(--accent-primary)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }}
        .article h2 {{ font-size: 1.5rem; font-weight: 700; margin: 2rem 0 0.8rem; color: var(--accent-secondary); }}
        .article h3 {{ font-size: 1.2rem; font-weight: 700; margin: 1.5rem 0 0.6rem; }}
        .article h4 {{ font-weight: 700; margin: 1rem 0 0.4rem; }}
        .article p {{ margin-bottom: 1rem; }}
        .article a {{ color: var(--accent-primary); text-decoration: none; }}
        .article a:hover {{ text-decoration: underline; }}
        .article strong {{ color: white; }}
        .article em {{ color: var(--text-muted); }}
        .article ul, .article ol {{ margin: 0.5rem 0 1rem 1.5rem; }}
        .article li {{ margin-bottom: 0.4rem; }}
        .article blockquote {{
            border-left: 4px solid var(--accent-primary);
            background: rgba(139,92,246,0.08);
            padding: 0.8rem 1.2rem;
            margin: 1rem 0;
            border-radius: 0 8px 8px 0;
            color: var(--text-muted);
        }}
        .article blockquote strong {{ color: var(--accent-secondary); }}
        .article hr {{ border: none; height: 1px; background: var(--border-color); margin: 2rem 0; }}
        .article img {{ max-width: 100%; border-radius: 10px; margin: 1rem 0; }}
        .article table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; border-radius: 8px; overflow: hidden; }}
        .article th, .article td {{ padding: 0.7rem 1rem; text-align: left; border-bottom: 1px solid var(--border-color); }}
        .article th {{ background: rgba(255,255,255,0.05); font-weight: 700; color: var(--accent-secondary); }}
        .article tr:last-child td {{ border-bottom: none; }}
        /* Code */
        .article code {{
            font-family: var(--font-mono);
            font-size: 0.9rem;
            background: rgba(255,255,255,0.08);
            padding: 0.15rem 0.4rem;
            border-radius: 4px;
            color: #fca5a5;
        }}
        .article pre {{
            background: #000;
            padding: 1.2rem;
            border-radius: 10px;
            overflow-x: auto;
            border: 1px solid var(--border-color);
            margin: 1rem 0;
        }}
        .article pre code {{ background: none; padding: 0; color: #a5b4fc; }}
        /* Details for quiz */
        .article details {{
            background: rgba(255,255,255,0.03);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 0.8rem 1.2rem;
            margin: 1rem 0;
            cursor: pointer;
        }}
        .article details summary {{
            font-weight: 700;
            color: var(--accent-success);
            cursor: pointer;
        }}
        .article details[open] {{ background: rgba(16,185,129,0.05); }}
        /* Nav + Footer */
        .nav-bar {{
            display: flex; justify-content: space-between; align-items: center;
            padding: 1rem 2rem; max-width: 800px; margin: 0 auto;
        }}
        .nav-bar a {{ color: var(--text-muted); text-decoration: none; font-size: 0.9rem; font-weight: 600; }}
        .nav-bar a:hover {{ color: white; }}
        .footer {{
            text-align: center; padding: 2rem; color: var(--text-muted); font-size: 0.85rem;
            border-top: 1px solid var(--border-color); margin-top: 2rem;
        }}
        .footer a {{ color: var(--accent-primary); text-decoration: none; }}
        .footer a:hover {{ text-decoration: underline; }}
        /* Callouts */
        .callout {{
            display: flex; align-items: flex-start; gap: 0.8rem;
            background: rgba(245,158,11,0.08); border: 1px solid rgba(245,158,11,0.2);
            border-radius: 10px; padding: 1rem 1.2rem; margin: 1rem 0;
        }}
        .callout.success {{ background: rgba(16,185,129,0.08); border-color: rgba(16,185,129,0.2); }}
        .callout.danger {{ background: rgba(239,68,68,0.08); border-color: rgba(239,68,68,0.2); }}
        .callout-icon {{ font-size: 1.2rem; flex-shrink: 0; }}
        @media (max-width: 600px) {{
            .container {{ padding: 1rem; }}
            .article {{ padding: 1.2rem; }}
            .article h1 {{ font-size: 1.5rem; }}
        }}
    </style>
</head>
<body>
    <div class="nav-bar">
        <a href="../index.html">🏠 Trang chính</a>
        <a href="index.html">📖 Learn</a>
    </div>
    <div class="container">
        <div class="article">
{content}
        </div>
    </div>
    <div class="footer">
        <a href="{linkedin}" target="_blank" rel="noopener">🔗 LinkedIn — {author}</a>
    </div>
</body>
</html>"""


def parse_frontmatter(text):
    """Parse YAML frontmatter with --- delimiters. Returns (meta, body)."""
    meta = {}
    body = text

    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            raw = parts[1].strip()
            body = parts[2].strip()

            # Simple YAML parser for our specific format
            for line in raw.split("\n"):
                line = line.strip()
                if ":" in line:
                    key, _, value = line.partition(":")
                    key = key.strip()
                    value = value.strip()
                    # Remove quotes
                    value = value.strip('"').strip("'")
                    meta[key] = value

    return meta, body


def fix_md_links(html):
    """Convert .md links inside href to .html"""
    # Links like <a href="01-file.md"> -> <a href="01-file.html">
    html = re.sub(r'href="([^"]+)\.md"', r'href="\1.html"', html)
    return html


def convert_file(filepath):
    basename = os.path.splitext(os.path.basename(filepath))[0]
    
    with open(filepath, "r", encoding="utf-8") as f:
        raw = f.read()

    meta, body = parse_frontmatter(raw)

    title = meta.get("title", basename)
    description = meta.get("description", "")
    tags_raw = meta.get("tags", "")
    # Clean tags
    tags = [t.strip().strip('"').strip("'") for t in tags_raw.strip("[]").split(",")] if tags_raw else []

    # Fix internal .md references in body
    # Replace "Bài X: ..." link patterns
    body = re.sub(r'\(([^)]+)\.md\)', r'(\1.html)', body)

    # Convert markdown to HTML
    md = markdown.Markdown(
        extensions=[
            "fenced_code",
            "codehilite",
            "tables",
            "toc",
            "md_in_html",  # preserve HTML in markdown (<details>, etc.)
        ]
    )
    content_html = md.convert(body)

    # Fix any .md links that the markdown converter may have created
    content_html = fix_md_links(content_html)

    og_title = title.split("—")[0].strip(" #").strip()

    url = f"{BASE_URL}/Learn/{basename}.html"

    jsonld = json.dumps({
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": og_title,
        "description": description[:200] if description else "",
        "author": {
            "@type": "Person",
            "name": AUTHOR,
            "url": LINKEDIN
        },
        "url": url
    }, ensure_ascii=False, indent=2)

    html = HTML_TEMPLATE.format(
        title=og_title,
        author=AUTHOR,
        description=description[:200].replace('"', "&quot;"),
        og_title=og_title,
        url=url,
        jsonld=jsonld,
        content=content_html,
        linkedin=LINKEDIN
    )

    outpath = os.path.join(LEARN_DIR, f"{basename}.html")
    with open(outpath, "w", encoding="utf-8") as f:
        f.write(html)

    return basename, title


def main():
    files = sorted([
        os.path.join(LEARN_DIR, f)
        for f in os.listdir(LEARN_DIR)
        if re.match(r"\d{2}-.+\.md$", f) and f != "README.md"
    ])

    results = []
    for fp in files:
        basename, title = convert_file(fp)
        results.append((basename, title))
        print(f"✅ {basename}.html — {title}")

    print(f"\n🎉 Done! {len(results)} files converted.")
    return results


if __name__ == "__main__":
    main()
