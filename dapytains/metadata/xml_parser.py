import os.path
import re
from typing import Dict, Optional, List, Tuple, Any
from dataclasses import dataclass, field
import lxml.etree as ET
from dapytains.metadata.classes import DublinCore, Extension, Collection


__all__ = ["Catalog", "parse"]


_re_tag = re.compile(r"[{}]")


@dataclass
class Catalog:
    relationships: List[Tuple[str, str]] = field(default_factory=list)
    objects: Dict[str, Collection] = field(default_factory=dict)


def _parse_metadata(xml: ET.Element) -> Tuple[Dict[str, Any], List[str]]:
    """ Parse Metadata

    :param xml: Collection/Resource tag
    :returns: Main metadata obj Resource or Collection objects
    """
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
    for node in xml.xpath("./extensions/*"):
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

    return obj, parents


def _parse_collection(xml: ET.Element, basedir: str, tree: Catalog, filepath: Optional[str] = None) -> Collection:
    """ Parse a Collection or Resource object

    :param xml: Parsed Collection or Resource by LXML
    :param basedir: Directory used to resolve filepath, that are relative to the main object
    :param tree: Catalog that is updated with objects.
    """
    obj, parents = _parse_metadata(xml)
    obj = Collection(**obj, resource=xml.tag == "resource")
    obj._metadata_filepath = filepath
    for parent in parents:
        tree.relationships.append((parent, obj.identifier))
    tree.objects[obj.identifier] = obj
    if xml.attrib.get("filepath") and obj.resource:
        obj.filepath = os.path.normpath(os.path.join(basedir, xml.attrib["filepath"]))
    for member in xml.xpath("./members/*"):
        if member.xpath("./title"):
            child = _parse_collection(member, basedir, tree)
            tree.relationships.append((obj.identifier, child.identifier))
        else:
            _, child = parse(os.path.join(basedir, member.attrib["filepath"]), tree)
            tree.relationships.append((obj.identifier, child.identifier))
    return obj


def parse(path: str, tree: Optional[Catalog] = None) -> Tuple[Catalog, Collection]:
    """ Ingest a collection description file.

    :param path: Path to a Collection XML File, see the schema at tests/catalog/schema.rng
    :param tree: Current catalog, which is either updated or created
    :return: Catalog and root collection found at path.

    """
    xml = ET.parse(path)
    current_dir = os.path.abspath(os.path.dirname(path))

    root: ET.Element = xml.getroot()
    tree = tree or Catalog()
    root_collection = _parse_collection(root, basedir=current_dir, tree=tree, filepath=path)
    return tree, root_collection
