import os
import pandas
from pandas import read_csv
import json
import pickle
from datetime import datetime
import sys
from io import StringIO
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
import requests

from biothings import config
logger = config.logger

DATA_PREFIX  = '/data/outbreak/plugins/covid_LST_reports'
RESULTS_PATH = os.path.join(DATA_PREFIX, 'results/')
DATA_PATH    = os.path.join(DATA_PREFIX, 'data/')
REPORTS_PATH = os.path.join(DATA_PREFIX, 'reports/')

#### Create curatedBy Object
def generate_curator():
    todate = datetime.now()
    curatedByObject = {"@type": "Organization", "identifier": "covid19LST", "url": "https://www.covid19lst.org/", 
                              "name": "COVID-19 Literature Surveillance Team", "affiliation": [], 
                              "curationDate": todate.strftime("%Y-%m-%d")}
    return(curatedByObject)


def generate_author():
    authorObject = generate_curator()
    authorObject.pop('curationDate')
    memberlist = read_csv(os.path.join(DATA_PREFIX, 'LST members.txt'),delimiter='\t',header=0,encoding='UTF-8')
    memberlist.rename(columns={'affiliation':'affiliation list'}, inplace=True)
    memberlist['affiliation']='blank'
    for i in range(len(memberlist)):
        affiliationlist = memberlist.iloc[i]['affiliation list'].split(';')
        tmplist = []
        for eachaffiliation in affiliationlist:
            tmplist.append({"name":eachaffiliation})
        memberlist.at[i,'affiliation'] = tmplist
    memberlist.drop(columns='affiliation list',inplace=True)
    memberdictlist = memberlist.to_dict('records')
    authorObject['members']=memberdictlist 
    return(authorObject)


def generate_abstract(publist):
    separator = ', '
    abstract = "Analytical reviews on the level of evidence presented in publications. This report specifically covers the following publications: "+ separator.join(publist)
    return(abstract)


### Batch convert DOIs
def convert_dois(doilist):
    doistring = '"' + '","'.join(doilist) + '"'
    r = requests.post("https://api.outbreak.info/resources/query/", params = {'q': doistring, 'scopes': 'doi', 'fields': '_id,name,url,doi'})
    if r.status_code == 200:
        rawresult = pandas.read_json(r.text)
        if 'notfound' in rawresult.columns:
            check = rawresult.loc[(rawresult['notfound']==1.0)|(rawresult['notfound']==True)]
            if len(check)==len(doilist):
                cleanresult = pandas.DataFrame(columns=['_id','name','url','doi'])
                missing = doilist            
            else:
                no_dups = rawresult[rawresult['query']==rawresult['doi']]
                cleanresult = no_dups[['_id','name','url','doi']].loc[~no_dups['_id'].isin(check['_id'].tolist())].copy()
                missing = [x for x in doilist if x not in cleanresult['doi'].unique().tolist()]        
        else:
            no_dups = rawresult[rawresult['query']==rawresult['doi']]
            cleanresult = no_dups[['_id','name','url','doi']]
            missing = []
        cleanresult.drop('doi',axis=1,inplace=True)
        
    else:
        cleanresult=[]
        missing=[]
    return(cleanresult, missing)


### Batch fetch pmid meta
def get_pmid_meta(pmidlist):
    pmidstring = '"' + '","'.join(pmidlist) + '"'
    r = requests.post("https://api.outbreak.info/resources/query/", params = {'q': pmidstring, 'scopes': '_id', 'fields': '_id,name,url'})
    if r.status_code == 200:
        rawresult = pandas.read_json(r.text)
        no_dups = rawresult[rawresult['query']==rawresult['_id']]
        if 'notfound' in rawresult.columns:
            check = rawresult.loc[(rawresult['notfound']==1.0)|(rawresult['notfound']==True)]
            if len(check)==len(pmidlist):
                cleanresult = pandas.DataFrame(columns=['_id','name','url'])
                missing = pmidlist            
            else:
                cleanresult = no_dups[['_id','name','url']].loc[~no_dups['_id'].isin(check['_id'].tolist())].copy()
                missing = [x for x in pmidlist if x not in cleanresult['_id'].unique().tolist()]
        else:
            cleanresult = no_dups[['_id','name','url']]
            missing = []
        
    else:
        cleanresult=[]
        missing=[]
    return(cleanresult, missing)     


#### Include method for poorly encoded pdfs
def strip_ids_from_text(output_text):
    pmidlist = []
    doilist = []
    check = output_text.split('\n')
    doilines = [x for x in check if 'doi' in x.lower()]
    if len(doilines)>0:
        for doiline in doilines:
            if '\t' in doiline:
                doistart = doiline[doiline.find('doi'):]
                doi = doistart[doistart.find('\t'):doistart.find('.\t')]
                doilist.append(doi.strip())
            else:
                doistart = doiline[doiline.find('doi'):]
                doi = doistart[doistart.find(' '):doistart.find('. ')]
                doilist.append(doi.strip())
    return(pmidlist,doilist)


