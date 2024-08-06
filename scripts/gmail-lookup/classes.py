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
    self.labels = mapping.get("labels")
    self.metricName = mapping.get("metric").get("name")
    #todo: add schema properties for metric attributes 
    #todo: i.e. namespace, unit, etc.
    #todo: add states for enum type
    match mapping.get("metric").get("type", "gauge"):
      case "counter":
        self.metric = Counter(mapping.get("metric").get("name"), 
                              self.description, 
                              labelnames=self.labels)
      case "summary":
        self.metric = Summary(mapping.get("metric").get("name"),
                              self.description,
                              labelnames=self.labels)
      case "histogram":
        self.metric = Histogram(mapping.get("metric").get("name"),
                              self.description,
                              labelnames=self.labels)
      case "info":
        self.metric = Info(mapping.get("metric").get("name"),
                              self.description,
                              labelnames=self.labels)
      case "enum":
        self.metric = Enum(mapping.get("metric").get("name"),
                              self.description,
                              labelnames=self.labels)
      case "gauge" | _:
        self.metric = Gauge(mapping.get("metric").get("name"), 
                            self.description,
                            labelnames=self.labels)

class MailParser(HTMLParser):
  def __init__(self, template: EmailTemplate, *, convert_charrefs: bool = True) -> None:
    super().__init__(convert_charrefs=convert_charrefs)
    self.template = template
    
    #? Internal metrics
    self.errorsCount = Counter('mail_exporter_errors', 
                               "Number of mail exporter errors",
                               ("name", "description", "metric"))
  
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
          for index, match in enumerate(result[0]):
            msg = appendMsg(msg, mp.labels[index], match)
        else:
          msg = appendMsg(msg, mp.labels[0], result[0])
        #self.processMetric(result[0], mp)
        log.debug(msg)
        return
    log.warning(f"No mapping for '{_d}'")
  
  def processMetric(self, result: Union[tuple|str], mapping: MetricMapping):
    log.debug(f"Processing metric '{mapping.metricName}' type '{type(mapping.metric)}' with values: {result}")
    if (len(mapping.labels) == 1 and type(result) == tuple) or (len(mapping.labels) != 1 and type(result) == str):
      log.error(f"Labels and capturing groups mismatch: Got {len(mapping.labels)} labels and {1 if type(result) != tuple else len(result)} capturing group")
      self.errorsCount.labels(name=mapping.metricName, description=mapping.description, metric=mapping.metric._name)
      return
    
    if type(result) == tuple:
      # If result is tuple, we have at least 1 label aside from the metric value
      labelValues = []
      for i, match in enumerate(result[0]):
        if mapping.labels[i] != "value":
          labelValues.append(match)
        else:
          value = match
      self.updateMetricWithLabels(mapping, labelValues, value)
    else:
      #self.updateMetricWithValue
      pass
  
  def updateMetricWithLabels(self, mapping: MetricMapping, labelValues: list, value: any = 1):
    match mapping.metric.__qualname__:
      case Counter.__qualname__:
        mapping.metric.labels(labelValues).inc(value)
      case Summary.__qualname__:
        pass
      case Histogram.__qualname__:
        pass
      case Info.__qualname__:
        pass
      case Enum.__qualname__:
        pass
      case Gauge.__qualname__ | _:
        pass
class GaugeTs(Gauge):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

  #fyi https://github.com/prometheus/client_python/issues/588
  #def collect(self):
  #  metrics = super().collect()
  #  for metric in metrics:
  #    samples = []
  #    for sample in metric.samples:
  #      timestamp = sample.labels.pop("timestamp", None)
  #      samples.append(type(sample)(sample.name, sample.labels, sample.value, timestamp, sample.exemplar))
  #    metric.samples = samples
  #  return metrics
  
  @overload
  def set(self, value: float, timestamp: any | None) -> None:
    self._raise_if_not_observable()
    self._value.set(float(value), timestamp=timestamp)