# Ref https://docs.python.org/3/library/html.parser.html
import re
import os
import json
import time
import base64
from logger import getLogger
from jsonschema import validate
from traceback import print_exc
from classes import EmailTemplate, MailParser
from prometheus_client import start_http_server
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

#? Globals
global log
global mappings
mappings: list[EmailTemplate] = []
#todo: implement exporter-like server approach

#? Setup logging
log = getLogger(os.getenv('LOG_LEVEL', 'DEBUG'))

def init():
  #? Get JSON mappings
  log.debug("Getting mappings")
  mappingsFile = os.getenv("MAPPINGS_FILE", "scripts/gmail-lookup/mappings.json")
  with open(mappingsFile, 'r') as stream:
    mappingsDict: dict = json.loads(stream.read())
  log.debug(f"Got mappings from {mappingsFile}")

  #? Mappings validation
  log.debug("Getting schema")
  schemaFile = os.getenv("SCHEMA_FILE", "scripts/gmail-lookup/schema.json")
  with open(schemaFile, 'r') as stream:
    schema = json.loads(stream.read())
  log.debug(f"Got schema from {schemaFile}. Validating mappings")
  validate(instance=mappingsDict, schema=schema)
  log.info("Mappings are valid")
  
  log.debug("Parsing mappings")
  for template in mappingsDict.get("templates"):
    mappings.append(EmailTemplate(template))
  log.debug("Mappings parse successful")

def backwardsLookup(query: str, userId: str, maxResults: str, mappings: list[EmailTemplate]):
  dateRegex = r"^\d{2}\/\d{2}\/\d{4}$"
  from datetime import datetime, timedelta
  if (gmailDateFrom := os.getenv("MAIL_DATE_FROM", False)):
    if not (re.match(dateRegex, gmailDateFrom)
            or datetime.strptime(gmailDateFrom, "%m/%d/%Y")): 
      raise ValueError("Date from should be MM/DD/YYYY")
  else:
    gmailDateFrom = (datetime.now() - timedelta(os.getenv("MAIL_FROM_DAYS", 30))).strftime("%m/%d/%Y")
  gmailQuery += f"after:{gmailDateFrom} "
  
  #? If MAIL_DATE_TO is not set lookup everything after gmailDateFrom
  if (gmailDateTo := os.getenv("MAIL_DATE_TO", False)):
    if not (re.match(dateRegex, gmailDateFrom)
            or datetime.strptime(gmailDateTo, "%m/%d/%Y")):
      raise ValueError("Date to should be MM/DD/YYYY")
    gmailQuery += f"before:{gmailDateTo} "
  

def getEmails(apiService: object, query: str, userId: str, maxResults: str):
  log.debug(f"Getting emails, query: '{query}'")
  nextPageToken = None
  resultsCount = 0
  #? Do/While, we want to get mails list first and then see if a nextPageToken exists
  while True:
    log.debug(f"Results iteration no.: '{resultsCount :+= 1}'")
    response = (apiService
                .users()
                .threads()
                .list(userId=userId, maxResults=maxResults, q=query, pageToken=nextPageToken)
                .execute())
    mailThreads = response.get("threads", [])
    nextPageToken = response.get("nextPageToken", None)
    
    if not mailThreads:
      log.debug("Got no threads")
      return
    
    for mThread in mailThreads:
      log.debug(f"Getting mail thread '{mThread["id"]}'")
      yield ((apiService.users().threads().get(userId=userId, id=mThread["id"])).execute())["messages"][0]
    
    if nextPageToken:
      #todo: make configurable (from parameter, this function should not interact with env)
      sleptSeconds = 1
      log.debug(f"Got nextPageToken, sleeping for {sleptSeconds} second(s)...")
      time.sleep(sleptSeconds)
    else:
      log.debug("Got to the end of the mail list")
      return

def main():
  log.debug("Getting credentials")
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
    log.debug("Credentials are invalid, attempting refresh")
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

  exitCode = 0
  gmailQuery = ""
  gmailMaxResults = os.getenv("GMAIL_RESULTS_PER_PAGE", "100")
  gmailUserId = os.getenv("GMAIL_USER_ID", "me")

  try:
    #? Prometheus Server
    server, t = start_http_server(int(os.getenv("PORT", "8000")))

    #? Build Gmail API
    log.info("Building Gmail API")
    service = build("gmail", "v1", credentials=creds)
    if os.getenv("BACKWARDS_LOOKUP", True):
      log.info("Backwards lookup is enabled")
    else:
      log.info("Backwards lookup is disabled")
    
    #todo: multiple senders (templates) support
    log.debug(f"Iterating over {len(mappings)} templates")
    #TODO: abstract the mappings loop in a function
    for i, mp in enumerate(mappings):
      log.debug(f"Template n°{i+1}")
      gmailQuery += f"from:{mp.sender} "
      log.debug(f"Gmail Query: '{gmailQuery}', maxResults: '{gmailMaxResults}', userId: '{gmailUserId}'")
      nextPageToken = None
      log.debug("Creating new parser")
      parser = MailParser(mp)
      log.debug("Iterating over results")
      resultsCount = 0
      while True:
        log.debug(f"Results iteration no.: '{resultsCount :+= 1}'")
        response = service.users().threads().list(userId=gmailUserId, maxResults=gmailMaxResults, q=gmailQuery, pageToken=nextPageToken).execute()
        threads = response.get("threads", [])
        for thread in threads:
          data = (service.users().threads().get(userId=gmailUserId, id=thread["id"])).execute()
          parser.timestamp = data["messages"][0]["internalDate"]
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
    time.sleep(3600)
    
  except HttpError as e:
    log.critical(f"HttpError: {e}")
    print_exc()
    exitCode = 1
  except Exception as e:
    log.critical(f"{e.__class__.__name__}: {e}")
    print_exc()
    exitCode = 1
  finally:
    server.shutdown()
    t.join()
    exit(exitCode)

if __name__ == "__main__":
  init()
  main()