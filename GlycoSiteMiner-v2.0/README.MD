## GlycoSiteMiner-v2.0 Overview

The directory contains Python scripts, a `conf/` folder with two JSON config files, a `misc/` folder with spaCy NER pattern files, and a large shared utility library. Together they define the **data ingestion and preprocessing front end** of the pipeline, before any ML classification happens.

---

### Structure

```
GlycoSiteMiner-v2.0/
├── conf/
│   ├── config.json                  # data_dir, LLM settings, GlyGen release, species list
│   └── medline.json                 # PubMed baseline/updatefiles download range
├── misc/
│   ├── aa.csv                       # Amino acid one/three/full name mappings
│   ├── glyco.json                   # Combined spaCy EntityRuler patterns (156 total)
│   ├── glycosylation_patterns.json  # 26 GLYCOSYLATION label patterns
│   ├── site_patterns.json           # 36 SITE label patterns
│   ├── phosphorylation_patterns.json# 31 PHOSPHORYLATION label patterns
│   ├── acetylation_patterns.json    # 8 ACETYLATION label patterns
│   ├── methylation_patterns.json    # 10 METHYLATION label patterns
│   ├── ubiquitination_patterns.json # 8 UBIQUITINATION label patterns
│   ├── species_map.json             # 16 reference species tax_id to name mappings
│   └── species_common_name.json     # 16 common name entries
├── log/                             # Weekly coding log
├── download-glygen.py               # Downloads GlyGen reference data
├── download-medline.py              # Downloads PubMed XML bulk files
├── download-pubtator.py             # Downloads PubTator3 NER annotations
├── download-gene-info.py            # Downloads NCBI gene_info and filters by species
├── download-pipeline-data.py        # Downloads pre-built tarballs from GlyGen FTP
├── extract-known-sites.py           # Builds known_sites.csv from GlyGen glycosylation CSVs
├── wrap-extract-medline-data.py     # Parallel wrapper for extract-medline-data.py
├── extract-medline-data.py          # Parses PubMed XML and extracts glyco-relevant abstracts
├── extract-pubtator-data.py         # Extracts PubTator3 annotations for matched PMIDs
├── util.py                          # ~1,300-line shared library
└── tasks.md                         # Instructions and tasks from Robel
```

---

### config.json: Key Settings

The LLM is configured as **GPT-4o-mini** with a structured output schema. The query prompt is:
> *"give me gene entity, protein entity, glycosylation sites, tissue, cell line and organism only using information provided in the following text"*

The schema extracts a list of objects, each with: `glycosylation_site`, `gene_entity`, `protein_entity`, `organism`, `tissue`, `cell_line`.

Species coverage: human, mouse, rat, bovine, pig, yeast, *Arabidopsis*. GlyGen sources tracked span 22 databases including UniProtKB, GlyConnect, O-GlcNAc Atlas, GlycoSMOS, PDB, and others. The GlyGen release pinned is **2.11.1**.

---

### What the Scripts Do

**download-glygen.py**: Pulls species-specific proteoform glycosylation site CSVs and protein metadata (canonical FASTA, gene locus, genenames, xref_geneid) from the GlyGen FTP. Prunes any file that does not contain a header row.

**download-medline.py**: Bulk-downloads PubMed XML `.gz` files for the configured baseline and updatefiles ranges. The `medline.json` currently points to files 1-657 of the 2026 baseline and updatefiles 1335-1484, matching the live NCBI FTP as of June 2026. The script skips files already present on disk so it can be safely paused and resumed without re-downloading.

**download-pubtator.py**: Pulls the full `bioconcepts2pubtator3.gz` dump from NCBI FTP. This is the NER source for genes, species, diseases, and chemicals in PubMed.

**download-gene-info.py**: Downloads the complete NCBI `All_Data.gene_info.gz`, then filters it down to only the species flagged as reference in `glygen/species_info.csv`. This supports the gene_id to UniProt accession linking. Decompression uses Python's built-in `gzip` module rather than a shell call, so it works cross-platform.

**download-pipeline-data.py**: Alternative to the individual downloads; pulls pre-processed tarballs directly from GlyGen's FTP (`medline_abstracts`, `medline_extracts`, `pubtator_extracts`, `llm_entities`, `gene_info`, `glygen`, `curation`, `confirmation`, `misc`). Note: this script checks `config["mode"] == "dev"` but `config.json` does not currently include a `"mode"` key, so it will throw a `KeyError` at runtime until that is added.

**extract-known-sites.py**: Reads all `*_proteoform_glycosylation_sites_*.csv` files under `data/glygen/`, filters to entries that have a PubMed xref, non-empty position, and single-position sites (start_pos == end_pos). Skips any site already tagged with `mining_tools = glycositeminer` to avoid circular self-reference. Outputs `known_sites.csv` with columns: `doc_id, canon, pos, amino_acid, source`. This becomes the ground-truth positive set used downstream.