#### Method for parsing out ids from a url
def parse_urls(eachurl,pmidlist,doilist):
    if 'pubmed' in eachurl and '?' not in eachurl:
        pmid = eachurl.replace("https://www.ncbi.nlm.nih.gov/pubmed/","").replace("https://pubmed.ncbi.nlm.nih.gov/","").rstrip("/")
        if "#affiliation" in pmid:
            trupmid = pmid.split("/")[0]
            tmpid = 'pmid'+trupmid
        else:
            tmpid = 'pmid'+pmid
        pmidlist.append(tmpid)
    elif 'doi' in eachurl:
        tenplace = eachurl.find('10.')
        doi = eachurl[tenplace:]
        doilist.append(doi)  
    return(pmidlist,doilist)


def parse_pdf(eachfile):
    pdffile = open('data/reports/'+eachfile,'rb')
    parser = PDFParser(pdffile)
    doc = PDFDocument(parser)
    allurls = []
    pmidlist = []
    doilist = []
    for page in PDFPage.create_pages(doc):
        try: 
            for annotation in page.annots:
                annotationDict = annotation.resolve()
                if "A" in annotationDict:
                    uri = annotationDict["A"]["URI"].decode('UTF-8').replace(" ", "%20")
                    allurls.append(uri)
        except:
            continue  
    if len(allurls)>0:  
        for eachurl in allurls:
            pmidlist,doilist = parse_urls(eachurl,pmidlist,doilist)              
    if len(allurls)==0: 
        output_string = StringIO()
        rsrcmgr = PDFResourceManager()
        device = TextConverter(rsrcmgr, output_string, laparams=LAParams())
        interpreter = PDFPageInterpreter(rsrcmgr, device)
        for page in PDFPage.create_pages(doc):
            interpreter.process_page(page)
        output_text = output_string.getvalue()
        pmidlist, doilist = strip_ids_from_text(output_text)         
    pmidlist = list(set(pmidlist))
    doilist = list(set(doilist))
                   
    return(pmidlist,doilist)


def merge_meta(pmidlist,doilist):
    if len(doilist)>0:
        doianns,missing_dois = convert_dois(doilist)
        doicheck = True
    else:
        doicheck = False
        missing_dois = None
    if len(pmidlist)>0:
        pmidanns,missing_pmids = get_pmid_meta(pmidlist)
        pmidcheck = True
    else:
        pmidcheck = False
        missing_pmids = None
    if doicheck==True and pmidcheck==True:
        basedOndf = pandas.concat((pmidanns,doianns),ignore_index=True)
    elif doicheck==True and pmidcheck==False:
        basedOndf = doianns
    elif doicheck==False and pmidcheck==True:
        basedOndf = pmidanns     
    if missing_pmids!=None and missing_dois!=None:
        missing = list(set(missing_pmids).union(set(missing_dois)))
    elif missing_pmids==None and missing_dois!=None:
        missing = missing_dois
    elif missing_pmids!=None and missing_dois==None:
        missing = missing_pmids
    else:
        missing = None
    return(basedOndf,missing)


def save_missing(missing):
    not_yet_file = 'pubs_not_yet_in_outbreak.p'
    if os.path.isfile(not_yet_file):
        missing_list = pickle.load(open(os.path.join(RESULTS_PATH, not_yet_file),'rb'))
        if missing != None:
            total_missing = list(set([*missing_list, *missing]))
            with open(os.path.join(RESULTS_PATH, not_yet_file),'wb') as dmpfile:
                pickle.dump(total_missing,dmpfile)
    else:
        if missing != None:
            total_missing = list(set(missing))
            with open(os.path.join(RESULTS_PATH, not_yet_file),'wb') as dmpfile:
                pickle.dump(total_missing,dmpfile)

        
## Note that strftime("%d") will give the day with a leading zero
## In windows, strftime("%#d") will give it without leading zeros
## In linux, strftime("%-d") will give it without leading zeros
def generate_report_url(datePublished):
    urlbase = "https://www.covid19lst.org/post/"
    urlend = "daily-covid-19-lst-report"
    is_windows = sys.platform.startswith('win')
    if is_windows==True:
        reporturl = urlbase+datePublished.strftime("%B").lower()+"-"+datePublished.strftime("%#d")+"-"+urlend
    else:
        reporturl = urlbase+datePublished.strftime("%B").lower()+"-"+datePublished.strftime("%-d")+"-"+urlend
    return(reporturl)



