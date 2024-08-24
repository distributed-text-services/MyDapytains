from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DublinCore:
    term: str
    value: str
    language: Optional[str] = None

    def json(self):
        return {"property": f"http://purl.org/dc/terms/{self.term}", "value": self.value, "language": self.language}


class Extension(DublinCore):
    term: str
    value: str
    language: Optional[str] = None

    def json(self):
        return {"property": self.term, "value": self.value, "language": self.language}


@dataclass
class Collection:
    identifier: str
    title: str
    description: Optional[str] = None
    dublin_core: List[DublinCore] = field(default_factory=list)
    extension: List[Extension] = field(default_factory=list)
    resource: bool = False
    filepath: Optional[str] = None

    def json(self):
        return {
            "identifier": self.identifier,
            "title": self.title,
            "description": self.description,
            "dublin_core": self.dublin_core,
            "extension": self.extension,
            "resource": self.resource,
            "filepath": self.filepath
        }

@dataclass
class CitableUnit:
    resource: str
    reference: str
    children: List[str] = field(default_factory=list)
    dublin_core: List[DublinCore] = field(default_factory=list)
    extension: List[Extension] = field(default_factory=list)
