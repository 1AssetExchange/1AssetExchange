import csv, http.server, json, os, sys, tempfile, threading, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import audit, daily

GOOD = """<html><head><title>Plumber in Cape Town | Acme Plumbing</title><meta name=viewport content=x>
<meta name=description content="Acme Plumbing offers 24/7 emergency plumbing, geyser repairs and drain cleaning across Cape Town."><meta property=og:title content=x>
<link rel=canonical href=/><script type="application/ld+json">{"@context":"https://schema.org","@graph":[{"@type":"LocalBusiness","name":"Acme"},{"@type":"FAQPage"}]}</script></head>
<body><h1>Plumber</h1><a href="tel:+27000">Call</a></body></html>"""
BAD = "<html><head></head><body><h1>a</h1><h1>b</h1></body></html>"
FILES = {"/good": (GOOD, 200), "/good/robots.txt": ("User-agent: *\nAllow: /", 200), "/good/llms.txt": ("# Acme Plumbing\nEmergency plumber in Cape Town", 200),
         "/good/sitemap.xml": ("<urlset></urlset>", 200), "/bad": (BAD, 200), "/bad/robots.txt": ("User-agent: GPTBot\nDisallow: /\nUser-agent: *\nDisallow: /", 200)}

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body, code = FILES.get(self.path, ("", 404))
        self.send_response(code); self.end_headers(); self.wfile.write(body.encode())
    def log_message(self, *a): pass

class T(unittest.TestCase):
    @classmethod
    def setUpClass(c):
        c.srv = http.server.HTTPServer(("127.0.0.1", 0), H); c.port = c.srv.server_port
        threading.Thread(target=c.srv.serve_forever, daemon=True).start()
        # robots/llms/sitemap live at root of "site": serve good under /good via path rewriting of base
    @classmethod
    def tearDownClass(c): c.srv.shutdown()

    def test_blocked_bots(self):
        self.assertIn("GPTBot", audit.blocked_bots(FILES["/bad/robots.txt"][0]))
        self.assertEqual(audit.blocked_bots("User-agent: *\nAllow: /"), [])

    def test_bad_scores_low_good_scores_high(self):
        g = audit.audit(f"http://127.0.0.1:{self.port}/good")
        b = audit.audit(f"http://127.0.0.1:{self.port}/bad")
        self.assertGreater(g["score"], b["score"])
        self.assertLess(b["score"], 30)
        ids = {c["id"] for c in g["checks"] if c["ok"]}
        self.assertTrue({"schema_biz", "schema_faq", "title", "desc", "h1", "phone", "mobile", "og", "canon"} <= ids)

    def test_unreachable(self):
        self.assertEqual(audit.audit("http://127.0.0.1:1/x")["score"], 0)

    def test_daily_pipeline(self):
        d = tempfile.mkdtemp(); leads = os.path.join(d, "l.csv")
        with open(leads, "w", newline="") as f:
            w = csv.writer(f); w.writerow(["name", "url", "email"]); w.writerow(["Bad Co", f"http://127.0.0.1:{self.port}/bad", "a@b.co"])
        sf = os.path.join(daily.ROOT, "data", "state.json")
        if os.path.exists(sf): os.remove(sf)
        try:
            self.assertEqual(daily.run(leads=leads, out=d, pay_url="https://pay.example/x", site_base="https://s"), 1)
            html = [f for f in os.listdir(d) if f.endswith(".html")]
            self.assertEqual(len(html), 1)
            self.assertIn("https://pay.example/x", open(os.path.join(d, html[0])).read())
            self.assertEqual(daily.run(leads=leads, out=d), 0)  # idempotent: no re-audit
        finally:
            for f in (sf,) + tuple(os.path.join(daily.ROOT, "data", x) for x in os.listdir(os.path.join(daily.ROOT, "data")) if x.startswith("outreach-")):
                if os.path.exists(f): os.remove(f)

if __name__ == "__main__": unittest.main()
