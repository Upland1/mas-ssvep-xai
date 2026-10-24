# Cite sources

Every agent says where its solution came from. A reader (Sebastian, the professor,
the methods-auditor) must be able to open each source and check the claim. This
procedure implements **R10** (`mas/RULES.md`) and `AGENTS.md` rule 8.

## When to cite

Cite every time you use something you did not derive on the spot:

- a method, formula, threshold, parameter value or default;
- an architecture or training recipe;
- an implementation pattern taken from a library, a repository or Sebastian's code;
- a known answer used in a synthetic test;
- a decision taken because of a rule, an audit finding or a request.

If a choice is your own, write `[own]` and one line on why. Never leave a choice
uncited and never invent a source. If you cannot find a source, say so.

## How to cite in the text

Put a bracketed number right after the claim, change or table row: `[1]`, `[2, 3]`.
Use the same number for the same source within one file. Every file that cites has
a `## Sources` section at the end, numbered to match.

In tables, the **Source** column holds the numbers (`[2]`), `R3`, `05_audit #1`, or
`[own]`.

## Formats for the Sources list

Pick the line that matches the source type. Keep the type tag in front.

| Type | Format |
|---|---|
| Paper | `[n] PAPER — Authors (Year). Title. Venue. DOI or URL. Used for: …` |
| Book / chapter | `[n] BOOK — Authors (Year). Title, chapter/section, pages. Used for: …` |
| Documentation | `[n] DOCS — Library vVersion, page title. URL. Used for: …` |
| External code example | `[n] CODE — owner/repo @ commit-or-tag, path:line-line. License. Used for: …` |
| Sebastian's code | `[n] OWN-CODE — ssvep-eeg-xai @ commit, path:line-line. Consulted because: … (R11 trigger)` |
| Project rule | `[n] RULE — mas/RULES.md Rk`, `AGENTS.md` rule k, or the spec file and section (`mas/05_PITFALLS.md PF-07`) |
| Review / handoff | `[n] HANDOFF — mas/state/phases/<Pxx-slug>/07_review.md, Round N, finding k` |
| Request / spec | `[n] REQUEST — 00_assignment.md or mas/03_ROADMAP.md Pxx task k, quoted phrase` |
| Data / output | `[n] DATA — path to CSV or log, command that produced it, commit` |
| Own reasoning | `[own]` inline only, never in the list |

Get the commit with `git rev-parse --short HEAD` (or `git -C <repo> rev-parse --short
HEAD`) and line numbers from the file you actually read. Versions come from
`pip show <package>`, not memory.

## Rules for code examples

1. **Read, understand, then write your own.** Use examples to learn the structure and
   check your result. Re-implement in this project's style.
2. **Copying.** Copy at most a few lines, only from code with a compatible license
   (MIT, BSD, Apache-2.0; check the repo's LICENSE file), and mark the lines with a
   comment `# adapted from [n]`. No copying from code without a license.
3. **Prefer primary sources.** The paper's own code or the library that defines the
   method (MNE, mne-connectivity, scikit-learn, SciPy, braindecode, pyRiemann) over
   blog posts or random gists. Say which you used.
4. **Record differences.** When your version differs from the example (e.g. sampling
   rate, window length, channel count, normalization), say how and why.
5. **Sebastian's code** is a source like any other, cited with commit and lines. In this
   rebuild it is governed by R11 (= `AGENTS.md` rule 8): consult
   `reference/ssvep-eeg-xai/` only after your own attempt.

## Checklist before marking your file READY

- [ ] Every row of the Changes / Tests table has something in its Source column.
- [ ] Every `[n]` in the text appears in `## Sources`, and every source is cited.
- [ ] Code sources carry repo, commit, path and lines; docs carry a version.
- [ ] Copied lines are marked in the code and covered by a compatible license.
- [ ] Any consultation of Sebastian's original code during the rebuild is listed in
      the "Reference consultations" section (R11).
- [ ] Nothing is cited that you did not actually open in this run.
