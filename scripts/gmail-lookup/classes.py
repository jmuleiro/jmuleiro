import re
import emoji
import logging as log
from html.parser import HTMLParser
from prometheus_client import Counter, Gauge, Summary, Histogram, Info, Enum

class EmailTemplate:
  """
  Email template class, which contain metric mappings
  """
  def __init__(self, template: dict) -> None:
    self.sender: str = template.get("sender")
    self.initialFilter = template.get("regexFilter", None)
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
    self.labels: list = mapping.get("labels", [])
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
      case "gauge":
        self.metric = GaugeTs(mapping.get("metric").get("name"), 
                            self.description,
                            labelnames=self.labels + ["timestamp"])

class MailParser(HTMLParser):
  def __init__(self, *, convert_charrefs: bool = True) -> None:
    super().__init__(convert_charrefs=convert_charrefs)
    
    #? Internal metrics
    self.errorsCount = Counter('mail_exporter_errors', 
                               "Number of mail exporter errors",
                               ("name", "description", "metric"))
    self.mismatchesCount = Counter('mail_exporter_mismatches',
                                  "Number of mail exporter regex mismatches in messages",
                                  ("template"))
  
  #? Timestamp property
  @property
  def timestamp(self):
    return self._timestamp
  @timestamp.setter
  def timestamp(self, value):
    # todo: validation
    self._timestamp = value

  #? Template property
  @property
  def template(self) -> EmailTemplate:
    return self._template
  @template.setter
  def template(self, value: EmailTemplate):
    self._template = value

  def handle_data(self, data: str):
    """
    Parses Gmail message payloads and drops unnecessary HTML tags and attributes.
    """
    #? Drop all lines that do not contain a dollar sign
    if self.template.initialFilter and not re.findall(self.template.initialFilter, data):
      return
    #? Remove emoji
    data = emoji.replace_emoji(data, '')
    data = re.sub(r'\D{0,9}(?>\{.*\})|(?>\@\D.*)', '', data)
    #? Remove whitespaces and commas
    data = re.sub(r'\n|\r|\t|\0|,', '', data).strip()
    self.processData(data)
  
  def processData(self, _d: str):
    for mp in self.template.mappings:
      if result := re.search(mp.pattern, _d):
        self.processMapping(result.groupdict(), mp)
        return
    log.warning(f"No mapping for '{_d}'")
    self.mismatchesCount.labels({"template": self.template.sender}).inc()
  
  def processMapping(self, result: dict[str, str], mapping: MetricMapping):
    log.debug(f"Processing metric '{mapping.metricName}' type '{type(mapping.metric)}' with values: {result}, result type: {type(result)}")
    if (len(mapping.labels) and len(mapping.labels) != (len(result) - 1)):
      log.error(f"Labels and capturing groups mismatch: Got {len(mapping.labels)} labels but {len(result)} groups (including value)")
      self.errorsCount.labels(name=mapping.metricName, description=mapping.description, metric=mapping.metric._name).inc()
      return
    
    value = float(result.pop("value"))
    self.updateMetric(mapping, result, value)
  
  def updateMetric(self, mapping: MetricMapping, labels: dict[str, str], value: float = 1):
    #todo: support other metric types aside from gauge
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
        mapping.metric.incTimestamped(labels, value, self.timestamp)

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

  def incTimestamped(self, labels: dict[str, str], value: float, timestamp):
    """
    Increments timestamped gauge with labels
    """
    log.debug(f"Increment timestamped gauge labels: {labels}, value: {value}, timestamp: {timestamp}")
    labels.update({
      "timestamp": timestamp
    })
    self.labels(**labels).inc(value)
  