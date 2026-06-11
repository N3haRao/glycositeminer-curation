## GlycoSiteMiner-v2.0 Overview

The directory contains 6 Python scripts, a `conf/` folder with two JSON config files, and a large shared utility library. Together they define the **data ingestion and preprocessing front end** of the pipeline, before any ML classification happens.

---

### Structure

```
GlycoSiteMiner-v2.0/
├── conf/
│   ├── config.json          # data_dir, LLM settings, GlyGen release, species list
│   └── medline.json         # PubMed baseline/updatefiles download range
├── download-glygen.py       # Downloads GlyGen reference data
├── download-medline.py      # Downloads PubMed XML bulk files
├── download-pubtator.py     # Downloads PubTator3 NER annotations
├── download-gene-info.py    # Downloads NCBI gene_info and filters by species
├── download-pipeline-data.py # Downloads pre-built tarballs from GlyGen FTP
├── extract-known-sites.py   # Builds known_sites.csv from GlyGen glycosylation CSVs
└── util.py                  # ~1,300-line shared library
└── tasks.md                 # Instructions and tasks from Robel
```

---

### config.json: Key Settings

The LLM is configured as **GPT-4o-mini** with a structured output schema. The query prompt is:
> *"give me gene entity, protein entity, glycosylation sites, tissue, cell line and organism only using information provided in the following text"*

The schema extracts a list of objects, each with: `glycosylation_site`, `gene_entity`, `protein_entity`, `organism`, `tissue`, `cell_line`.

Species coverage: human, mouse, rat, bovine, pig, yeast, *Arabidopsis*. GlyGen sources tracked span 22 databases including UniProtKB, GlyConnect, O-GlcNAc Atlas, GlycoSMOS, PDB, and others. The GlyGen release pinned is **2.11.1**.

---

### What the Scripts Do

**download-glygen.py**: Pulls species-specific proteoform glycosylation site CSVs and protein metadata (canonical FASTA, gene locus, genenames, xref_geneid) from the GlyGen FTP. Prunes any file that doesn't contain a header row.

**download-medline.py**: Bulk-downloads PubMed XML `.gz` files for the configured baseline and updatefiles ranges. The `medline.json` currently points to files 1-10 of the 2026 baseline and update files 1335-1355. You need to update start/end to match the actual current FTP range.

**download-pubtator.py**: Pulls the full `bioconcepts2pubtator3.gz` dump from NCBI FTP. This is the NER source (genes, species, diseases, chemicals in PubMed).

**download-gene-info.py**: Downloads the complete NCBI `All_Data.gene_info.gz`, then filters it down to only the species flagged as reference in `glygen/species_info.csv`. This is what supports the gene_id → UniProt accession linking.

**download-pipeline-data.py**: Alternative to the individual downloads; pulls pre-processed tarballs directly from GlyGen's FTP (`medline_abstracts`, `medline_extracts`, `pubtator_extracts`, `llm_entities`, `gene_info`, `glygen`, `curation`, `confirmation`, `misc`). Uses `config["mode"] == "dev"` to redirect to an internal server path.

**extract-known-sites.py**: Reads all `*_proteoform_glycosylation_sites_*.csv` files under `data/glygen/`, filters to entries that have a PubMed xref, non-empty position, and single-position sites (start_pos == end_pos). Skips any site already tagged with `mining_tools = glycositeminer` (avoids circular self-reference). Outputs `known_sites.csv` with columns: `doc_id, canon, pos, amino_acid, source`. This becomes the ground-truth positive set used downstream.

---

### util.py: The Core Library

This is the real engine. Key functional groups:

**Amino acid normalization** (`get_aa_dict`, `get_aa_three`): Builds bidirectional maps between one-letter, three-letter, and full amino acid names. Used throughout parsing.

**Site text parsing** (`transform_sent`, `parse_one_word`, `parse_two_words`, `transform_llm_site`): This is the residue extraction logic. Handles formats like `N123`, `Asn123`, `Asn-123`, `Asn(123)`, `asparagine 123`, and multi-word variants. The `transform_sent` function is also where the **"C-3" ambiguity lives**; it tokenizes by splitting on spaces and tries to match amino acid names + digit patterns, so `C-3` (cysteine-3 appearance) could fire as a site parse even when it's a carbon position on a sugar. `transform_llm_site` runs LLM-extracted site strings through the same parser to normalize them to the `Xxx-NNN` format.

**Gene → UniProt linking** (`load_geneid2canon`, `load_geneid2ensg`): This is the stage responsible for the wrong-accession bug pattern that we flagged. It builds a `geneid2canon` dict through two paths: direct `xref_geneid.csv` lookup, and an indirect Ensembl bridge (`gene_info` ENSG IDs → GlyGen gene locus CSV). If the gene_id-to-ENSG mapping is wrong or the ENSG maps to multiple proteins, wrong accessions propagate downstream.

**Known sites and match logic** (`get_known_site_dict`, `get_match_dict`, `get_site_dict`): `get_match_dict` reads `enteg/site.*.json` files and builds a match dictionary keyed by `doc_id|canon|pos`, with value `"1"` (aa_match) or `"-1"` (no match). It requires `str_b != "no_glyco_ents"` before accepting a site; meaning a glyco-related entity must co-occur in the abstract for a site to be considered.

**ML sample loading** (`load_samples_labeled`, `load_samples_unlabeled`): Reads feature vectors from CSV. `load_curated_neg()` pulls human-curated rejects from `/data/shared/glycositeminer/userdata/curation/*`; this is where our curation work feeds back into the training data as synthetic negatives.

**LLM output ingestion** (`load_llm_sites`): Takes LLM JSON output, resolves organism text to tax_ids (three-tier: exact name match → two-word prefix match → curated manual map), then normalizes site strings via `transform_llm_site`. Falls back to PubTator species annotations if the LLM organism field is empty or unresolvable.

**Organism resolution** (`get_otext2taxid_dict`, `get_otext2taxid_reduced_dict`): Builds organism-text-to-taxonomy-ID mappings. The "reduced" version only looks at organisms actually seen in LLM output files; the full version does a scan of NCBI's `names.dmp`. A `curated_taxid_map.json` in the misc dir handles known edge cases.

---

### Things That Stand Out Relative to Our Work

1. **The accession bug root**: `load_geneid2canon` is the likely culprit. The ENSG bridge in particular can yield multiple canons for one gene_id with no disambiguation logic, it just adds all of them. Downstream ranking code picks whichever appears first.

2. **"C-3" parsing**: `transform_sent` and `parse_one_word` will match single-letter `C` followed by a digit under flag `1a`. There's no glyco-context filter at the parsing stage - that filtering happens later in `get_match_dict` via the `str_b != "no_glyco_ents"` gate, but if glyco terms are present in the abstract anyway (common in glycobiology papers), the bad site still passes through.

3. **`load_curated_neg` hardcodes a path** (`/data/shared/glycositeminer/userdata/curation/*`): this means our curation output needs to land in exactly that location to feed the negative training set. 

> Personal note: Worth confirming with Robel that the curation data is actually reaching that path.

4. **No `download-pipeline-data.py` mode flag in config.json**: the script checks `config["mode"] == "dev"` but the current `config.json` doesn't have a `"mode"` key, which would throw a `KeyError` at runtime. 

> Personal note: Confirm if it's likely a placeholder for a dev/prod switch that hasn't been fully wired up.

5. **LLM prompt has no glycosylation-specific instruction**: it asks for glycosylation sites but doesn't tell the model to distinguish glycosylation from phosphorylation or other PTMs, which is consistent with the tyrosine phosphorylation false-positive pattern we've been filtering manually.