**wrap-extract-medline-data.py**: Splits the full list of XML files into up to 12 equal batches and launches a parallel `extract-medline-data.py` worker for each batch using `subprocess.Popen`. Waits for all workers to finish before returning.

**extract-medline-data.py**: The core Step 3 worker. For each PubMed XML file in its assigned batch it parses abstracts with `pubmed_parser`, runs spaCy's EntityRuler using `misc/glyco.json` patterns to detect glycosylation-relevant sentences, normalizes residue patterns through `util.transform_sent`, and only keeps abstracts where both a `SITE` and a `GLYCOSYLATION` entity co-occur. Writes two outputs per matching PMID: a structured JSON to `medline_extracts/` and plain text to `medline_abstracts/`.

**extract-pubtator-data.py**: Streams through `bioconcepts2pubtator3.gz`, matches PMIDs against those found in `medline_abstracts/`, and writes the PubTator annotation block for each match to `pubtator_extracts/`. This is Step 4.

---

### misc/: The Pattern Library

`glyco.json` is the file actually loaded at runtime by `extract-medline-data.py`. It is a combined spaCy EntityRuler pattern list with 156 entries covering SITE, GLYCOSYLATION, PHOSPHORYLATION, ACETYLATION, METHYLATION, and UBIQUITINATION labels. The individual `*_patterns.json` files are the source components.

The SITE and GLYCOSYLATION labels are what Step 3 uses to decide which abstracts are glycosylation-relevant. An abstract must have at least one entity of each label somewhere in its text to pass through.

---

### util.py: The Core Library

This is the real engine. Key functional groups:

**Amino acid normalization** (`get_aa_dict`, `get_aa_three`): Builds bidirectional maps between one-letter, three-letter, and full amino acid names. Used throughout parsing.

**Site text parsing** (`transform_sent`, `parse_one_word`, `parse_two_words`, `transform_llm_site`): This is the residue extraction logic. Handles formats like `N123`, `Asn123`, `Asn-123`, `Asn(123)`, `asparagine 123`, and multi-word variants. The `transform_sent` function is also where the **"C-3" ambiguity lives**; it tokenizes by splitting on spaces and tries to match amino acid names followed by digit patterns, so `C-3` (a carbon position on a sugar) could still fire as a site parse. `transform_llm_site` runs LLM-extracted site strings through the same parser to normalize them to the `Xxx-NNN` format.

**Gene to UniProt linking** (`load_geneid2canon`, `load_geneid2ensg`): This is the stage responsible for the wrong-accession bug pattern. It builds a `geneid2canon` dict through two paths: direct `xref_geneid.csv` lookup, and an indirect Ensembl bridge (gene_info ENSG IDs to GlyGen gene locus CSV). If the gene_id-to-ENSG mapping is stale or the ENSG maps to multiple proteins, wrong accessions propagate downstream with no disambiguation.

**Known sites and match logic** (`get_known_site_dict`, `get_match_dict`, `get_site_dict`): `get_match_dict` reads `enteg/site.*.json` files and builds a match dictionary keyed by `doc_id|canon|pos`, with value `"1"` (aa_match) or `"-1"` (no match). It requires `str_b != "no_glyco_ents"` before accepting a site, meaning a glyco-related entity must co-occur in the abstract for a site to be considered.

**ML sample loading** (`load_samples_labeled`, `load_samples_unlabeled`): Reads feature vectors from CSV. `load_curated_neg()` pulls human-curated rejects from `/data/shared/glycositeminer/userdata/curation/*`; this is where curation work feeds back into the training data as synthetic negatives.

**LLM output ingestion** (`load_llm_sites`): Takes LLM JSON output, resolves organism text to tax_ids via a three-tier lookup (exact name match, two-word prefix match, curated manual map), then normalizes site strings via `transform_llm_site`. Falls back to PubTator species annotations if the LLM organism field is empty or unresolvable.

**Organism resolution** (`get_otext2taxid_dict`, `get_otext2taxid_reduced_dict`): Builds organism-text-to-taxonomy-ID mappings. The reduced version only looks at organisms actually seen in LLM output files; the full version does a scan of NCBI's `names.dmp`. A `curated_taxid_map.json` in the misc directory handles known edge cases.

---

### Known Issues

1. **Wrong accession root cause**: `load_geneid2canon` in `util.py` is the likely culprit. The Ensembl bridge can yield multiple canons for one gene_id with no disambiguation logic; all of them get added and downstream ranking picks whichever appears first.

2. **"C-3" false positives**: `transform_sent` and `parse_one_word` will match single-letter `C` followed by a digit under flag `1a`. There is no glyco-context filter at the parsing stage. That filtering happens later in `get_match_dict` via the `str_b != "no_glyco_ents"` gate, but if glyco terms are present in the abstract anyway (common in glycobiology papers), the bad site still passes through.

