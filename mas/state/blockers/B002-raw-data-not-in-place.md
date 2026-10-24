# Blocker B002: raw recordings are not in data/raw/

- Opened: 2026-10-24 by orchestrator (setup)
- Phase: P00
- blocking: P00
- Status: resolved 2026-10-24

## Question

P00 inventories `data/raw/S01 … S05/*.ebr` (delivered out-of-band,
git-ignored). The folder does not exist in this repository. Agents may not
copy or list recordings themselves.

## Options and consequences

| Option | Consequence |
|---|---|
| A. Sebastian copies or symlinks the recordings: `data/raw/S01/OO.ebr` … | P00 can run |
| B. Point the scripts at another folder via config | the roadmap's paths change; needs a decision in `decisions.md` |

## Recommendation

A, then check from your own terminal: `git check-ignore data/raw/S01/OO.ebr`
must print the path.

## Resolution (Sebastian)

2026-10-24: option A. Sebastian copied the `.ebr` files of S01–S05 from
`../SSVEPs_OO_mOO/` into the git-ignored raw-data folder (photos and videos left
behind). `git status` shows no data files. Completeness (23 files, spec §4) is
verified by the P00 inventory script, not by an agent listing the folder.
