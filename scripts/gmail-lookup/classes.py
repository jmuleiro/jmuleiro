import re
import emoji
import logging as log
from html.parser import HTMLParser

class EmailTemplate:
  """
  Email template class, which contain metric mappings
  """
  def __init__(self, template: dict) -> None:
    self.sender: str = template.get("sender")
    self.mappings = []
    for mp in template.get("mappings"):
      self.mappings.append(MetricMapping(mp))

class MetricMapping:
  """
  Metric/email mapping class
  """
  def __init__(self, mapping: dict) -> None:
    self.pattern = mapping.get("pattern")
    self.name = mapping.get("name", "Default Metric Name")
    self.description = mapping.get("description", "Default Metric Description")
    self.metric = mapping.get("metric")
    self.labels = mapping.get("labels")

class MailParser(HTMLParser):
  def __init__(self, template: EmailTemplate, *, convert_charrefs: bool = True) -> None:
    super().__init__(convert_charrefs=convert_charrefs)
    self.template = template
  
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
    self.processData(data)
  
  def processData(self, _d: str):
    def appendMsg(_m: str, _t: str, _M: str) -> str:
      return f"{_m}{_t.title()}: '{_M.strip()}', "
    for mp in self.template.mappings:
      msg = f"Type: {mp.name.title()}, "
      if result := re.findall(mp.pattern, _d):
        if type(result[0]) == tuple:
          for index, match in enumerate(result[0] if type(result[0]) == tuple else (result[0])):
            msg = appendMsg(msg, mp.labels[index], match)
        else:
          msg = appendMsg(msg, mp.labels[0], result[0])
        log.debug(msg)
        return
    log.warning(f"No mapping for '{_d}'")