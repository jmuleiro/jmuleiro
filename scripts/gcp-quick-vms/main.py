import sys
import string
import secrets
import logging
import argparse
from typing import Any
from google.cloud import compute_v1 as compute
from google.api_core.extended_operation import ExtendedOperation

def getLogFormat(color = None, reset = "\x1b[0m"):
  return f'%(asctime)s::{color if color else ""}%(levelname)s{reset if color else ""} >>> %(message)s'

class Formatter(logging.Formatter):
  debug = "\x1b[38;5;254m"
  info = "\x1b[38;5;38m"
  warning = "\x1b[38;5;208m"
  error = "\x1b[38;5;196m"
  critical = "\x1b[31;1m"
  reset = "\x1b[0m"

  FORMATS = {
    logging.DEBUG: debug + getLogFormat() + reset,
    logging.INFO: debug + getLogFormat(info),
    logging.WARNING: warning + getLogFormat() + reset,
    logging.ERROR: error + getLogFormat() + reset,
    logging.CRITICAL: critical + getLogFormat() + reset
  }

  def format(self, record):
    logfmt = self.FORMATS.get(record.levelno)
    f = logging.Formatter(logfmt)
    return f.format(record)
    
def initLogging(level: str):
  #* Get log level id from environment variable
  match level.upper():
    case 'DEBUG':
      logLevelId = logging.DEBUG
    case 'WARNING':
      logLevelId = logging.WARNING
    case 'ERROR':
      logLevelId = logging.ERROR
    case 'CRITICAL':
      logLevelId = logging.CRITICAL
    case _:
      logLevelId = logging.INFO
  logger = logging.getLogger()
  logger.setLevel(logLevelId)
  handler = logging.StreamHandler()
  handler.setStream(sys.stdout)
  handler.setLevel(logLevelId)
  handler.setFormatter(Formatter())
  logger.addHandler(handler)

#TODO: get args using functional approach
def getArgs() -> object:
  pass

#? From https://github.com/GoogleCloudPlatform/python-docs-samples/blob/HEAD/compute/client_library/snippets/instances/create.py
def getImageFromFamily(project: str, family: str):
  client = compute.ImagesClient()
  return client.get_from_family(project=project, family=family)

def diskFromImage(type: str, size: int, image: str, autoDelete: bool = True, boot: bool = True) -> compute.AttachedDisk:
  """
    Args:
      type: Disk type
      size: Disk size
      boot: Indicates whether disk should be used as boot disk
      image: Image to use in the following format: "projects/{project_name}/global/images/{image_name}"
      autoDelete: Whether the disk should be deleted alongside the virtual machine
  """
  bootDisk = compute.AttachedDisk()
  params = compute.AttachedDiskInitializeParams()
  params.source_image = image
  params.disk_size_gb = size
  params.disk_type = type
  bootDisk.initialize_params = params
  bootDisk.auto_delete = autoDelete
  bootDisk.boot = boot
  return bootDisk

def waitForExtendedOperation(operation: ExtendedOperation, name: str = "operation", timeout: int = 300) -> Any:
  result = operation.result(timeout=timeout)

  if operation.error_code:
    logging.error(
      f"Error during {name}: [Code: {operation.error_code}]: {operation.error_message}"
      f"Operation ID: {operation.name}"
    )
    raise operation.exception() or RuntimeError(operation.error_message)
  
  if operation.warnings:
    logging.debug(f"Warnings during {name}")
    for warning in operation.warnings:
      logging.warning(f"[Code: {warning.code}: {warning.message}]")
  
  return result

