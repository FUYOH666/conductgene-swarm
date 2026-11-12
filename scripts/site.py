"""Build the GitHub Pages site into _site/: a landing page, the evidence packs, llms.txt.

uv run python scripts/site.py && open _site/index.html
"""

from __future__ import annotations

import shutil
from html import escape
from pathlib import Path

from precedent import __version__
from precedent.theme import DARK, LIGHT, MONO, SANS, SERIF, css_variables

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "_site"
REPO = "https://github.com/FUYOH666/precedent"
SITE = "https://fuyoh666.github.io/precedent"

CSS = f"""
@font-face{{font-family:'Instrument Serif';src:url(fonts/InstrumentSerif-Regular.ttf);font-display:swap}}
@font-face{{font-family:Geist;src:url(fonts/Geist.ttf);font-weight:100 900;font-display:swap}}
@font-face{{font-family:'Geist Mono';src:url(fonts/GeistMono.ttf);font-weight:100 900;font-display:swap}}
:root{{{css_variables(LIGHT)}}}
@media (prefers-color-scheme: dark){{:root{{{css_variables(DARK)}}}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font:17px/1.6 {SANS}}}
main{{max-width:880px;margin:0 auto;padding:72px 24px 96px}}
.mark{{display:inline-flex;flex-direction:column;gap:5px;margin-right:16px;vertical-align:middle}}
.mark i{{display:block;width:40px;height:17px;border-radius:5px;border:2px solid}}
.mark i:first-child{{border-color:var(--red);background:var(--red-bg)}}
.mark i:last-child{{border-color:var(--green);background:var(--green-bg)}}
h1{{font:400 64px/1 {SERIF};margin:0;display:inline;vertical-align:middle;letter-spacing:-1px}}
.tag{{font:400 30px/1.25 {SERIF};margin:28px 0 8px}}
p{{margin:14px 0}}
.muted{{color:var(--muted)}}
.kicker{{font:500 12px {MONO};color:var(--accent);letter-spacing:.12em;text-transform:uppercase;margin-top:56px}}
a{{color:var(--accent)}}
code{{font:14px {MONO}}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:14px;margin:16px 0}}
.card{{display:block;text-decoration:none;color:inherit;background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px 20px}}
.card:hover{{border-color:var(--accent)}}
.card b{{font:400 22px {SERIF};display:block;margin:6px 0}}
.badge{{font:700 12px {MONO};padding:2px 10px;border-radius:999px;border:1px solid}}
.pass{{color:var(--green);background:var(--green-bg)}}.block{{color:var(--red);background:var(--red-bg)}}
pre{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px;overflow:auto;font:14px {MONO}}}
footer{{margin-top:72px;font:12px {MONO};color:var(--faint)}}
"""

INDEX = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Precedent · pull requests for AI judgment</title>
<meta name="description" content="Human corrections to an LLM judge become scoped rules, tested on every case, approved by a second person, reversible, with a hash-chained audit log.">
<meta property="og:title" content="Precedent · pull requests for AI judgment">
<meta property="og:description" content="A correction to an AI judge, treated like a code change.">
<meta property="og:image" content="{SITE}/social-preview.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<style>{CSS}</style></head><body><main>
<div><span class="mark"><i></i><i></i></span><h1>precedent</h1></div>
<p class="tag">Pull requests for AI judgment</p>
<p>Our first version learned a rule from one supervisor's correction. It broke three calls it had been
getting right, and our own evaluation reported <code>improved: True</code>.</p>
<p>Precedent makes that change impossible to ship. A correction to an LLM judge becomes a rule that
states its reason. The rule is tested against every case the system has been checked on, needs a
second person to approve it, and reverts in one command. Every step lands in a hash-chained log.</p>
<pre>uvx --from git+{REPO} precedent demo</pre>

