# GlycoSiteMiner Curation

Documentation and working notes for protein glycosylation site curation and ML-pipeline development on the **GlycoSiteMiner** project (GlyGen / GWU HIVE Lab).

## About

GlycoSiteMiner is a seven-stage pipeline that extracts experimentally confirmed protein glycosylation sites from the published literature:

> NER extraction → LLM extraction → entity mapping → match scoring → feature generation → ML filtering → LLM verification

This repository tracks my contributions across two parallel workstreams:

- **Curation**: validating LLM-extracted glycosylation sites against the underlying PubMed evidence and entering confirmed sites into structured datasets via GlyTableMaker.
- **ML pipeline v2.0**: proposals and experiments to improve extraction quality, with a longer-term goal of extending the pipeline beyond glycosylation to post-translational modifications more generally (phosphorylation as the proof-of-concept).

## Repository structure

| Path | Contents |
|------|----------|
| `docs/` | Curation guidelines, decision rules, glossary |
| `curation/` | Worked examples and validation logs |
| `ml-pipeline-v2/` | Proposals, evaluation set, and design notes for v2.0 |
| `study-notes/` | *Essentials of Glycobiology* chapter walkthroughs |
| `meetings/` | Scrum and kickoff notes |
| `deliverables/` | Final report, presentation, and documentation |

## Core curation principles

A few of the filtering rules this work depends on:

- **Sequon ≠ occupancy.** An N-glycan sequon (N-X-S/T, X≠P) marks a *potential* site; only experimental evidence (e.g. the PNGase F deamidation signature in mass spec) confirms occupancy.
- **O-GalNAc has no canonical sequon**: every O-GalNAc site requires experimental confirmation.
- **Glycation ≠ glycosylation**: non-enzymatic sugar adducts are excluded as false positives.
- **Monosaccharide identity** distinguishes O-GalNAc from O-mannose, O-glucose, and O-fucose.

## Reference resources

- *Essentials of Glycobiology*, 4th ed. — [NCBI Bookshelf, NBK579927](https://www.ncbi.nlm.nih.gov/books/NBK579927/)
- [UniProt](https://www.uniprot.org/) — protein accessions
- [PubMed](https://pubmed.ncbi.nlm.nih.gov/) — source corpus
- [GlyGen](https://www.glygen.org/) — glycoinformatics resource

## Status

_Early phase (June–July). This README and the directories below are updated as work progresses._

## Deliverables

- [ ] GitHub documentation
- [ ] 1–2 page report
- [ ] Final presentation
