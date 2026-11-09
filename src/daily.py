#!/usr/bin/env python3
"""Daily pipeline: leads.csv -> audit each -> docs/<slug>.html + outreach drafts + state. Never auto-sends mail."""
import csv, json, re, sys, os, datetime
sys.path.insert(0, os.path.dirname(__file__))
from audit import audit, report_html, grade

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def slug(u): return re.sub(r"[^a-z0-9]+", "-", re.sub(r"^https?://", "", u.lower())).strip("-")

def run(leads=None, out=None, pay_url=None, site_base="", limit=25):
    leads = leads or os.path.join(ROOT, "data", "leads.csv")
    out = out or os.path.join(ROOT, "docs")
    pay_url = pay_url or os.environ.get("PAY_URL", "#")
    state_f = os.path.join(ROOT, "data", "state.json")
    state = json.load(open(state_f)) if os.path.exists(state_f) else {}
    os.makedirs(out, exist_ok=True)
    drafts, n = [], 0
    for row in csv.DictReader(open(leads)):
        url = row["url"].strip()
        if url in state or n >= limit: continue
        r = audit(url); n += 1
        s = slug(url)
        open(os.path.join(out, s + ".html"), "w").write(report_html(r, pay_url))
        state[url] = {"score": r["score"], "date": str(datetime.date.today()), "email": row.get("email", "")}
        if not r["reachable"]: continue
        top = [c["label"] for c in r["checks"] if not c["ok"]][:2]
        drafts.append(f"## {row.get('name', url)} <{row.get('email', '')}>\n"
                      f"Subject: {row.get('name', 'Your site')}: scores {r['score']}/100 for AI search\n\n"
                      f"Hi, I checked {url} for visibility in ChatGPT/Perplexity/Google AI answers. Score {r['score']}/100 ({grade(r['score'])}). "
                      f"Biggest gaps: {'; '.join(top) or 'none'}. Free report: {site_base}/{s}.html\n"
                      f"Reply STOP and I won't contact you again. - <your name, address>\n")
    json.dump(state, open(state_f, "w"), indent=1)
    if drafts:
        open(os.path.join(ROOT, "data", f"outreach-{datetime.date.today()}.md"), "w").write("\n---\n".join(drafts))
    return n

if __name__ == "__main__":
    print("audited", run(site_base=os.environ.get("SITE_BASE", "")))
