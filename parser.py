import json
import os

from biothings import config
from config import DATA_ARCHIVE_ROOT
logger = config.logger

def load_annotations()
    filenames = os.listdir(SRC_ROOT_FOLDER)
    for eachjson in filenames:
        filepath = os.path.join(SRC_ROOT_FOLDER,eachjson)
        with open(filepath,'r') as rawdoc
            doc = json.loads(rawdoc)
            yield doc