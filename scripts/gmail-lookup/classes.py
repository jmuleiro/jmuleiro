class EmailTemplate:
  """
  Email template class, which contain metric mappings
  """
  def __init__(self, template: dict) -> None:
    #todo: validate with regex
    self.sender: str = template.get("sender")
    self.mappings = MetricMapping(template.get("mappings"))

#todo: validation
class MetricMapping:
  """
  Metric/email mapping class
  """
  def __init__(self, name: str, mapping: dict) -> None:
    self.name = name
    self.labels: list[str] = mapping.get("labels")
  
