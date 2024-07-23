# Ref https://docs.python.org/3/library/html.parser.html
from html.parser import HTMLParser
import os
import re
import json
import logging
import base64
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

#? Get JSON mappings
mappingsFile = os.getenv("MAPPINGS_FILE", "scripts/gmail-lookup/mappings.json")
with open(mappingsFile, 'r') as stream:
  mappings = json.loads(stream.read())["mappings"]

def processData(_d: str, mappings: dict):
  def appendMsg(_m: str, _t: str, _M: str) -> str:
    return f"{_m}{_t.title()}: '{_M.strip()}', "
  for mp in mappings:
    msg = f"Type: {mp.title()}, "
    if result := re.findall(mappings[mp]['pattern'], _d):
      if type(result[0]) == tuple:
        for index, match in enumerate(result[0] if type(result[0]) == tuple else (result[0])):
          #print(f"Current mapping: {mp}, current index: {index}, matches: {result[0]}")
          msg = appendMsg(msg, mappings[mp]['data'][index], match)
      else:
        msg = appendMsg(msg, mappings[mp]['data'][0], result[0])
      print(msg)
      return

class MailParser(HTMLParser):
  """
  Parses Gmail message payloads and drops unnecessary HTML tags and attributes.
  """
  def handle_data(self, data: str):
    data = re.sub(r'\D{0,9}(?>\{.*\})|(?>\@\D.*)', '', data)
    #? Remove whitespaces and commas
    data = re.sub(r'\n|\r|\t|\0|,', '', data).strip()
    processData(data, mappings)

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
  
  gmailMaxResults = os.getenv("GMAIL_RESULTS_PER_PAGE", "1")
  gmailUserId = os.getenv("GMAIL_USER_ID", "me")
  gmailQuery = "from: transaction@belo.app"
  
  try:
    #? Build Gmail API
    service = build("gmail", "v1", credentials=creds)
    threads = service.users().threads().list(userId=gmailUserId, maxResults=gmailMaxResults, q=gmailQuery).execute().get("threads", [])
    for thread in threads:
      data = (service.users().threads().get(userId=gmailUserId, id=thread["id"])).execute()
      parser = MailParser()
      parser.feed(base64.urlsafe_b64decode(data["messages"][0]["payload"]["body"]["data"]).decode())
    
  except HttpError as error:
    print(f"HttpError: {error}")

if __name__ == "__main__":
  main()