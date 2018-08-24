import os
import csv
import boto3
import requests
from lxml import etree

s3 = boto3.resource('s3')

wbxXMLsvc = 'https://nta1wss.webex.com/WBXService/XMLService'
vaNBRstor = 'https://nta1wss.webex.com/nbr/services/NBRStorageService'
vaNBRsvc = 'https://nta1wss.webex.com/nbr/services/nbrXMLService'
sjNBRstor = 'https://nta1wss.webex.com/nbr/services/NBRStorageService'
sjNBRsvc = 'https://nta1wss.webex.com/nbr/services/nbrXMLService'

siteID = ''
userID = ''
userPW = ''

output_path = "output"

etLstRecording = etree.parse('wbx.LstRecording.xml').getroot()
etNBRRecordIdList = etree.parse('wbx.getNBRRecordIdList.xml').getroot()
etStorageAccessTicket = etree.parse('wbx.getStorageAccessTicket.xml').getroot()
etDlNbrStorageFile = etree.parse('wbx.downloadNBRStorageFile.xml').getroot()

stXMLheaders = {'Content-Type': 'text/xml'}
stSOAPheaders = {'Content-Type': 'text/xml', 'SOAPAction': ""}

parser = etree.XMLParser(ns_clean=True, recover=True, encoding='utf-8')

if __name__ == "__main__":

    if not os.path.exists(output_path):
        os.makedirs(output_path)

    #Get recording info and put into text files in directories
    # etLstRecording[0][0][2].text = siteID
    # etLstRecording[0][0][0].text = userID
    # etLstRecording[0][0][1].text = userPW
    # rLstRecording = requests.post(wbxXMLsvc, data=etree.tostring(etLstRecording), headers=stXMLheaders)
    # docLstRecording = etree.fromstring(rLstRecording.text.encode('utf-8'), parser=parser)
    # with open('output/LstRecording.xml', 'w+') as outLstRecording:
    #     outLstRecording.write(etree.tostring(docLstRecording, pretty_print=True))

    #Get Storage Access Ticket
    etStorageAccessTicket[1][0][0].text = siteID
    etStorageAccessTicket[1][0][1].text = userID
    etStorageAccessTicket[1][0][2].text = userPW
    rStorageAccessTicket = requests.post(vaNBRstor, data=etree.tostring(etStorageAccessTicket), headers=stSOAPheaders)
    rSATxml = etree.fromstring(rStorageAccessTicket.text.encode('utf-8'), parser=parser)
    sessionSAT = rSATxml[0][0][0].text

    f = open('recordingList.csv')
    csv_f = csv.reader(f)

    #Download NBR Storage Files
    for recordId in csv_f:

        recordID = recordId[0]

        base_output_file = 'output/tmp_' + recordID + '.arf'
        new_output_file = 'output/' + recordID + '.arf'

        etDlNbrStorageFile[1][0][2].text = sessionSAT
        with open('output/DlNbrStorageFile.xml', 'w+') as outDlNbrStorageFile:
            outDlNbrStorageFile.write(etree.tostring(etDlNbrStorageFile, pretty_print=True))
        etDlNbrStorageFile[1][0][0].text = siteID
        etDlNbrStorageFile[1][0][1].text = recordID
        etDlNbrStorageFile[1][0][2].text = sessionSAT
        rDlNbrStorageFile = requests.post(vaNBRstor, data=etree.tostring(etDlNbrStorageFile), headers=stSOAPheaders, stream=True)
        dlFile = open(base_output_file, 'wb')
        for chunk in rDlNbrStorageFile.iter_content(chunk_size=512):
            if chunk:
                dlFile.write(chunk)
        f = open(base_output_file, 'rb').read().split('\r\n\r\n')
        arf = open(new_output_file, 'wb')
        arf.write(f[3])
        data = open(new_output_file, 'rb')
        s3.Bucket('karmaguru').put_object(Key=recordID + '.arf', Body=data)
        os.remove(base_output_file)
        os.remove(new_output_file)

        print recordID + ": Complete"

        #Get Storage Access Ticket
        etStorageAccessTicket[1][0][0].text = siteID
        etStorageAccessTicket[1][0][1].text = userID
        etStorageAccessTicket[1][0][2].text = userPW
        rStorageAccessTicket = requests.post(vaNBRstor, data=etree.tostring(etStorageAccessTicket), headers=stSOAPheaders)
        rSATxml = etree.fromstring(rStorageAccessTicket.text.encode('utf-8'), parser=parser)
        sessionSAT = rSATxml[0][0][0].text