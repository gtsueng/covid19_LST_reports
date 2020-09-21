## COVID-19 Literature Surveillance Team parser for Outbreak.info

This is the parser for the COVID-19 Literature Surveillance Team reports.  The COVID-19 Literature Surveillance Team is a group of MDs, PhDs, Medical Students and Residents who summarize and evaluate recent publications on COVID-19. They use the Bottom Line Up Front (BLUF) standard for their summaries and the 2011 Oxford level of evidence rubric for evaluating level of evidence.

This parser generates the metadata records for each report in the COVID-19 LST google drive. It also creates value added information to be appended to existing publication metadata records.

Note that reports in the drive prior to September 12, 2020 were checked for naming issues and manually corrected and stored in the data folder of this repository.  As a result, the parser will only pull files posted to the google drive after September 11th.

Additionally, this parser uses the PyDrive2 library to leverage the googledrive API. Sufficient credentials (credentials.json) will be needed in order to make it work.