<div class="kicker">What an auditor receives</div>
<div class="cards">
  <a class="card" href="evidence/escalation-callback@1.html"><span class="badge block">✗ BLOCKED</span>
  <b>The keyword rule from version 1</b><span class="muted">Fixes 2 calls, breaks 3. The evidence pack shows which ones and why.</span></a>
  <a class="card" href="evidence/escalation-callback@2.html"><span class="badge pass">✓ PASSED</span>
  <b>The same correction, stated as its reason</b><span class="muted">Fixes 3, breaks 0, approved by a second person.</span></a>
</div>

<div class="kicker">In a real pull request</div>
<p>The rules gate runs on this repository as a GitHub Action:
<a href="{REPO}/pull/14">#14, the v1 rule, blocked</a> ·
<a href="{REPO}/pull/15">#15, the reason-based rule, passed and merged</a>.</p>

<div class="kicker">Read</div>
<p><a href="{REPO}">The repository</a> · <a href="{REPO}/blob/main/docs/essay.md">Your reviewers are already
writing policy (essay)</a> · <a href="{REPO}/blob/main/docs/what-v1-got-wrong.md">What v1 got wrong</a> ·
<a href="{REPO}/blob/main/docs/how-it-works.md">How it works</a></p>

<div class="kicker">Work with us</div>
<p>If your reviewers correct an AI's decisions and those corrections go nowhere, send us a sample of the
decisions they overrode. We run them through the gate on your hardware and show which corrections are
safe rules and which would have broken something.
<a href="https://scanovich.ai/contact/?ref=precedent">scanovich.ai/contact</a></p>

<footer>precedent {escape(__version__)} · MIT · built at <a href="https://scanovich.ai">Scanovich</a></footer>
</main></body></html>
"""

FAVICON = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
<style>@media (prefers-color-scheme: dark){{.r{{fill:{DARK.red_bg};stroke:{DARK.red}}}.g{{fill:{DARK.green_bg};stroke:{DARK.green}}}}}</style>
<rect class="r" x="3" y="5" width="26" height="10" rx="3" fill="{LIGHT.red_bg}" stroke="{LIGHT.red}" stroke-width="2"/>
<rect class="g" x="3" y="18" width="26" height="10" rx="3" fill="{LIGHT.green_bg}" stroke="{LIGHT.green}" stroke-width="2"/>
</svg>
"""

LLMS = f"""# Precedent

> Pull requests for AI judgment. Human corrections to an LLM judge become scoped rules written in
> yes/no predicates, tested by a blocking gate against every labelled case and past correction,
> approved by a second person, reversible, and recorded in a hash-chained SQLite event log.

- [README]({REPO}/blob/main/README.md): what it is, quickstart, results, limitations
- [How it works]({REPO}/blob/main/docs/how-it-works.md): judge, predicates, rules, gate, log
- [Writing a pack]({REPO}/blob/main/docs/writing-a-pack.md): define a new domain
- [Essay]({REPO}/blob/main/docs/essay.md): why corrections should be treated as code changes
- [What v1 got wrong]({REPO}/blob/main/docs/what-v1-got-wrong.md): the failure that motivated v2
- [Evidence pack, blocked rule]({SITE}/evidence/escalation-callback@1.html)
- [Evidence pack, approved rule]({SITE}/evidence/escalation-callback@2.html)
- [Python API]({REPO}/blob/main/src/precedent/__init__.py): public names are in `__all__`
"""


def main() -> int:
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "evidence").mkdir(parents=True)
    (OUT / "index.html").write_text(INDEX, encoding="utf-8")
    (OUT / "favicon.svg").write_text(FAVICON, encoding="utf-8")
    (OUT / "llms.txt").write_text(LLMS, encoding="utf-8")
    shutil.copy(ROOT / "docs" / "assets" / "social-preview.png", OUT / "social-preview.png")
    shutil.copytree(ROOT / "docs" / "assets" / "fonts", OUT / "fonts")
    for f in (ROOT / "docs" / "evidence" / "demo" / "evidence").glob("*"):
        shutil.copy(f, OUT / "evidence" / f.name)
    print(f"site: {sorted(p.relative_to(OUT).as_posix() for p in OUT.rglob('*') if p.is_file())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
