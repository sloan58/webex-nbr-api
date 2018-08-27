import os
import csv
import boto3
import sqlite3
import requests
from lxml import etree

# AWS S3 connector
s3 = boto3.resource('s3')

# SQLite connector
db = sqlite3.connect('recordings.sqlite')
cursor = db.cursor()

# Webex NBR API URL
vaNBRstor = 'https://nta1wss.webex.com/nbr/services/NBRStorageService'

# Webex API Auth
siteID = ''
userID = ''
userPW = ''

# Output path for recordings
output_path = "output"

# API XML templates
etNBRRecordIdList = etree.parse('wbx.getNBRRecordIdList.xml').getroot()
etStorageAccessTicket = etree.parse('wbx.getStorageAccessTicket.xml').getroot()
etDlNbrStorageFile = etree.parse('wbx.downloadNBRStorageFile.xml').getroot()

# Soap headers
stXMLheaders = {'Content-Type': 'text/xml'}
stSOAPheaders = {'Content-Type': 'text/xml', 'SOAPAction': ""}

# SOAP parser
parser = etree.XMLParser(ns_clean=True, recover=True, encoding='utf-8')

if __name__ == "__main__":

    # Create the output dir if it doesn't exist
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    #Download NBR Storage Files
    while True:

        # Get first available recording (not PROCESSING or COMPLETED)
        cursor.execute('''SELECT name, status FROM recordings WHERE status IS NULL''')
        record = cursor.fetchone()
        try:
            recordID = record[0]
            status = record[1]
        except TypeError:
            print "No records found for download"
            break

        # Update recording status
        cursor.execute('''UPDATE recordings SET status = ? WHERE name = ? ''',
        ('PROCESSING', recordID))
        db.commit()

        # Create base output file
        base_output_file = 'output/tmp_' + recordID + '.arf'

        #Get Storage Access Ticket
        etStorageAccessTicket[1][0][0].text = siteID
        etStorageAccessTicket[1][0][1].text = userID
        etStorageAccessTicket[1][0][2].text = userPW
        rStorageAccessTicket = requests.post(vaNBRstor, data=etree.tostring(etStorageAccessTicket), headers=stSOAPheaders)
        rSATxml = etree.fromstring(rStorageAccessTicket.text.encode('utf-8'), parser=parser)
        sessionSAT = rSATxml[0][0][0].text

        # Build XML for request
        etDlNbrStorageFile[1][0][0].text = siteID
        etDlNbrStorageFile[1][0][1].text = recordID
        etDlNbrStorageFile[1][0][2].text = sessionSAT

        # Send API POST request
        rDlNbrStorageFile = requests.post(vaNBRstor, data=etree.tostring(etDlNbrStorageFile), headers=stSOAPheaders, stream=True)
        dlFile = open(base_output_file, 'wb')

        # Save file to disk
        for chunk in rDlNbrStorageFile.iter_content(chunk_size=512):
            if chunk:
                dlFile.write(chunk)
        
        # Split utf-8 and binary data from response
        f = open(base_output_file, 'rb').read().split('\r\n\r\n')

        # Create final output filename
        try:
            new_output_file = 'output/' + f[2].splitlines()[0].replace(" ", "_")
        except IndexError:
            new_output_file = 'output/' + recordID + '.arf'
        
        # Open output file
        arf = open(new_output_file, 'wb')

        # Save binary recording
        try:
            arf.write(f[3])
        except IndexError:
            print recordID + ": Recording does not exist"
            os.remove(base_output_file)
            os.remove(new_output_file)
            cursor.execute('''UPDATE recordings SET status = ? WHERE name = ? ''',
            ('COMPLETED', recordID))
            db.commit()
            continue

        # Save to S3 and remove local copy
        # data = open(new_output_file, 'rb')
        # s3.Bucket('mys3bucket').put_object(Key=recordID + '.arf', Body=data)
        # os.remove(new_output_file)

        # Remove tmp output file that had utf-8 and binary
        os.remove(base_output_file)

        # Update status to COMPLETED
        cursor.execute('''UPDATE recordings SET status = ?, meetingname = ? WHERE name = ? ''',
        ('COMPLETED', new_output_file, recordID))
        db.commit()

        print recordID + ": Complete"