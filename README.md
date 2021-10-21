## COVID-19 Literature Surveillance Team parser for Outbreak.info

This is the parser for the COVID-19 Literature Surveillance Team reports.  The COVID-19 Literature Surveillance Team is a group of MDs, PhDs, Medical Students and Residents who summarize and evaluate recent publications on COVID-19. They use the Bottom Line Up Front (BLUF) standard for their summaries and the 2011 Oxford level of evidence rubric for evaluating level of evidence.

This parser generates the metadata records for each report in the COVID-19 LST google drive. It also creates value added information to be appended to existing publication metadata records.

Note that reports in the drive prior to September 12, 2020 were checked for naming issues and manually corrected and stored in the data folder of this repository.  As a result, the parser will only pull files posted to the google drive after September 11th.

Additionally, this parser uses the PyDrive2 library to leverage the googledrive API. Sufficient credentials (credentials.json) will be needed in order to make it work.

Note that the jupyter notebook contains more detailed comments and serves as the documentation for this code. If it causes issues with running the code withing the BioThings ecosystem, delete the 'documentation' folder before running.

Note that the COVID-19 LST provides 2 types of data: Their reports (which are deserving of their own entries as review articles) and their annotations (to be appended to publication entries).  This repo is for the reports, which are updated almost daily (weekends are less steady). 

Note that COVID-19 LST has ended their project and stopped generating literature reports as of July, 2021. From October on, this plugin will just access already parsed data from github. For the plugin which actually parses COVID-19 LST reports (pdf) use the "active_update" branch.