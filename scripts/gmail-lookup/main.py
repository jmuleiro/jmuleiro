# Ref https://docs.python.org/3/library/html.parser.html
import os
import re
import json
import time
import emoji
import base64
from logger import getLogger
from jsonschema import validate
from classes import EmailTemplate
from html.parser import HTMLParser
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

def init():
  #? Globals
  global log
  global mappings
  mappings: list[EmailTemplate] = []

  #? Setup logging
  log = getLogger(os.getenv('LOG_LEVEL', 'DEBUG'))
  
  #? Get JSON mappings
  log.debug("Getting mappings...")
  mappingsFile = os.getenv("MAPPINGS_FILE", "scripts/gmail-lookup/mappings.json")
  with open(mappingsFile, 'r') as stream:
    mappingsDict: dict = json.loads(stream.read())
  log.debug(f"Got mappings from {mappingsFile}")

  #? Mappings validation
  log.debug("Getting schema...")
  schemaFile = os.getenv("SCHEMA_FILE", "scripts/gmail-lookup/schema.json")
  with open(schemaFile, 'r') as stream:
    schema = json.loads(stream.read())
  log.debug(f"Got schema from {schemaFile}. Validating mappings...")
  validate(instance=mappingsDict, schema=schema)
  log.info("Mappings are valid")
  
  log.debug("Parsing mappings...")
  for template in mappingsDict.get("templates"):
    mappings.append(EmailTemplate(template))
  log.debug("Mappings parse successful")
  exit(0)

#todo: place into classes file, can't separate easily because of logging and mappings
class MailParser(HTMLParser):
  """
  Parses Gmail message payloads and drops unnecessary HTML tags and attributes.
  """
  def handle_data(self, data: str):
    #? Drop all lines that do not contain a dollar sign
    if not re.findall(r'\$', data):
      return
    #? Remove emoji
    data = emoji.replace_emoji(data, '')
    data = re.sub(r'\D{0,9}(?>\{.*\})|(?>\@\D.*)', '', data)
    #? Remove whitespaces and commas
    data = re.sub(r'\n|\r|\t|\0|,', '', data).strip()
    #todo: templates is an array of EmailTemplate
    templates = EmailTemplate(mappings.get("templates"))
    self.processData(data, templates)
  
  def processData(_d: str, mappings: dict):
    def appendMsg(_m: str, _t: str, _M: str) -> str:
      return f"{_m}{_t.title()}: '{_M.strip()}', "
    for mp in mappings:
      msg = f"Type: {mp.title()}, "
      if result := re.findall(mappings[mp]['pattern'], _d):
        if type(result[0]) == tuple:
          for index, match in enumerate(result[0] if type(result[0]) == tuple else (result[0])):
            msg = appendMsg(msg, mappings[mp]['data'][index], match)
        else:
          msg = appendMsg(msg, mappings[mp]['data'][0], result[0])
        log.debug(msg)
        return
    log.warning(f"No mapping for '{_d}'")

def main():
  log.debug("Getting credentials...")
  creds = None
  SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
  tokenFile = os.getenv("OAUTH_TOKEN_FILENAME", "token.json")
  credentialsFile = os.getenv("OAUTH_CREDENTIALS_FILENAME", "scripts/gmail-lookup/credentials2.json")

  if os.path.exists(tokenFile):
    creds = Credentials.from_authorized_user_file(tokenFile, SCOPES)
    log.debug(f"Found token file: '{tokenFile}'")
  else:
    log.debug(f"No token file at: '{tokenFile}'")
  
  #? If credentials are invalid, log in
  if not creds or not creds.valid:
    log.debug("Credentials are invalid, attempting refresh...")
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
      log.debug("Refreshed credentials")
    else:
      log.debug(f"Refresh not possible, starting OAuth flow with credentials at '{credentialsFile}'")
      flow = InstalledAppFlow.from_client_secrets_file(credentialsFile, SCOPES)
      creds = flow.run_local_server()
      log.debug("OAuth flow completed successfully")
    
    with open(tokenFile, "w") as token:
      token.write(creds.to_json())
      log.debug(f"Wrote token file to '{tokenFile}'")

  for i, mp in enumerate(mappings):
    log.debug(f"Template n°{i+1}")
    gmailQuery = f"from: {mp.sender}"
    #todo: run mails from mp.sender through mp.mappings

  gmailMaxResults = os.getenv("GMAIL_RESULTS_PER_PAGE", "100")
  gmailUserId = os.getenv("GMAIL_USER_ID", "me")
  # Date format: YYYY/MM/DD or MM/DD/YYYY
  gmailDateFrom = os.getenv("GMAIL_DATE_FROM", "2024/05/31")
  gmailDateTo = os.getenv("GMAIL_DATE_TO", "2024/07/01")
  gmailQuery = "from: transaction@belo.app"
  if gmailDateFrom:
    gmailQuery += f" after:{gmailDateFrom}"
  if gmailDateTo:
    gmailQuery += f" before:{gmailDateTo}"
  log.debug(f"""Parameters:
maxResults: {gmailMaxResults}
userId: {gmailUserId}
dateFrom: {gmailDateFrom}
dateTo: {gmailDateTo}
query: {gmailQuery}
""")
  
  try:
    #? Build Gmail API
    log.info("Building Gmail API...")
    service = build("gmail", "v1", credentials=creds)
    nextPageToken = None
    log.debug("Iterating over results...")
    resultsCount = 0
    while True:
      log.debug(f"Results iteration no.: '{resultsCount :+= 1}'")
      response = service.users().threads().list(userId=gmailUserId, maxResults=gmailMaxResults, q=gmailQuery, pageToken=nextPageToken).execute()
      threads = response.get("threads", [])
      for thread in threads:
        data = (service.users().threads().get(userId=gmailUserId, id=thread["id"])).execute()
        parser = MailParser()
        parser.feed(base64.urlsafe_b64decode(data["messages"][0]["payload"]["body"]["data"]).decode())
      
      nextPageToken = response.get("nextPageToken", None)
      log.debug(f"NextPageToken: {nextPageToken}")
      if nextPageToken:
        sleptSeconds = 1
        log.info(f"Sleeping for {sleptSeconds} second(s)...")
        time.sleep(sleptSeconds)
      else:
        log.info("Got to the end of the list")
        break
    
  except HttpError as error:
    log.critical(f"HttpError: {error}")

if __name__ == "__main__":
  init()
  main()