def createInstance(
    project: str,
    name: str,
    zone: str,
    disks: list[compute.AttachedDisk],
    username: str,
    pwd: str,
    machine: str = "n1-standard-1",
    externalAccess: bool = True,
    spot: bool = True,
    displayDevice: bool = True
  ):
  client = compute.InstancesClient()
  networkInterface = compute.NetworkInterface()
  networkInterface.name = "global/networks/default"

  if externalAccess:
    access = compute.AccessConfig()
    access.type_ = compute.AccessConfig.Type.ONE_TO_ONE_NAT.name
    access.name = "External NAT"
    access.network_tier = access.NetworkTier.PREMIUM.name
    networkInterface.access_configs = [access]
  
  instance = compute.Instance()
  instance.network_interfaces = [networkInterface]
  instance.name = name
  instance.disks = disks
  instance.machine_type = f"zones/{zone}/machineTypes/{machine}"
  instance.metadata = compute.Metadata()
  startupScriptItem = compute.Items()
  startupScriptItem.key = "startup-script"
  startupScriptItem.value = f"""
  #!/bin/bash
  set -e
  export DEBIAN_FRONTEND="noninteractive"
  export LANG="en_US.UTF-8"
  echo -e 'LANG="en_US.UTF-8"\\nLANGUAGE="en_US:en"\\n' > /etc/default/locale
  apt-get -qq update
  apt-get -qq install xrdp
  systemctl enable --now xrdp
  adduser xrdp ssl-cert
  systemctl restart xrdp
  useradd -m -p '{pwd}' {username}
  apt-get -qq install task-gnome-desktop tigervnc-standalone-server tigervnc-common tightvncserver
  systemctl set-default graphical.target
  mkdir /home/{username}/.vnc
  echo '{pwd}' | vncpasswd -f > /home/{username}/.vnc/passwd
  chown -R {username}:{username} /home/{username}/.vnc
  chmod 0600 /home/{username}/.vnc/passwd
  su -c 'vncserver -localhost no' - {username}
  """
  instance.metadata.items = [startupScriptItem]

  if spot:
    instance.scheduling = compute.Scheduling()
    instance.scheduling.provisioning_model = (
      compute.Scheduling.ProvisioningModel.SPOT.name
    )
  
  if displayDevice:
    instance.display_device = compute.DisplayDevice()
    instance.display_device.enable_display = True
  
  # Request
  request = compute.InsertInstanceRequest()
  request.zone = zone
  request.project = project
  request.instance_resource = instance

  logging.info(f"Creating instance {name} in {zone}...")
  operation = client.insert(request=request)
  
  waitForExtendedOperation(operation, "instance creation")

  logging.info(f"Instance {name} successfully created.")


if __name__ == '__main__':
  import os
  import uuid
  import random
  import google.auth
  import google.auth.exceptions

  initLogging(os.getenv('LOG_LEVEL', logging.WARNING))
  parser = argparse.ArgumentParser()
  parser.add_argument('count')
  parser.add_argument('machine_type')
  args = parser.parse_args()
  vmCount = args.count
  vmMachine = args.machine_type
  logging.debug(f"""
  VM Count: {vmCount}
  Machine Type: {vmMachine}
  """)
  
  zones = ["southamerica-east1-a", "southamerica-east1-b", "southamerica-east1-c"]

  try:
    projectId = google.auth.default()[1]
  except google.auth.exceptions.DefaultCredentialsError:
    logging.critical(
      "Please run `gcloud auth application-default login`"
      "or set GOOGLE_APPLICATION_CREDENTIALS to a credentials path to execute this script."
    )
  else:
    sharedId = "quickvms-" + uuid.uuid4().hex[:10]
    for i in range(0, int(vmCount)):
      instanceName = f"{sharedId}-{i}"
      instanceZone = random.choice(zones)
      instanceImage = getImageFromFamily(
        project="debian-cloud", family="debian-11"
      )
      diskType = f"zones/{instanceZone}/diskTypes/pd-ssd"
      disks = [diskFromImage(diskType, 10, instanceImage.self_link)]
      alphabet = string.ascii_letters + string.digits
      randomTemporaryPassword = ''.join(secrets.choice(alphabet) for i in range(8))
      username = "remote"
      createInstance(projectId, instanceName, instanceZone, disks, username, randomTemporaryPassword, vmMachine)
      logging.info(f"""
                  Created all Virtual Machines. Remote desktop has been installed.
                  Get instance IPs by running:
                  `gcloud compute instances list`
                  Username: {username}
                  Shared password: {randomTemporaryPassword}
                  """)