import re
import emoji
import logging as log
from html.parser import HTMLParser
from typing import Union, overload
from prometheus_client import Counter, Gauge, Summary, Histogram, Info, Enum

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
    self.labels: list = mapping.get("labels")
    self.metricName = mapping.get("metric").get("name")
    #todo: add schema properties for metric attributes 
    #todo: i.e. namespace, unit, etc.
    #todo: add states for enum type
    match mapping.get("metric").get("type", "gauge"):
      case "counter":
        self.metric = Counter(mapping.get("metric").get("name"), 
                              self.description, 
                              labelnames=self.labels + ["timestamp"])
      case "summary":
        self.metric = Summary(mapping.get("metric").get("name"),
                              self.description,
                              labelnames=self.labels + ["timestamp"])
      case "histogram":
        self.metric = Histogram(mapping.get("metric").get("name"),
                              self.description,
                              labelnames=self.labels + ["timestamp"])
      case "info":
        self.metric = Info(mapping.get("metric").get("name"),
                              self.description,
                              labelnames=self.labels + ["timestamp"])
      case "enum":
        self.metric = Enum(mapping.get("metric").get("name"),
                              self.description,
                              labelnames=self.labels + ["timestamp"])
      case "gauge" | _:
        self.metric = GaugeTs(mapping.get("metric").get("name"), 
                            self.description,
                            labelnames=self.labels + ["timestamp"])

class MailParser(HTMLParser):
  def __init__(self, template: EmailTemplate, *, convert_charrefs: bool = True) -> None:
    super().__init__(convert_charrefs=convert_charrefs)
    self.template = template
    
    #? Internal metrics
    self.errorsCount = Counter('mail_exporter_errors', 
                               "Number of mail exporter errors",
                               ("name", "description", "metric"))
  
  def get_timestamp(self):
    return self._timestamp
  
  def set_timestamp(self, value):
    # todo: validation
    self._timestamp = value

  timestamp = property(get_timestamp, set_timestamp)

  def handle_data(self, data: str):
    """
    Parses Gmail message payloads and drops unnecessary HTML tags and attributes.
    """
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
    for mp in self.template.mappings:
      if result := re.findall(mp.pattern, _d):
        self.processMapping(result, mp)
        return
    log.warning(f"No mapping for '{_d}'")
  
  def processMapping(self, result: Union[list|str], mapping: MetricMapping):
    log.debug(f"Processing metric '{mapping.metricName}' type '{type(mapping.metric)}' with values: {result}, result type: {type(result)}")
    if (len(mapping.labels) == 1 and type(result) == list) or (len(mapping.labels) != 1 and type(result) == str):
      #todo: investigate errors
      log.error(f"Labels and capturing groups mismatch: Got {len(mapping.labels)} labels and {1 if type(result) != list else len(result)} capturing group")
      self.errorsCount.labels(name=mapping.metricName, description=mapping.description, metric=mapping.metric._name)
      return
    
    if type(result) == list:
      labels = {}
      for i, match in enumerate(result[0]):
        #todo: get rid of "value" label somehow
        #if mapping.labels[i] != "value":
        #  labels.update({
        #    mapping.labels[i]: match
        #  })
        #else:
        #  value = match
        if mapping.labels[i] == "value":
          value = float(match)
        labels.update({
          mapping.labels[i]: match
        })
      self.updateMetric(mapping, labels=labels, value=value)
    else:
      self.updateMetric(mapping, value=value)
  
  def updateMetric(self, mapping: MetricMapping, labels: dict[str, str] = None, value: float = 1):
    match mapping.metric:
      case Counter():
        pass
      case Summary():
        pass
      case Histogram():
        pass
      case Info():
        pass
      case Enum():
        pass
      case GaugeTs():
        if labels:
          mapping.metric.incTimestamped(labels, value, self.timestamp)
        else:
          mapping.metric.incTimestamped(value, self.timestamp)
class GaugeTs(Gauge):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

  #fyi https://github.com/prometheus/client_python/issues/588
  def collect(self):
    metrics = super().collect()
    for metric in metrics:
      samples = []
      for sample in metric.samples:
        timestamp = sample.labels.pop("timestamp", None)
        samples.append(type(sample)(sample.name, sample.labels, sample.value, timestamp, sample.exemplar))
      metric.samples = samples
    return metrics

  @overload
  def incTimestamped(self, value: float, timestamp):
    """
    Increments a timestamped gauge's value
    """
    log.debug(f"Increment timestamped gauge value: {value}, timestamp: {timestamp}")
    self.labels({"timestamp": timestamp}).inc(value)

  def incTimestamped(self, labels: dict[str, str], value: float, timestamp):
    """
    Increments timestamped gauge with labels
    """
    log.debug(f"Increment timestamped gauge labels: {labels}, value: {value}, timestamp: {timestamp}")
    labels.update({
      "timestamp": timestamp
    })
    self.labels(**labels).inc(value)
  