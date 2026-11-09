#!/usr/bin/env python3
"""AI-visibility (GEO) + technical audit for a small-business website. Stdlib only."""
import json, re, sys, urllib.request, urllib.parse
from html.parser import HTMLParser

AI_BOTS = ["GPTBot", "ClaudeBot", "PerplexityBot", "Google-Extended", "CCBot", "OAI-SearchBot"]
UA = "Mozilla/5.0 (compatible; VisibilityAuditBot/1.0)"


def fetch(url, timeout=12):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(1_500_000).decode("utf-8", "replace"), r.geturl()
    except Exception:
        return 0, "", url


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""; self._t = False; self.meta = {}; self.h1 = 0
        self.canonical = False; self.ld = []; self._ld = False; self.tel = False; self.viewport = False

    def handle_starttag(self, tag, a):
        a = dict(a)
        if tag == "title": self._t = True
        elif tag == "h1": self.h1 += 1
        elif tag == "meta":
            k = a.get("name") or a.get("property")
            if k: self.meta[k.lower()] = a.get("content", "")
            if (a.get("name") or "").lower() == "viewport": self.viewport = True
        elif tag == "link" and a.get("rel") == "canonical": self.canonical = True
        elif tag == "a" and (a.get("href") or "").startswith("tel:"): self.tel = True
        elif tag == "script" and a.get("type") == "application/ld+json": self._ld = True; self.ld.append("")

    def handle_endtag(self, tag):
        if tag == "title": self._t = False
        if tag == "script": self._ld = False

    def handle_data(self, d):
        if self._t: self.title += d
        if self._ld and self.ld: self.ld[-1] += d


def schema_types(blocks):
    types = set()
    def walk(o):
        if isinstance(o, dict):
            t = o.get("@type")
            for x in (t if isinstance(t, list) else [t]):
                if x: types.add(str(x))
            for v in o.values(): walk(v)
        elif isinstance(o, list):
            for v in o: walk(v)
    for b in blocks:
        try: walk(json.loads(b))
        except Exception: pass
    return types


def blocked_bots(robots):
    blocked, agent = set(), None
    for line in robots.splitlines():
        line = line.split("#")[0].strip()
        if ":" not in line: continue
        k, v = [x.strip() for x in line.split(":", 1)]
        if k.lower() == "user-agent": agent = v
        elif k.lower() == "disallow" and v == "/" and agent:
            for b in AI_BOTS:
                if agent == "*" or agent.lower() == b.lower(): blocked.add(b)
    return sorted(blocked)


# (id, points, label, fix)
def audit(url):
    if not re.match(r"https?://", url): url = "https://" + url
    status, html, final = fetch(url)
    base = "{0.scheme}://{0.netloc}".format(urllib.parse.urlparse(final))
    res = {"url": url, "final_url": final, "reachable": status == 200, "checks": []}
    if status != 200:
        res["score"] = 0; return res
    p = Page(); p.feed(html)
    _, robots, _ = fetch(base + "/robots.txt")
    s_llms, llms, _ = fetch(base + "/llms.txt")
    s_map, sm, _ = fetch(base + "/sitemap.xml")
    types = schema_types(p.ld)
    blk = blocked_bots(robots)
    desc = p.meta.get("description", "")
    biz = {"LocalBusiness", "Organization", "Store", "Restaurant", "ProfessionalService"} | {t for t in types if "Business" in t or t.endswith("Service")}
    C = [
        ("https", 10, "Site served over HTTPS", final.startswith("https://"), "Enable HTTPS; AI and search engines deprioritise insecure sites."),
        ("ai_bots", 20, "AI crawlers are allowed in robots.txt" + (f" (blocked: {', '.join(blk)})" if blk else ""), not blk, "Remove blanket Disallow for GPTBot/ClaudeBot/PerplexityBot so ChatGPT, Claude & Perplexity can cite you."),
        ("schema_biz", 20, "LocalBusiness/Organization structured data (JSON-LD)", bool(types & biz), "Add JSON-LD with name, address, phone, hours, services: the #1 way AI answers identify you."),
        ("schema_faq", 10, "FAQ structured data", "FAQPage" in types, "Add an FAQ section marked up as FAQPage; AI engines quote Q&A directly."),
        ("llms", 5, "llms.txt present", s_llms == 200 and len(llms) > 20, "Publish /llms.txt summarising who you are and your key pages."),
        ("sitemap", 5, "sitemap.xml present", s_map == 200 and ("<urlset" in sm or "<sitemapindex" in sm), "Publish /sitemap.xml and submit it to Google Search Console."),
        ("title", 5, "Descriptive <title> (15-65 chars)", 15 <= len(p.title.strip()) <= 65, "Use '<Service> in <City> | <Brand>' style title."),
        ("desc", 5, "Meta description (70-170 chars)", 70 <= len(desc) <= 170, "Write a clear 1-2 sentence description with service + location."),
        ("h1", 5, "Exactly one <h1>", p.h1 == 1, "Use a single H1 stating what you do and where."),
        ("phone", 5, "Click-to-call phone link", p.tel, "Add a tel: link so customers (and assistants) can reach you."),
        ("mobile", 5, "Mobile viewport tag", p.viewport, "Add <meta name=viewport> so the site is mobile friendly."),
        ("og", 3, "Open Graph tags", "og:title" in p.meta, "Add og:title/og:description/og:image for better link previews."),
        ("canon", 2, "Canonical link", p.canonical, "Add rel=canonical to avoid duplicate-content dilution."),
    ]
    res["checks"] = [dict(id=i, pts=pt, label=l, ok=bool(ok), fix=f) for i, pt, l, ok, f in C]
    res["score"] = sum(c["pts"] for c in res["checks"] if c["ok"])
    return res


def grade(s): return "A" if s >= 85 else "B" if s >= 70 else "C" if s >= 50 else "D" if s >= 30 else "F"


def report_html(r, pay_url="#", brand="AI Visibility Audit"):
    esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;")
    fails = [c for c in r["checks"] if not c["ok"]]
    rows = "".join(f"<tr><td>{'✅' if c['ok'] else '❌'}</td><td>{esc(c['label'])}</td><td>{c['pts']}</td></tr>" for c in r["checks"])
    fixes = "".join(f"<li><b>{esc(c['label'])}</b><br>{esc(c['fix'])}</li>" for c in fails[:2])
    locked = f"<p>+ {max(0, len(fails)-2)} more fixes with copy-paste code in the full report.</p>" if len(fails) > 2 else ""
    return f"""<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>{brand}: {esc(r['url'])}</title><style>body{{font:16px system-ui;max-width:680px;margin:2rem auto;padding:0 1rem}}
.s{{font-size:3rem;font-weight:700}}td{{padding:.3rem .6rem;border-bottom:1px solid #ddd}}a.b{{display:inline-block;background:#111;color:#fff;padding:.8rem 1.2rem;border-radius:8px;text-decoration:none}}</style>
<h1>{brand}</h1><p>{esc(r['url'])}</p><div class=s>{r['score']}/100 (grade {grade(r['score'])})</div>
<table>{rows}</table><h2>Top fixes</h2><ol>{fixes}</ol>{locked}
<p><a class=b href="{pay_url}">Get the full fix-list + implementation code</a></p>"""


if __name__ == "__main__":
    for u in sys.argv[1:]:
        print(json.dumps(audit(u), indent=1))
