#!/usr/bin/env python3
"""Convert .md articles in Learn/ to .html for GitHub Pages.
SEO-optimized: BreadcrumbList, Article + Course schema, lastModified, Person sameAs, OG image, breadcrumb UI."""

import os, re, json
import markdown

LEARN_DIR = "/Users/npdat132/Works/kiro-claude-cursor/Learn"
BASE_URL = "https://devnpdat.github.io/kiro-claude-cursor"
LINKEDIN = "https://www.linkedin.com/in/phudatnguyen-dotnet-developer/"
GITHUB = "https://github.com/devnpdat"
AUTHOR = "Phú Đạt Nguyễn"
OG_IMAGE = f"{BASE_URL}/assets/og-image.png"
TODAY = "2026-07-10"

# Article order for prev/next linking
ARTICLES = [
    {"id": "00", "slug": "00-cach-hoc-ky-thuat-chuyen-sau-nho-lau", "title": "Bài 0: Cách Học Kỹ Thuật Chuyên Sâu & Nhớ Lâu"},
    {"id": "01", "slug": "01-cpu-bound-vs-io-bound", "title": "Bài 1: CPU-bound vs I/O-bound"},
    {"id": "02", "slug": "02-thread-vs-async-await", "title": "Bài 2: Thread vs Async/Await"},
    {"id": "03", "slug": "03-scale-vertical-vs-horizontal-k8s", "title": "Bài 3: Scale — Vertical vs Horizontal, K8s"},
    {"id": "04", "slug": "04-kafka-cau-hinh-toi-uu", "title": "Bài 4: Kafka — Cấu hình tối ưu"},
    {"id": "05", "slug": "05-database-performance-index-query-plan", "title": "Bài 5: Database Performance"},
    {"id": "06", "slug": "06-caching-strategy-redis", "title": "Bài 6: Caching Strategy — Redis"},
    {"id": "07", "slug": "07-observability-metrics-logs-traces", "title": "Bài 7: Observability"},
    {"id": "08", "slug": "08-memory-and-gc-dotnet", "title": "Bài 8: Memory & GC .NET"},
    {"id": "09", "slug": "09-hardware-and-platform-cpu-gpu-ram-os", "title": "Bài 9: Hardware & Platform"},
]

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} | {author}</title>
    <meta name="description" content="{description}">
    <meta name="author" content="{author}">
    <meta name="dateModified" content="{date}">
    <meta name="datePublished" content="{date}">
    <meta property="og:title" content="{og_title}">
    <meta property="og:description" content="{description}">
    <meta property="og:url" content="{url}">
    <meta property="og:type" content="article">
    <meta property="og:site_name" content="{author} — .NET Developer">
    <meta property="og:image" content="{og_image}">
    <meta property="og:image:width" content="1200">
    <meta property="og:image:height" content="630">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{og_title}">
    <meta name="twitter:description" content="{description}">
    <meta name="twitter:image" content="{og_image}">
    <link rel="canonical" href="{url}">
    <script type="application/ld+json">
    {jsonld_main}
    </script>
    <script type="application/ld+json">
    {jsonld_breadcrumb}
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
        /* Breadcrumb */
        .breadcrumb {{
            display: flex; align-items: center; gap: 0.5rem;
            padding: 0.8rem 2rem; max-width: 800px; margin: 0 auto;
            font-size: 0.85rem; color: var(--text-muted);
        }}
        .breadcrumb a {{ color: var(--text-muted); text-decoration: none; }}
        .breadcrumb a:hover {{ color: white; text-decoration: underline; }}
        .breadcrumb .sep {{ color: rgba(255,255,255,0.2); }}
        .breadcrumb .current {{ color: var(--accent-secondary); }}
        /* Article */
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
        /* Prev/Next nav */
        .article-nav {{
            display: flex; justify-content: space-between; gap: 1rem;
            margin-top: 2rem; padding-top: 1.5rem;
            border-top: 1px solid var(--border-color);
        }}
        .article-nav a {{
            background: rgba(255,255,255,0.03);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 1rem 1.2rem;
            flex: 1;
            text-decoration: none;
            color: var(--text-muted);
            transition: border-color 0.2s;
        }}
        .article-nav a:hover {{
            border-color: var(--accent-primary);
            color: white;
        }}
        .article-nav a.next {{ text-align: right; }}
        .article-nav .dir {{ font-size: 0.75rem; color: var(--accent-secondary); }}
        .article-nav .nav-title {{ font-weight: 600; font-size: 0.95rem; }}
        .article-nav a:only-child {{ flex: 0 1 auto; }}
        /* Date badge */
        .date-badge {{
            display: inline-block; font-size: 0.8rem; color: var(--text-muted);
            margin-bottom: 1.5rem;
        }}
        .footer {{
            text-align: center; padding: 2rem; color: var(--text-muted); font-size: 0.85rem;
            border-top: 1px solid var(--border-color); margin-top: 2rem;
        }}
        .footer a {{ color: var(--accent-primary); text-decoration: none; }}
        .footer a:hover {{ text-decoration: underline; }}
        @media (max-width: 600px) {{
            .container {{ padding: 1rem; }}
            .article {{ padding: 1.2rem; }}
            .article h1 {{ font-size: 1.5rem; }}
            .article-nav {{ flex-direction: column; }}
        }}
    </style>
