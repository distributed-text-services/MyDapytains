import os.path
import re
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, field
import lxml.etree as ET
from dapitains.local.collection import DublinCore, Extension, Collection, CitableUnit


_re_tag = re.compile(r"[{}]")


@dataclass
class Catalog:
    relationships: List[Tuple[str, str]] = field(default_factory=list)
    objects: Dict[str, Collection] = field(default_factory=dict)


def parse_metadata(xml: ET.Element):
    obj = {
        "identifier": xml.attrib["identifier"],
        "title": xml.xpath("./title[1]/text()")[0],
        "description": (xml.xpath("./description[1]/text()") or [None])[0]
    }
    # Treat Dublin Core
    dublin_core = []
    for node in xml.xpath("./dublinCore/*"):
        tag = node.tag.split("}")[-1]
        language = node.attrib.get("{http://www.w3.org/XML/1998/namespace}lang")
        text = node.text
        dublin_core.append(DublinCore(tag, text, language))
    if dublin_core:
        obj["dublin_core"] = dublin_core

    # Treat Extension
    extensions = []
    for node in xml.xpath("./extension/*"):
        tag = _re_tag.sub("", node.tag)
        language = node.attrib.get("{http://www.w3.org/XML/1998/namespace}lang")
        text = node.text
        extensions.append(Extension(tag, text, language))
    if extensions:
        obj["extensions"] = extensions

    # Parents
    parents = []
    for node in xml.xpath("./parent/text()"):
        parents.append(str(node))
    obj["parents"] = parents

    return obj


def parse_collection(xml: ET.Element, basedir: str, tree: Catalog) -> Collection:
    obj = parse_metadata(xml)
    obj = Collection(**obj, resource=xml.tag == "resource")
    tree.objects[obj.identifier] = obj
    if xml.attrib.get("filepath"):
        obj.filepath = os.path.join(basedir, xml.attrib["filepath"])
    for member in xml.xpath("./members/*"):
        if member.xpath("./title"):
            child = parse_collection(member, basedir, tree)
            tree.relationships.append((obj.identifier, child.identifier))
        else:
            _, child = ingest_catalog(os.path.join(basedir, member.attrib["filepath"]), tree)
            tree.relationships.append((obj.identifier, child.identifier))
        for parent in child.parents:
            tree.relationships.append((parent, child.identifier))
    return obj


def ingest_catalog(path: str, tree: Optional[Catalog] = None) -> Tuple[Catalog, Collection]:
    """

    :param path:
    :return:

    >>> ingest_catalog("../../tests/catalog/example-collection.xml")
    """
    xml = ET.parse(path)
    current_dir = os.path.abspath(os.path.dirname(path))

    root: ET.Element = xml.getroot()
    tree = tree or Catalog()
    root_collection = parse_collection(root, basedir=current_dir, tree=tree)
    return tree, root_collection

