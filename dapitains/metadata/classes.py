from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DublinCore:
    term: str
    value: str
    language: Optional[str] = None

    def json(self):
        if self.language:
            return {"property": f"http://purl.org/dc/terms/{self.term}", "value": self.value, "lang": self.language}
        else:
            return {"property": f"http://purl.org/dc/terms/{self.term}", "value": self.value}


class Extension(DublinCore):
    term: str
    value: str
    language: Optional[str] = None

    def json(self):
        if self.language:
            return {"property": self.term, "value": self.value, "language": self.language}
        else:
            return {"property": self.term, "value": self.value}


@dataclass
class Collection:
    identifier: str
    title: str
    description: Optional[str] = None
    dublin_core: List[DublinCore] = field(default_factory=list)
    extensions: List[Extension] = field(default_factory=list)
    resource: bool = False
    filepath: Optional[str] = None

    def json(self):
        return {
            "identifier": self.identifier,
            "title": self.title,
            "description": self.description,
            "dublin_core": self.dublin_core,
            "extension": self.extensions,
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
