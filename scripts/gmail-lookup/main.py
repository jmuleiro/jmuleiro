# Ref https://docs.python.org/3/library/html.parser.html
from html.parser import HTMLParser
import os
import re
import logging
import base64
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

class MailParser(HTMLParser):
  """
  Parses Gmail message payloads and drops unnecessary HTML tags and attributes.
  """
  def handle_data(self, data):
    data = data.strip()
    data = re.sub(r'\D{0,9}(?>\{.*\})|(?>\@\D.*)', '', data)
    data = re.sub(r'\n|\r|\t|\0', '', data)
    if data:
      print(f"Data     : {data}")

#* OAuth Scopes
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

def main():
  creds = None
  tokenFile = os.getenv("OAUTH_TOKEN_FILENAME", "token.json")
  credentialsFile = os.getenv("OAUTH_CREDENTIALS_FILENAME", "scripts/gmail-lookup/credentials2.json")

  if os.path.exists(tokenFile):
    creds = Credentials.from_authorized_user_file(tokenFile, SCOPES)
  
  #* If credentials are invalid, log in
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(credentialsFile, SCOPES)
      creds = flow.run_local_server()
    
    with open(tokenFile, "w") as token:
      token.write(creds.to_json())
  
  gmailResultsPerPage = os.getenv("GMAIL_RESULTS_PER_PAGE", "1")
  gmailUserId = os.getenv("GMAIL_USER_ID", "me")
  gmailQuery = "from: transaction@belo.app"

  try:
    service = build("gmail", "v1", credentials=creds)
    threads = service.users().threads().list(userId=gmailUserId, maxResults=gmailResultsPerPage, q=gmailQuery).execute().get("threads", [])
    for thread in threads:
      data = (service.users().threads().get(userId=gmailUserId, id=thread["id"])).execute()
      parser = MailParser()
      parser.feed(base64.urlsafe_b64decode(data["messages"][0]["payload"]["body"]["data"]).decode())
      #print(f"Thread messages: {base64.urlsafe_b64decode(data["messages"][0]["payload"]["body"]["data"]).decode()}")
    
  except HttpError as error:
    print(f"HttpError: {error}")

if __name__ == "__main__":
  main()