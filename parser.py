import os
import pandas
from pandas import read_csv
import json
import pickle
from datetime import datetime
import sys
import PyPDF2 as pypdf
import requests

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
    memberlist = read_csv('data/LST members.txt',delimiter='\t',header=0,encoding='UTF-8')
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
        cleanresult = rawresult.drop_duplicates(subset='_id',keep="first")
        if len(doilist)>len(cleanresult):
            missing = [x for x in doilist if x not in cleanresult['doi'].unique().tolist()]
        else:
            missing = None
        cleanresult.drop(columns=['doi','_score','query'],inplace=True)
    return(cleanresult, missing)


### Batch fetch pmid meta
def get_pmid_meta(pmidlist):
    pmidstring = '"' + '","'.join(pmidlist) + '"'
    r = requests.post("https://api.outbreak.info/resources/query/", params = {'q': pmidstring, 'scopes': '_id', 'fields': '_id,name,url'})
    if r.status_code == 200:
        rawresult = pandas.read_json(r.text)
        cleanresult = rawresult[['_id','name','url']].loc[rawresult['_score']==1].copy()
        cleanresult.drop_duplicates(subset='_id',keep="first", inplace=True)
        if len(pmidlist)>len(cleanresult):
            missing = [x for x in pmidlist if x not in cleanresult['_id'].unique().tolist()]
        else:
            missing = None
    return(cleanresult, missing)    


def parse_pdf(eachfile):
    pdffile = open('data/reports/'+eachfile,'rb')
    pdf = pypdf.PdfFileReader(pdffile)
    pages = pdf.getNumPages()
    key = '/Annots'
    uri = '/URI'
    ank = '/A'
    allurls = []
    for page in range(pages):
        pageSliced = pdf.getPage(page)
        pageObject = pageSliced.getObject()
        if key in pageObject:
            ann = pageObject[key]
            for a in ann:
                u = a.getObject()
                if ank in u:
                    if uri in u[ank]:
                        allurls.append(u[ank][uri])
    pmidlist = []
    doilist = []
    for eachurl in allurls:
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
    try:
        missing_list = pickle.load(open('results/pubs_not_yet_in_outbreak.txt','rb'))
        if missing != None:
            total_missing = list(set([*missing_list, *missing]))
            with open('results/pubs_not_yet_in_outbreak.txt','wb') as dmpfile:
                pickle.dump(total_missing,dmpfile)
    except:
        if missing != None:
            with open('results/pubs_not_yet_in_outbreak.txt','wb') as dmpfile:
                pickle.dump(missing,dmpfile)

        
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
    for eachfile in filelist:
        reportdate = eachfile[0:4]+'.'+eachfile[4:6]+'.'+eachfile[6:8]
        datePublished = datetime.fromisoformat(eachfile[0:4]+'-'+eachfile[4:6]+'-'+eachfile[6:8])
        name = "Covid-19 LST Report "+reportdate
        reporturl = generate_report_url(datePublished)
        report_id = 'lst'+reportdate
        pmidlist,doilist = parse_pdf(eachfile)
        basedOndf,missing = merge_meta(pmidlist,doilist)
        reportlinkdf = basedOndf[['_id','url']]
        reportlinkdf['identifier']=report_id
        reportlinkdf['url']=reporturl
        reportlinkdf['name']=name
        report_pmid_df = pandas.concat(([report_pmid_df,reportlinkdf]),ignore_index=True)
        report_pmid_df.drop_duplicates(keep='first',inplace=True)
        report_pmid_df.to_csv('data/report_pmid_df.txt',sep='\t',header=True)
        save_missing(missing)
        abstract = generate_abstract(basedOndf['_id'].unique().tolist())
        metadict = {"@context": {"schema": "http://schema.org/", "outbreak": "https://discovery.biothings.io/view/outbreak/"}, 
                    "@type": "Publication", "journalName": "COVID-19 LST Daily Summary Reports", "journalNameAbbreviation": "covid19LST", 
                    "publicationType": "Review", "license":"(CC BY-NC-SA 4.0) (http://creativecommons.org/licenses/by-nc-sa/4.0/)",
                    "_id":report_id,"curatedBy": curatedByObject,"abstract": abstract, "name": name, 
                    "datePublished": datePublished.strftime("%y-%m-%d"),"url": reporturl,"author":[author], 
                    "isBasedOn":basedOndf.to_dict('records')}
        yield(metadict)
        
        
## This function identifies files uploaded after 2020.09.11 that have NOT yet been downloaded
## Note that this is the function if a service account IS available. 
def check_google():
    from pydrive2.auth import GoogleAuth
    from pydrive2.drive import GoogleDrive
    from pydrive2.auth import ServiceAccountCredentials
    
    gauth = GoogleAuth()
    scope = ['https://www.googleapis.com/auth/drive']
    gauth.credentials = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    drive = GoogleDrive(gauth)
    file_id = '1603ahBNdt1SnSaYYBE-G8SA6qgRTQ6fF'
    file_list = drive.ListFile({'q': "'%s' in parents and trashed=false" % file_id}).GetList()
    
    df = pandas.DataFrame(file_list)
    dfclean = df[['createdDate','id','title']].copy()
    dfclean['date'] = pandas.to_datetime(dfclean['createdDate'],format='%Y-%m-%d', errors='coerce')
    lastupdate = dfclean.loc[dfclean['createdDate']=='2020-09-11T01:53:29.639Z'].iloc[0]['date']
    dfnew = dfclean.loc[dfclean['date']>lastupdate]
    
    all_files = os.listdir('data/reports/')
    new_files = [item  for item in all_files if item not in dfnew['title'].unique().tolist()]
    reportdf = dfnew.loc[dfnew['title'].isin(new_files)]
    return(reportdf)


## This is the function to actually conduct the download
def download_reports(reportdf):
    from google_drive_downloader import GoogleDriveDownloader as gdd
    for i in range(len(reportdf)):
        title = reportdf.iloc[i]['title']
        eachid = reportdf.iloc[i]['id']
        gdd.download_file_from_google_drive(file_id=eachid,
                                            dest_path='data/reports/'+title,
                                            unzip=False)    
        

def load_annotations():
    reportdf = check_google()
    download_reports(reportdf)
    dumpdir = 'data/reports/'
    filelist = os.listdir(dumpdir)
    metadict = generate_report_meta(filelist)
    yield from(metadict)
    




