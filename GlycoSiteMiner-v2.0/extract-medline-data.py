import os
import sys
import gzip
import json
import glob
import pubmed_parser as pp
import re

import spacy
from optparse import OptionParser
import util


def main():

    usage = "\n%prog  [options]"
    parser = OptionParser(usage, version="%prog version___")
    parser.add_option("-s", "--start", action="store", dest="start", help="")
    parser.add_option("-e", "--end", action="store", dest="end", help="")

    (options, args) = parser.parse_args()
    for key in ([options.start, options.end]):
        if not (key):
            parser.print_help()
            sys.exit(0)

    global pmid_dict

    config_obj = json.loads(open("conf/config.json", "r").read())

    start_idx = int(options.start)
    end_idx = int(options.end)
    xml_dir = config_obj["data_dir"] + "medline_xml/"
    out_dir_one = config_obj["data_dir"] + "medline_extracts/"
    out_dir_two = config_obj["data_dir"] + "medline_abstracts/"
    log_dir = config_obj["data_dir"] + "logs/"
    log_file = log_dir + "medline_abstracts.%s.%s.log" % (start_idx, end_idx)

    DEBUG = False
    #DEBUG = True
    if DEBUG:
        file_list = [xml_dir + "/pubmed23n0349.xml.gz"]
        debug_doc_id_list = ["10531415"]
        out_dir_one = "tmp/medline_extracts/"
        out_dir_two = "tmp/medline_abstracts/"

    # I use os.makedirs with exist_ok=True instead of "mkdir -p" via subprocess
    # because mkdir -p is a Unix command and silently fails on Windows
    os.makedirs(out_dir_one, exist_ok=True)
    os.makedirs(out_dir_two, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)

    # I load the spaCy EntityRuler with glyco.json, which combines SITE and
    # GLYCOSYLATION patterns so I can filter abstracts to only glyco-relevant ones
    nlp = spacy.blank("en")
    patterns_json_file = "misc/glyco.json"
    ruler = nlp.add_pipe("entity_ruler")
    pattern_obj_list = json.loads(open(patterns_json_file, "r", encoding="utf-8").read())
    ruler.add_patterns(pattern_obj_list)
    nlp.add_pipe("sentencizer")

    SPACE_PATTERN = re.compile(r'[\s][\s]+')
    with open(log_file, "w", encoding="utf-8") as FL:
        FL.write("Started logging\n")

    file_list = sorted(glob.glob(xml_dir + "/*.xml.gz"))
    aa_dict = util.get_aa_dict("misc/")
    end_idx = len(file_list) if end_idx > len(file_list) else end_idx

    for gz_xml_file in file_list[start_idx - 1:end_idx]:
        if not gz_xml_file.endswith(".gz"):
            continue

        # I use os.path.basename instead of split("/")[-1] because Windows paths
        # use backslashes and the slash split would return the full path
        file_name = os.path.basename(gz_xml_file).replace(".xml.gz", "")
        dicts_out = pp.parse_medline_xml(gz_xml_file)
        n_found = 0
        idx = 0

        for obj in dicts_out:
            if "pmid" not in obj:
                continue
            if obj["pmid"] == "":
                continue
            if "abstract" not in obj:
                continue
            if obj["abstract"] == "":
                continue
            doc_id = obj["pmid"]

            if DEBUG:
                if doc_id not in debug_doc_id_list:
                    continue

            if idx % 1000 == 0:
                with open(log_file, "a", encoding="utf-8") as FL:
                    FL.write("checked %s PMIDs, %s found from %s\n" % (idx, n_found, gz_xml_file))
            idx += 1

            title_text, abstract_text = obj["title"], obj["abstract"]
            mesh = obj["mesh_terms"]
            publication_types = obj["publication_types"]

            # I combine title and abstract into one string then collapse extra whitespace
            text = "{} {}".format(title_text, abstract_text).strip()
            text = re.sub(SPACE_PATTERN, " ", text)
            doc = {"docId": doc_id, "text": text}
            if len(title_text) > 0:
                doc["title"] = {"charStart": 0, "charEnd": len(title_text) - 1}
            if len(publication_types) > 0:
                doc["type"] = publication_types
            if len(mesh) > 0:
                doc["mesh"] = mesh

            tmp_doc = nlp(doc["text"])
            sent_list = [sent.text.strip() for sent in tmp_doc.sents]
            sent_obj_list = []
            doc2lbl = {}
            sent_idx = 0

            for sent in sent_list:
                sent_idx += 1
                # I normalize residue patterns in each sentence (e.g. Asn123 -> Asn - 123)
                # before running the entity ruler so patterns match consistently
                sent = util.transform_sent(sent, aa_dict)
                sent_doc = nlp(sent)
                entities = []
                seen_lbl = {}
                for ent in sent_doc.ents:
                    entities.append({
                        "start": ent.start_char,
                        "end": ent.end_char,
                        "label": ent.label_,
                        "text": ent.text
                    })
                    doc2lbl[ent.label_] = True
                    seen_lbl[ent.label_] = True
                if "SITE" in seen_lbl or "GLYCOSYLATION" in seen_lbl:
                    sent_obj_list.append({
                        "sentence": sent,
                        "sentence_idx": sent_idx,
                        "entities": entities
                    })

            # I only write output when the abstract has both a SITE and a GLYCOSYLATION
            # entity somewhere in it, which filters out non-glycosylation papers
            if len(sent_obj_list) > 0 and "SITE" in doc2lbl and "GLYCOSYLATION" in doc2lbl:
                n_found += 1
                out_doc = {"doc_id": doc_id, "sent_list": sent_obj_list}
                out_file = out_dir_one + "pmid.%s.json" % (doc_id)
                with open(out_file, "w", encoding="utf-8") as FW:
                    FW.write("%s\n" % (json.dumps(out_doc, indent=4)))
                out_file = out_dir_two + "pmid.%s.txt" % (doc_id)
                with open(out_file, "w", encoding="utf-8") as FW:
                    FW.write("%s\n" % (doc["text"]))
                if DEBUG:
                    print("created file:%s\n" % (out_file))

        with open(log_file, "a", encoding="utf-8") as FL:
            FL.write("final %s found from %s\n" % (n_found, gz_xml_file))

    return


if __name__ == '__main__':
    main()