3. **Hardcoded curation path**: `load_curated_neg` expects curation output at `/data/shared/glycositeminer/userdata/curation/*`. Curation data must land in exactly that location to feed the negative training set. Worth confirming with Robel that the curation pipeline is writing there.

4. **Missing `mode` key in config.json**: `download-pipeline-data.py` checks `config["mode"] == "dev"` but `config.json` does not have a `"mode"` key. This will throw a `KeyError` at runtime. Likely a placeholder for a dev/prod switch not yet fully wired up.

5. **LLM prompt is not PTM-specific**: The prompt asks for glycosylation sites but does not instruct the model to distinguish glycosylation from phosphorylation or other PTMs. This is consistent with the tyrosine phosphorylation false-positive pattern seen during manual curation.

---

### Bugs Fixed (June 2026)

| Script | Bug | Fix |
|---|---|---|
| `conf/medline.json` | Baseline range was 1-10 and updatefiles was 1335-1355, both stale placeholders | Updated to baseline 1-657 and updatefiles 1335-1484 to match the live 2026 NCBI FTP |
| `download-medline.py` | Script always restarted from file 1, re-downloading everything on resume | Added a check to skip files that already exist on disk |
| `download-gene-info.py` | `gunzip` shell command does not exist on Windows; decompression failed silently and the script crashed on the missing output file | Replaced `subprocess.getoutput("gunzip ...")` with Python's built-in `gzip` module |
| `download-gene-info.py` | `species_info.csv` gained a ninth column (`main_xref_ds`), shifting `is_reference` from `row[-2]` to `row[-3]`; `tax_id_dict` was always empty, producing a 0-byte output file | Corrected column index to `row[-3]` |
| `download-gene-info.py` | NCBI gene_info file has a `#tax_id` header line that was being processed as a data row | Added a skip for lines starting with `#` |
| `download-gene-info.py` | Temporary files `tmp.gene_info.gz` and `tmp.gene_info` were left on disk after filtering | Added cleanup with `os.remove()` after each step |
| `extract-known-sites.py` | Python defaulted to `cp1252` on Windows when reading GlyGen CSVs; byte `0x9d` in one file caused a `UnicodeDecodeError` | Added `encoding="utf-8", errors="ignore"` to all file open calls |
| `extract-known-sites.py` | `in_file.split("/")[-1]` does not extract the filename correctly on Windows | Replaced with `os.path.basename(in_file)` |
| `extract-known-sites.py` | `import os` was missing | Added `import os` |
| `wrap-extract-medline-data.py` | Used `os.system("nohup python3 ... &")` which does not work on Windows | Replaced with `subprocess.Popen` using `sys.executable`; added `proc.wait()` to block until all workers finish |
| `extract-medline-data.py` | All three directory creation calls used `mkdir -p` via subprocess, which silently fails on Windows | Replaced with `os.makedirs(..., exist_ok=True)` |
| `extract-medline-data.py` | `gz_xml_file.split("/")[-1]` does not work on Windows paths | Replaced with `os.path.basename(gz_xml_file)` |
| `extract-medline-data.py` | Inner loop variable `obj` shadowed the outer abstract `obj` from `pubmed_parser` | Renamed inner variable to `sent_doc` |
| `extract-medline-data.py` | File opens had no encoding specified; would fail on Windows with non-ASCII content | Added `encoding="utf-8"` to all file opens |
| `extract-pubtator-data.py` | Wrong input filename: script looked for `bioconcepts2pubtatorcentral.offset.gz` but Step 1 downloads `bioconcepts2pubtator3.gz` | Corrected the filename |
| `extract-pubtator-data.py` | Buffer check used `if pmid in pmid_dict` (the new PMID) instead of `if prev_pmid in pmid_dict` (the completed block); caused wrong files to be written | Changed to `prev_pmid in pmid_dict` |
| `extract-pubtator-data.py` | `buf = ""` was only reset inside the matched-PMID branch, so unmatched PMIDs kept accumulating lines into the buffer indefinitely | Moved `buf = ""` outside the inner if block so it resets on every PMID change |
| `extract-pubtator-data.py` | `buf += line` was inside the PMID-change block, so the first line of every new PMID was lost when the previous PMID was unmatched | Moved `buf += line` outside the PMID-change block so every line is always accumulated |
| `extract-pubtator-data.py` | Post-loop flush always wrote the last PMID's buffer even when it was not in `pmid_dict` | Added `prev_pmid in pmid_dict` check before writing |
| `extract-pubtator-data.py` | `logs/` directory was never created before the script tried to write the log file | Added `os.makedirs` for both `pubtator_extracts/` and `logs/` |
| `extract-pubtator-data.py` | `in_file.split("/")[-1]` does not work on Windows paths | Replaced with `os.path.basename(in_file)` |
| `extract-pubtator-data.py` | File opens had no encoding specified | Added `encoding="utf-8"` to all file opens |
