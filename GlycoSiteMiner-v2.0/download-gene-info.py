import sys,os
import json
import glob
import gzip
import subprocess
from optparse import OptionParser


def main():

    global config_obj
    config_obj = json.loads(open("conf/config.json", "r").read())

    source = "gene_info"
    # create dir if doesn't exist    
    if os.path.isdir(config_obj["data_dir"] + source) == False:
        cmd = "mkdir -p " + config_obj["data_dir"] + source
        x = subprocess.getoutput(cmd)

    out_file = config_obj["data_dir"] + "glygen/species_info.csv"
    tax_id_dict = {}
    with open (out_file, "r") as FR:
        for line in FR:
            row = line.strip().split(",")
            # is_reference is 3rd from last; row[-2] is sort_order
            if row[-3] == "yes":
                tax_id_dict[row[0].strip()] = True

    url = "https://ftp.ncbi.nlm.nih.gov/gene/DATA/GENE_INFO/All_Data.gene_info.gz"
    
    gz_file = config_obj["data_dir"] + "gene_info/tmp.gene_info.gz"
    cmd = "curl %s -o %s " % (url, gz_file)
    x = subprocess.getoutput(cmd)

    # decompress using Python's gzip module so this works on Windows too
    in_file = config_obj["data_dir"] + "gene_info/tmp.gene_info"
    with gzip.open(gz_file, "rb") as FZ, open(in_file, "wb") as FD:
        FD.write(FZ.read())
    os.remove(gz_file)
    out_file = config_obj["data_dir"] + "gene_info/All_Data.gene_info"
    
    FW = open(out_file, "w")
    with open (in_file, "r") as FR:
        for line in FR:
            # skip comment/header lines
            if line.startswith("#"):
                continue
            tax_id = line.split("\t")[0].strip()
            if tax_id in tax_id_dict:
                FW.write(line)
    FW.close()
    os.remove(in_file)

    cmd = "chmod -R 777 " + config_obj["data_dir"] + "/" + source
    x = subprocess.getoutput(cmd)
   




if __name__ == '__main__':
    main()


