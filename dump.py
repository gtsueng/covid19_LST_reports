import os
import requests
from urllib.parse import urljoin
from biothings.hub.dataload.dumper import HTTPDumper

import biothings, config
biothings.config_for_app(config)
from config import DATA_ARCHIVE_ROOT

import biothings.hub.dataload.dumper


class LSTDumper(HTTPDumper):
    SRC_NAME = "covid19_LST_reports"
    __metadata__ = {
        "src_meta": {
            "author": {
                "name": "Ginger Tsueng",
                "url": "https://github.com/gtsueng"
            },
            "code": {
                "branch": "main",
                "repo": "https://github.com/outbreak-info/covid19_LST_reports.git"
            },
            "url": "https://www.covid19lst.org/",
            "license": "http://creativecommons.org/licenses/by-nc-sa/4.0/"
        }
    }
    _JSON_URL_BASE = 'https://raw.githubusercontent.com/outbreak-info/covid19_LST_report_data/main/json/'

    def create_todump_list(self, force=False, **kwargs):
        r = requests.get(
            'https://raw.githubusercontent.com/outbreak-info/covid19_LST_report_data/main/reportlist.txt')
        reportlist = r.text.split('\n')
        for list_item in reportlist:
            remote_path = urljoin(self._JSON_URL_BASE, list_item)
            self.to_dump.append(
                {
                    'remote': remote_path,
                    'local': list_item
                }
            )
        self.release = "2021.08"  # set to some sane value
    
    # override in subclass accordingly
    SRC_ROOT_FOLDER = os.path.join(DATA_ARCHIVE_ROOT, SRC_NAME)
    
    SCHEDULE = None #"15 14 * * 1"  # mondays at 14:15UTC/7:15PT