</head>
<body>
    <div class="breadcrumb">
        <a href="../index.html">🏠 Trang chính</a>
        <span class="sep">›</span>
        <a href="index.html">📖 Learn</a>
        <span class="sep">›</span>
        <span class="current">{short_title}</span>
    </div>
    <div class="container">
        <div class="article">
            <div class="date-badge">📅 Cập nhật lần cuối: {date}</div>
{content}
        </div>
        {article_nav}
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
            for line in raw.split("\n"):
                line = line.strip()
                if ":" in line:
                    key, _, value = line.partition(":")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    meta[key] = value
    return meta, body


def fix_md_links(html):
    """Convert .md links inside href to .html"""
    return re.sub(r'href="([^"]+)\.md"', r'href="\1.html"', html)


def get_prev_next(slug):
    """Get prev and next article info."""
    for i, art in enumerate(ARTICLES):
        if art["slug"] == slug:
            prev_art = ARTICLES[i-1] if i > 0 else None
            next_art = ARTICLES[i+1] if i < len(ARTICLES)-1 else None
            return prev_art, next_art
    return None, None


def convert_file(filepath):
    basename = os.path.splitext(os.path.basename(filepath))[0]
    
    with open(filepath, "r", encoding="utf-8") as f:
        raw = f.read()

    meta, body = parse_frontmatter(raw)

    title = meta.get("title", basename)
    description = meta.get("description", "")
    tags_raw = meta.get("tags", "")
    tags = [t.strip().strip('"').strip("'") for t in tags_raw.strip("[]").split(",")] if tags_raw else []

    # Fix internal .md references in body
    body = re.sub(r'\(([^)]+)\.md\)', r'(\1.html)', body)

    # Convert markdown to HTML
    md = markdown.Markdown(
        extensions=["fenced_code", "codehilite", "tables", "toc", "md_in_html"]
    )
    content_html = md.convert(body)
    content_html = fix_md_links(content_html)

    og_title = title.split("—")[0].strip(" #").strip()
    url = f"{BASE_URL}/Learn/{basename}.html"

    # Person sameAs
    person_jsonld = json.dumps({
        "@context": "https://schema.org",
        "@type": "Person",
        "name": AUTHOR,
        "url": LINKEDIN,
        "sameAs": [LINKEDIN, GITHUB]
    }, ensure_ascii=False, indent=2)

    # Article schema with dateModified
    article_jsonld = json.dumps({
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": og_title,
        "description": description[:200] if description else "",
        "author": {"@type": "Person", "name": AUTHOR, "url": LINKEDIN},
        "datePublished": TODAY,
        "dateModified": TODAY,
        "url": url,
        "image": OG_IMAGE
    }, ensure_ascii=False, indent=2)

    main_jsonld = f"{person_jsonld}\n    {article_jsonld}"

    # BreadcrumbList
    breadcrumb_jsonld = json.dumps({
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Trang chính", "item": BASE_URL + "/"},
            {"@type": "ListItem", "position": 2, "name": "Learn", "item": BASE_URL + "/Learn/"},
            {"@type": "ListItem", "position": 3, "name": og_title, "item": url}
        ]
    }, ensure_ascii=False, indent=2)

    # Prev/Next links
    prev_art, next_art = get_prev_next(basename)
    nav_html = ""
    if prev_art or next_art:
        nav_html = '<nav class="article-nav">'
        if prev_art:
            prev_url = f"{prev_art['slug']}.html"
            nav_html += f'<a href="{prev_url}" class="prev" rel="prev">'
            nav_html += f'<div class="dir">← Bài trước</div>'
            nav_html += f'<div class="nav-title">{prev_art["title"]}</div>'
            nav_html += f'</a>'
        else:
            nav_html += '<div></div>'
        if next_art:
            next_url = f"{next_art['slug']}.html"
            nav_html += f'<a href="{next_url}" class="next" rel="next">'
            nav_html += f'<div class="dir">Bài tiếp theo →</div>'
            nav_html += f'<div class="nav-title">{next_art["title"]}</div>'
            nav_html += f'</a>'
        nav_html += '</nav>'

    html = HTML_TEMPLATE.format(
        title=og_title,
        short_title=og_title[:50],
        author=AUTHOR,
        description=description[:200].replace('"', "&quot;"),
        date=TODAY,
        og_title=og_title,
        url=url,
        og_image=OG_IMAGE,
        jsonld_main=main_jsonld,
        jsonld_breadcrumb=breadcrumb_jsonld,
        content=content_html,
        article_nav=nav_html,
        linkedin=LINKEDIN,
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
