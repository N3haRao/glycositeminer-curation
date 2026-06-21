import os
import sys
import json
import glob
import subprocess


def main():

    DEBUG = False
    #DEBUG = True

    config_obj = json.loads(open("conf/config.json", "r").read())

    pattern = "*"
    if DEBUG:
        pattern = "pubmed23n000*"

    xml_dir = config_obj["data_dir"] + "medline_xml/"
    xml_file_list = sorted(glob.glob(xml_dir + "/%s.xml.gz" % (pattern)))
    n = len(xml_file_list)

    # I split the full file list into up to 12 equal batches so each worker
    # only handles a manageable slice of the 807 XML files
    batch_size = int(len(xml_file_list) / 10) if len(xml_file_list) > 10 else len(xml_file_list)
    range_list = []
    for i in range(0, 12):
        s = i * batch_size + 1
        e = s + batch_size
        if e >= n:
            e = n
            range_list.append({"s": s, "e": e})
            break
        range_list.append({"s": s, "e": e})

    # I use subprocess.Popen instead of os.system("nohup python3 ... &") because
    # nohup and & are Unix-only and will fail silently on Windows
    python_exe = sys.executable
    procs = []
    for o in range_list:
        cmd = [python_exe, "extract-medline-data.py", "-s", str(o["s"]), "-e", str(o["e"])]
        proc = subprocess.Popen(cmd)
        procs.append(proc)
        print("Launched worker: start=%s end=%s (pid=%s)" % (o["s"], o["e"], proc.pid))

    # I wait for all workers to finish before returning so the caller knows
    # when the full extraction is complete
    for proc in procs:
        proc.wait()

    print("All workers finished.")
    return


if __name__ == '__main__':
    main()
