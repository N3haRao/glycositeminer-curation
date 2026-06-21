import os
import sys
import string
import glob
import json
import datetime
import gzip
import subprocess

__version__ = "1.0"
__status__ = "Dev"


def main():

    config_obj = json.loads(open("conf/config.json", "r").read())

    # I corrected the filename here: the file downloaded in Step 1 is
    # bioconcepts2pubtator3.gz, not bioconcepts2pubtatorcentral.offset.gz
    gz_file = config_obj["data_dir"] + "pubtator_downloads/bioconcepts2pubtator3.gz"
    medline_abstracts_dir = config_obj["data_dir"] + "medline_abstracts/"
    pubtator_extracts_dir = config_obj["data_dir"] + "pubtator_extracts/"
    log_file = config_obj["data_dir"] + "logs/pubtator_extracts.log"

    # I use os.makedirs with exist_ok=True instead of "mkdir -p" via subprocess
    # because mkdir -p is a Unix command and silently fails on Windows
    os.makedirs(pubtator_extracts_dir, exist_ok=True)

    # I also create the logs directory here because the original script tried to
    # write the log file before anything created that directory
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    # I build a lookup of every PMID that made it through the medline extraction step.
    # Only PubTator blocks for these PMIDs need to be saved.
    # I use os.path.basename instead of split("/")[-1] so this works on Windows too
    pmid_dict = {}
    for in_file in glob.glob(medline_abstracts_dir + "pmid.*.txt"):
        doc_id = os.path.basename(in_file).split(".")[-2]
        pmid_dict[doc_id] = True

    total_common_count = len(pmid_dict)
    with open(log_file, "w", encoding="utf-8") as FL:
        FL.write("")

    common_count, pubtator_count = 0, 0
    prev_pmid = ""
    buf = ""

    with gzip.open(gz_file, "r") as fin:
        for line in fin:
            line = line.decode("utf-8", errors="ignore")
            if line.strip() == "":
                continue

            # PubTator lines are either "PMID|t|..." / "PMID|a|..." or tab-separated
            # annotations. Either way the PMID is the first whitespace-delimited token
            pmid = line.split("|")[0].split()[0]

            if prev_pmid != "" and pmid != prev_pmid:
                # The previous PMID's block is now complete. I check prev_pmid (not pmid)
                # because I am deciding whether to write the block I just finished collecting,
                # not the one I am about to start. The original code checked pmid here by
                # mistake, which caused the wrong PMID's data to be written and the buffer
                # to grow without bound for unmatched PMIDs.
                pubtator_count += 1
                if prev_pmid in pmid_dict:
                    out_file = pubtator_extracts_dir + "pmid.%s.txt" % (prev_pmid)
                    with open(out_file, "w", encoding="utf-8") as FW:
                        FW.write("%s\n" % (buf))
                    common_count += 1

                # I always reset the buffer when the PMID changes, regardless of whether
                # I wrote the previous block. The original code only reset buf inside the
                # "if pmid in pmid_dict" branch, so unmatched PMIDs kept accumulating lines.
                buf = ""

                if pubtator_count % 10000 == 0:
                    with open(log_file, "a", encoding="utf-8") as FL:
                        FL.write("parsed %s pubtator PMIDs, found %s/%s of medline extracts\n" % (
                            pubtator_count, common_count, total_common_count))

            # I accumulate every line into the buffer unconditionally so the full
            # annotation block for each PMID is captured before I decide whether to keep it
            buf += line
            prev_pmid = pmid

    # I flush the very last PMID's buffer after the loop ends, checking that it is
    # one we actually want before writing. The original code always wrote the last
    # block even when it was not in pmid_dict.
    if prev_pmid != "":
        pubtator_count += 1
        if prev_pmid in pmid_dict:
            out_file = pubtator_extracts_dir + "pmid.%s.txt" % (prev_pmid)
            with open(out_file, "w", encoding="utf-8") as FW:
                FW.write("%s\n" % (buf))
            common_count += 1

    with open(log_file, "a", encoding="utf-8") as FL:
        FL.write("finished parsing %s pubtator PMIDs, found %s/%s of medline extracts\n" % (
            pubtator_count, common_count, total_common_count))

    return


if __name__ == '__main__':
    main()
