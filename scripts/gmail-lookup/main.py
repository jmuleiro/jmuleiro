import os
import logging
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

#* OAuth Scopes
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

def main():
  creds = None
  tokenFile = os.getenv("OAUTH_TOKEN_FILENAME", "token.json")
  credentialsFile = os.getenv("OAUTH_CREDENTIALS_FILENAME", "credentials.json")

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
  
  gmailResultsPerPage = os.getenv("GMAIL_RESULTS_PER_PAGE", "50")
  gmailUserId = os.getenv("GMAIL_USER_ID")
  gmailQuery = ""

  try:
    service = build("gmail", "v1", credentials=creds)
    messages = service.users().messages().list(userId=gmailUserId, maxResults=gmailResultsPerPage, q=gmailQuery)
    print(messages)
    
  except HttpError as error:
    print(f"HttpError: {error}")

if __name__ == "__main__":
  main()