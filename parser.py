import json
import requests

from biothings import config
logger = config.logger

def load_filenames():
    r = requests.get('https://raw.githubusercontent.com/outbreak-info/covid19_LST_report_data/main/reportlist.txt')
    reportlist=r.text.split('\n')
    formattedlist = [x.replace(" ","%20") for x in reportlist]
    return(formattedlist)

def load_annotations()
    basejsonurl = 'https://raw.githubusercontent.com/outbreak-info/covid19_LST_report_data/main/json/'
    formattedlist = load_filenames()
    for eachjson in formattedlist:
        fileurl = basejsonurl+eachjson
        rawdoc = requests.get(fileurl)
        doc = json.loads(rawdoc.text)
        yield doc