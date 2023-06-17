## Setup
The script only works with [Google Application Default Credentials](https://cloud.google.com/docs/authentication/application-default-credentials) (ADC). 
1. It is required to have the [gcloud CLI](https://cloud.google.com/sdk/docs/install) installed in order to run the script properly. To set up application default credentials:
```bash
gcloud auth application-default login
```

2. Install Python dependencies:
```bash
pip3 install -r requirements.txt
```