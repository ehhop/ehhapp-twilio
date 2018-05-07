import httplib2
import os
import oauth2client
from oauth2client import client, tools, file
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from googleapiclient import errors, discovery

SCOPES = 'https://www.googleapis.com/auth/gmail.send'
CLIENT_SECRET_FILE = '../gmail_sending_secrets.json'
APPLICATION_NAME = 'EHHOP Webserver'

def get_credentials():
    home_dir = '/var/wsgiapps/ehhapp_twilio/'
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir, 'gmail-python-email-send.json')
    store = file.Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        raise Exception("Credentials invalid")
#        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
#        flow.user_agent = APPLICATION_NAME
#        credentials = tools.run_flow(flow, store)
#        print('Storing credentials to ' + credential_path)
    return credentials

def SendMessage(sender="", to="", cc="", subject="", msgHtml="", msgPlain=""):
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('gmail', 'v1', http=http)
    message1 = CreateMessage(sender=sender, to=to, cc=cc, subject=subject, msgHtml=msgHtml, msgPlain=msgPlain)
    SendMessageInternal(service, "me", message1)

def SendMessageInternal(service, user_id, message):
    try:
        message = (service.users().messages().send(userId=user_id, body=message).execute())
        print('Message Id: %s' % message['id'])
        return message
    except errors.HttpError as error:
        print('An error occurred: %s' % error)

def CreateMessage(sender="", to="", cc=None, subject="", msgHtml="", msgPlain=""):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = to
    if (cc != None)&(cc != "")&("@" in cc):
        msg['Cc'] = cc
    msg.attach(MIMEText(msgPlain, 'plain','utf-8'))
    msg.attach(MIMEText(msgHtml, 'html','utf-8'))
    raw = base64.urlsafe_b64encode(msg.as_string())
    raw = raw.decode()
    body = {'raw': raw}
    return body

def main():
    to = "ryan.neff@icahn.mssm.edu"
    sender = "ehhop.voicemails@icahn.mssm.edu"
    subject = "subject"
    msgHtml = "Hi<br/>Html Email"
    msgPlain = "Hi\nPlain Email"
    cc = ""
    SendMessage(sender=sender, to=to, cc=cc, subject=subject, msgHtml=msgHtml, msgPlain=msgPlain)

if __name__ == '__main__':
    main()