def generate_report_meta(filelist):
    report_pmid_df = pandas.DataFrame(columns=['_id','name','identifier','url'])
    curatedByObject = generate_curator()
    author = generate_author()
    badpdfs = []
    for eachfile in filelist:
        reportdate = eachfile[0:4]+'.'+eachfile[4:6]+'.'+eachfile[6:8]
        try:
            datePublished = datetime(int(eachfile[0:4]), int(eachfile[4:6]), int(eachfile[6:8]))
        except:
            logger.warning(f"could not find date published for {eachfile}")
            continue

        name = "Covid-19 LST Report "+reportdate
        reporturl = generate_report_url(datePublished)
        report_id = 'lst'+reportdate
        logger.warning(eachfile)
        pmidlist,doilist = parse_pdf(eachfile)
        if len(pmidlist)+len(doilist)==0:
            badpdfs.append(eachfile)
        else:
            basedOndf,missing = merge_meta(pmidlist,doilist)
            basedOndf['@type']='Publication'
            reportlinkdf = basedOndf[['_id','url']]
            reportlinkdf['identifier']=report_id
            reportlinkdf['url']=reporturl
            reportlinkdf['name']=name
            report_pmid_df = pandas.concat(([report_pmid_df,reportlinkdf]),ignore_index=True)
            report_pmid_df.drop_duplicates(keep='first',inplace=True)
            report_pmid_df.to_csv(os.path.join(DATA_PREFIX, 'report_pmid_df.txt'),sep='\t',header=True)
            save_missing(missing)
            abstract = generate_abstract(basedOndf['_id'].unique().tolist())
            metadict = {"@context": {"schema": "http://schema.org/", "outbreak": "https://discovery.biothings.io/view/outbreak/"}, 
                        "@type": "Publication", "journalName": "COVID-19 LST Daily Summary Reports", "journalNameAbbreviation": "covid19LST", 
                        "publicationType": "Review", "license":"(CC BY-NC-SA 4.0) (http://creativecommons.org/licenses/by-nc-sa/4.0/)",
                        "_id":report_id,"curatedBy": curatedByObject,"abstract": abstract, "name": name, 
                        "datePublished": datePublished.strftime("%Y-%m-%d"),"url": reporturl,"author":[author], 
                        "isBasedOn":basedOndf.to_dict('records')}
            yield(metadict)
        except:
            save_missing(list(report_id))
        
        
## This function identifies files uploaded after 2020.09.11 that have NOT yet been downloaded
## Note that this is the function if a service account IS available. 
def check_google():
    from pydrive2.auth import GoogleAuth
    from pydrive2.drive import GoogleDrive
    from pydrive2.auth import ServiceAccountCredentials
    
    gauth = GoogleAuth()
    scope = ['https://www.googleapis.com/auth/drive']
    cred_path = os.path.join(DATA_PREFIX, 'credentials.json')
    gauth.credentials = ServiceAccountCredentials.from_json_keyfile_name(cred_path, scope)
    drive = GoogleDrive(gauth)
    file_id = '1603ahBNdt1SnSaYYBE-G8SA6qgRTQ6fF'
    file_list = drive.ListFile({'q': "'%s' in parents and trashed=false" % file_id}).GetList()
    
    df = pandas.DataFrame(file_list)
    dfclean = df[['createdDate','id','title']].copy()
    dfclean['date'] = pandas.to_datetime(dfclean['createdDate'],format='%Y-%m-%d', errors='coerce')
    lastupdate = dfclean.loc[dfclean['createdDate']=='2020-09-11T01:53:29.639Z'].iloc[0]['date']
    dfnew = dfclean.loc[dfclean['date']>lastupdate]
    
    all_files = os.listdir(REPORTS_PATH)
    new_files = [item for item in dfnew['title'].unique().tolist() if item not in all_files]
    reportdf = dfnew.loc[dfnew['title'].isin(new_files)]
    return(reportdf)


## This is the function to actually conduct the download
def download_reports(reportdf):
    from google_drive_downloader import GoogleDriveDownloader as gdd
    notdownloaded = 0
    for i in range(len(reportdf)):
        title = reportdf.iloc[i]['title']
        eachid = reportdf.iloc[i]['id']
        try:
            date_title = int(title[0:6])
            gdd.download_file_from_google_drive(file_id=eachid,
                                                dest_path='data/reports/'+title,
                                                unzip=False)
        except:
            notdownloaded = notdownloaded+1   
        

def load_annotations():
    reportdf = check_google()
    download_reports(reportdf)
    dumpdir = REPORTS_PATH
    filelist = os.listdir(dumpdir)
    logger.warning(filelist)
    metadict = generate_report_meta(filelist)
    yield from(metadict)
