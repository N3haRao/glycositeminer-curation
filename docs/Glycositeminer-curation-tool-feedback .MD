# GlycoSiteMiner Curation Tool: Feedback and Improvement Suggestions

**Author:** Neha Rao
**Context:** GlycoSiteMiner Curation interface (PMID list, per-record curation form with Response Tables 1 to 4)
**Date:** June 2026

This document collects feedback on the curation web tool based on hands-on use. Items are grouped by theme and roughly ordered by priority. Severity tags (Critical / High / Medium / Low) are included to help with triage.

---

## 1. Data integrity and accession validation (Critical)

Wrong accessions silently poison the curated dataset, so this is a correctness issue rather than a UX nicety. A recent spike-protein record exposed the problem.

- **Validate that the pre-populated accession matches the extracted entity.** One spike abstract loaded P02686 (which is myelin basic protein) and P0C604 (which is an olfactory receptor) for a SARS-CoV-2 spike paper. The pipeline should cross-check entity to accession and flag mismatches before a record reaches a curator.
- **Validate residue identity against the canonical sequence.** The form should confirm that, for example, Thr323 is actually a threonine at position 323 in P0DTC2-1. If the residue does not match, flag it. This automatically catches isoform and numbering errors.

## 2. Flagging and escalation mechanism (High)

Currently the only way to report a broken record is to leave the tool and message someone on Slack.

- Add a **"Flag for review" button** per record (and ideally per row) with a reason dropdown: wrong accession, invalid site, not a glyco site, abstract mismatch, duplicate, other, plus a free-text box.
- Flagged records should route to a POC or dev queue and be **filterable on the home page**.
- **Distinguish two different states clearly.** "I curated this and the answer is reject / No" is very different from "this record is broken and should not be curated as-is." Right now both look like an ordinary save, but they mean different things downstream.

## 3. Dropdown logic and conditional fields (High)

- **Add "N/A" to the Tables 3 and 4 dropdowns.** When a site is "No" for glycosylation in Table 2, Tables 3 and 4 are meaningless, but the curator is forced to leave "--select," which is ambiguous (was it skipped, or is it not applicable?).
- **Better: auto-disable or grey out the Tables 3 and 4 rows when Table 2 "Glycosylated?" is set to No**, and auto-set them to N/A. This enforces the logic so a curator cannot accidentally enter contradictory data such as "not glycosylated" but "Direct evidence."
- Apply the same conditional handling to Table 2 itself: if "Ac & Site Associated?" is No, the glycosylation question is arguably moot, so that dependency should be handled too.

## 4. In-context guidance and documentation (High)

- **Per-table tooltips or expandable help text.** Each table needs a one-line definition. Table 3: "Direct = site experimentally shown to be glycosylated in this work; Indirect = inferred." Table 4: "This study versus Prior study."
- **A linked curation SOP or decision tree.** The navigation bar already has FAQ and About tabs, so populate the FAQ with the actual curation rules.
- **Spell out the key distinctions inline**, since these are the recurring traps:
  - Glycosylation versus phosphorylation (the constant decoy, for example AKT1 Tyr474 and GBF1 Tyr876/898).
  - Glycosylation versus glycation.
  - Sequon-predicted versus experimentally confirmed.
  - The fact that O-GlcNAc does count as glycosylation.
- **A "gold standard" example record** that curators can open to see a correct fill with reasoning. The AKT1 phospho-versus-glyco case would be a good choice.
- **Define the home-page columns.** What is `group_index`? How does `curated_sites` relate to `site_count`?

## 5. Home page, status, and workflow (High)

- **Explicit per-record status:** Uncurated, In progress, Completed, Flagged. The `curated_sites` count is not a clean status.
- **Two-button model:** keep "Save" for in-progress work, and add **"Mark complete / Submit"** to finalize. This separates partial saves from finished records.
- **Filtering and sorting:** filter by status (hide completed, show only uncurated or flagged), sort by `site_count`, and search by PMID.
- **A progress indicator,** for example "X of 826 records curated."

## 6. Validation before save (Medium)

- **Block "Mark complete" if any required dropdown is still "--select."**
- **Logical consistency checks.** If Glycosylated = Yes, require Evidence Type, Evidence Origin, and Supporting Text. If No, require N/A (or auto-fill it).
- **Require Supporting Text whenever a "Yes" is selected,** so every positive call is grounded in a quote.
- **Warn on unsaved changes** when navigating away from a record.

## 7. Supporting Text field (Medium)

- **Let curators highlight text directly in the displayed abstract to populate the field.** This removes copy-paste errors and guarantees a verbatim quote.
- **Auto-suggest the sentence the pipeline matched the site to** as a starting point.
- Allow multi-line entry and show a character count.

## 8. Surface pipeline context (Medium)

This item doubles as ML feedback and feeds directly into the v2.0 pipeline work.

- For each extracted site, **show why it was pulled:** the matched sentence, the predicted modification type (N-glycan, O-glycan, or phospho), and the confidence score.
- Showing the **predicted modification type** would let a curator instantly spot a phospho decoy without re-reading the whole abstract.
- Display the **residue, position, and surrounding sequence context.**
- Bonus: curator corrections captured here become labeled training signal for the active-learning loop.

## 9. Typos and polish 

- "Resonse" should be "Response" (Table-1 header).
- "PMID List fo Curation" should be "for."
- "identified bythe GlycoSiteMiner pipeline" should be "by the."
- Site notation is inconsistent between the abstract ("T - 323") and the tables ("Thr323"). This is acceptable, but worth a note so curators know they map to the same residue.
- The `GSM_0000001` breadcrumb is opaque. Label what it represents.

## 10. Audit trail and export (Medium / Low)

- **Timestamp, curator ID, and edit history** per saved curation.
- **Confirm the DOWNLOADS tab exports the full response tables,** not just the PMID list. The response tables are the actual deliverable for GlyGen ingestion.
- Version each curation against the pipeline version that produced the record.

## 11. Speed and accessibility (Nice-to-have)

- Clean **tab order** through dropdowns and text fields for fast keyboard-driven curation.
- A **bulk action** to set all rejected rows' Tables 3 and 4 to N/A at once.
- Auto-save drafts.

---

## Priority summary

| Priority | Items |
|----------|-------|
| Critical | Accession and residue validation (Section 1) |
| High | Flagging mechanism (2), conditional dropdown logic (3), in-context guidance (4), status and workflow (5) |
| Medium | Save-time validation (6), supporting text capture (7), pipeline context (8), audit and export (10) |
| Low | Typos and polish (9), speed and accessibility (11) |
