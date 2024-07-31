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
