import biothings.hub.dataload.uploader
import os

import requests
import biothings
import config
biothings.config_for_app(config)

MAP_URL = "https://raw.githubusercontent.com/SuLab/outbreak.info-resources/master/outbreak_resources_es_mapping.json"
MAP_VARS = ["@type", "abstract", "author", "isBasedOn", "curatedBy", "datePublished", "identifier", "journalName", "journalNameAbbrev", "license", "name", "publicationType", "url"]

# when code is exported, import becomes relative
try:
    from covid19_LST_parser.parser import load_annotations as parser_func
except ImportError:
    from .parser import load_annotations as parser_func


class LSTUploader(biothings.hub.dataload.uploader.BaseSourceUploader):

    main_source="covid19_LST_parser"
    name = "covid19_LST_parser"
    __metadata__ = {
        "src_meta": {
            "author":{
                "name": "Ginger Tsueng",
                "url": "https://github.com/gtsueng"
            },
            "code":{
                "branch": "master",
                "repo": "https://github.com/gtsueng/covid19_LST_parser.git"
            },
            "url": "https://www.covid19lst.org/",
            "license": "https://creativecommons.org/licenses/by-nc-sa/4.0/"
        }
    }
    idconverter = None
    storage_class = biothings.hub.dataload.storage.BasicStorage

    def load_data(self, data_folder):
        self.logger.info("No data to load from file for COVID19-LST")
        return parser_func()

    @classmethod
    def get_mapping(klass):
        r = requests.get(MAP_URL)
        if(r.status_code == 200):
            mapping = r.json()
            mapping_dict = { key: mapping[key] for key in MAP_VARS }
            return mapping_dict