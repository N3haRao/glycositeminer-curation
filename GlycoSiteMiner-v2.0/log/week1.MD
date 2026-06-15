# GlycoSiteMiner-v2.0 Weekly Update

## Overview


I worked through the full data download and preprocessing pipeline for GlycoSiteMiner-v2.0, completing Steps 1 and 2 from `tasks.md`. 

---

## Step 1: Data Download

### Setup

Before running anything, I explored the full codebase to understand the pipeline architecture, then made two configuration changes:

**`conf/medline.json`**: The file had placeholder values for the PubMed FTP file ranges. I fetched the live FTP directories at `https://ftp.ncbi.nlm.nih.gov/pubmed/baseline/` and `https://ftp.ncbi.nlm.nih.gov/pubmed/updatefiles/` and updated the ranges to match the current 2026 release:
- Baseline end: `10` updated to `657`
- Updatefiles end: `1355` updated to `1484`

### Downloads

I ran all four download scripts, each targeting a different data source. Here is what each one fetched and any issues I encountered:

**GlyGen (`download-glygen.py`)**

The first run failed because `mkdir -p` is a Unix command and does not work on Windows, so the `data/glygen/` directory was never created and curl had nowhere to write. I created all four required directories manually (`data/glygen/`, `data/medline_xml/`, `data/pubtator_downloads/`, `data/gene_info/`) and reran the script. It completed successfully and downloaded 174 files covering FASTA sequences, gene locus files, gene name crossreferences, gene ID crossreferences, and glycosylation site CSVs for all configured species.

Species covered: human, mouse, rat, pig, bovine, chicken, hamster, arabidopsis, yeast, zebrafish, fruitfly, dicty, sarscov1, sarscov2, hcv1a, hcv1b.

**PubTator3 (`download-pubtator.py`)**

This ran without issues and downloaded the full `bioconcepts2pubtator3.gz` NER annotation dump. Final size: 5.7 GB.

**NCBI Gene Info (`download-gene-info.py`)**

1. The script called `gunzip` via `subprocess.getoutput()` to decompress the downloaded `.gz` file. On Windows, `gunzip` does not exist, so the call failed silently, leaving the file compressed. When the script tried to open the decompressed file, it crashed with `FileNotFoundError`. I replaced the `gunzip` call with Python's built-in `gzip` module, which works cross-platform.

2. After the decompression fix, the script ran but produced an empty `All_Data.gene_info` (0 bytes). I traced this to a stale column index: the script read `species_info.csv` and checked `row[-2]` to identify reference species, but the CSV had gained a new ninth column (`main_xref_ds`) since the index was written. This shifted `is_reference` from position `-2` to `-3`, so the `tax_id_dict` was always empty and nothing passed the filter. I corrected the index to `row[-3]`.

3. I also added a skip for header lines starting with `#` in the raw gene_info file, since NCBI's format includes a `#tax_id` comment line at the top that would otherwise be processed as a data row.

4. Added cleanup of the temporary files (`tmp.gene_info.gz` and `tmp.gene_info`) after filtering is complete.

Final output: `All_Data.gene_info` at 118 MB containing 648,034 gene records across 16 reference species, filtered down from a 9.4 GB source file.

**PubMed Medline (`download-medline.py`)**

This script downloads 807 XML files (657 baseline + 150 updatefiles). I paused it mid-run and when I resumed, the script was restarting from file 1 and re-downloading files that were already on disk. I fixed this by adding a check that skips any file already present at the output path before calling curl. This way the script can always be safely resumed without wasted bandwidth.

Final output: 807 `.xml.gz` files in `data/medline_xml/`.

---

## Step 2: Extract Known Sites

`extract-known-sites.py` crashed immediately with a `UnicodeDecodeError`. On Windows, Python defaults to the `cp1252` encoding when opening files without an explicit encoding, and one of the GlyGen CSVs contained a byte (`0x9d`) that `cp1252` cannot decode. I fixed this by:

1. Adding `encoding="utf-8", errors="ignore"` to the input file open call.
2. Adding `encoding="utf-8"` to the output file open call.
3. Replacing `in_file.split("/")[-1]` with `os.path.basename(in_file)` to correctly extract the filename on Windows, where paths use backslashes.
4. Adding `import os` which was missing from the script.

### Output

The script completed successfully and produced `data/glygen/known_sites.csv` with 312,064 known glycosylation site records. Each record contains a PubMed ID, UniProt canonical accession, residue position, amino acid, and source dataset.

---

## Files Downloaded Summary

| Dataset | Location | Count / Size |
|---|---|---|
| GlyGen reference files | `data/glygen/` | 174 files |
| PubTator3 NER dump | `data/pubtator_downloads/` | 5.7 GB |
| NCBI gene info (filtered) | `data/gene_info/All_Data.gene_info` | 118 MB, 648,034 records |
| PubMed XML files | `data/medline_xml/` | 807 files |
| Known glycosylation sites | `data/glygen/known_sites.csv` | 312,064 records |

---

## Scripts Modified Summary

| Script | Changes |
|---|---|
| `conf/medline.json` | Updated baseline end from 10 to 657, updatefiles end from 1355 to 1484 |
| `download-gene-info.py` | Replaced `gunzip` shell call with Python `gzip` module; fixed `is_reference` column index from `row[-2]` to `row[-3]`; added header line skip; added temp file cleanup; added `import gzip` |
| `download-medline.py` | Added file existence check to skip already-downloaded files, enabling safe resume |
| `extract-known-sites.py` | Added UTF-8 encoding to all file opens; replaced `split("/")[-1]` with `os.path.basename()`; added `import os` |
