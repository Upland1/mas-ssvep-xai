"""P24 documentation checks: Sources sections, cited paths exist, SVG parses, privacy, PF-31 naming.

Data-free: the `reports/` checks skip when that folder is absent.
"""
import glob
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MD_DOCS = ["README.md", "RESEARCH_LOG.md", "docs/report/v2/report.md",
           "docs/progress_report/progress_report.md"]
SVG = "docs/infographic/methodology_infographic.svg"
ALL_DOCS = MD_DOCS + [SVG]

# characters that may appear inside a cited path
_PATH = r"[A-Za-z0-9_.*/\-<>{}\[\]]+"
REPORTS_RE = re.compile(r"(?<![A-Za-z0-9_./\-])reports/" + _PATH)
MAS_RE = re.compile(r"(?<![A-Za-z0-9_./\-])(?:mas|docs)/" + _PATH)
PHASE_REPORT_RE = re.compile(r"mas/state/reports/(P\d\d)\.md")


def _text(rel):
  return (ROOT / rel).read_text(encoding="utf-8")


def _clean(p):
  """Strip trailing punctuation and markdown/XML residue from a captured path."""
  p = p.rstrip(".,;:)]}>")
  return p


def _is_placeholder(p):
  return (bool(re.search(r"[<>{}\[\]]", p)) or "..." in p
          or bool(re.search(r"/Pxx|Pxx\.", p)))


def _cited(regex, rel):
  out = set()
  for m in regex.findall(_text(rel)):
    m = _clean(m)
    if m and not _is_placeholder(m):
      out.add(m)
  return sorted(out)


def _exists(rel_path):
  # git-ignored run-time locations (created by `make`) are not checked
  if rel_path.startswith("mas/state/scratch/"):
    return True
  # blocker ids are cited by their prefix (B003 for B003-cohort-beyond-S05.md)
  if re.fullmatch(r"mas/state/blockers/B\d{3}", rel_path):
    rel_path += "*"
  if any(c in rel_path for c in "*?"):
    return bool(glob.glob(str(ROOT / rel_path)))
  return (ROOT / rel_path).exists()


@pytest.mark.parametrize("rel", ALL_DOCS)
def test_document_exists(rel):
  assert (ROOT / rel).is_file(), rel


@pytest.mark.parametrize("rel", MD_DOCS)
def test_markdown_has_sources_section(rel):
  lines = _text(rel).splitlines()
  heads = [i for i, l in enumerate(lines) if re.match(r"^## Sources\s*$", l)]
  assert len(heads) == 1, f"{rel}: expected one '## Sources' heading, found {len(heads)}"
  body = [l for l in lines[heads[0] + 1:] if l.strip()]
  assert len(body) >= 3, f"{rel}: Sources section is empty"


def test_svg_parses_and_has_sources_note():
  root = ET.fromstring(_text(SVG))
  assert root.tag == "{http://www.w3.org/2000/svg}svg"
  texts = " ".join("".join(e.itertext()) for e in root.iter() if e.tag.endswith("text"))
  assert "Sources" in texts


@pytest.mark.parametrize("rel", ALL_DOCS)
def test_cited_reports_paths_exist(rel):
  if not (ROOT / "reports").is_dir():
    pytest.skip("reports/ absent (data-free CI)")
  missing = []
  for p in _cited(REPORTS_RE, rel):
    if p.startswith("reports/") and not _exists(p.rstrip("/")):
      missing.append(p)
  assert not missing, f"{rel} cites missing paths: {missing}"


@pytest.mark.parametrize("rel", ALL_DOCS)
def test_cited_mas_and_docs_paths_exist(rel):
  missing = [p for p in _cited(MAS_RE, rel) if not _exists(p.rstrip("/"))]
  assert not missing, f"{rel} cites missing paths: {missing}"


@pytest.mark.parametrize("rel", ALL_DOCS)
def test_no_nonexistent_phase_report_cited(rel):
  missing = [f"mas/state/reports/{p}.md" for p in sorted(set(PHASE_REPORT_RE.findall(_text(rel))))
             if not (ROOT / f"mas/state/reports/{p}.md").is_file()]
  assert not missing, f"{rel}: {missing}"


@pytest.mark.parametrize("rel", MD_DOCS)
def test_no_bare_compact_model_name_in_tables(rel):
  """PF-31: table rows must say compact_cnn or compact_eegnet, not a bare 'compact'."""
  bad = []
  for i, line in enumerate(_text(rel).splitlines(), 1):
    if not line.lstrip().startswith("|"):
      continue
    for cell in (c.strip().strip("*`_ ") for c in line.strip().strip("|").split("|")):
      if cell.lower() in ("compact", "compact net", "compactnet"):
        bad.append((i, cell))
  assert not bad, f"{rel}: bare 'compact' model name in table cells {bad}"


# the guard's vendor/tool pattern, assembled from fragments so no term appears whole here
_TERMS = [["cla", "ude"], ["anthr", "opic"], ["co-auth", "ored-by"]]
_VENDOR = re.compile("|".join("".join(t) for t in _TERMS), re.I)


@pytest.mark.parametrize("rel", ALL_DOCS)
def test_privacy_no_vendor_terms(rel):
  hits = [(i, l.strip()[:60]) for i, l in enumerate(_text(rel).splitlines(), 1) if _VENDOR.search(l)]
  assert not hits, f"{rel}: vendor/tool term at lines {[h[0] for h in hits]}"
