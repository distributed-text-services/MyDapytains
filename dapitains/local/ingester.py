import os.path
import re
from typing import Dict, Optional
import lxml.etree as ET
from dapitains.local.collections import DublinCore, Extension, Collection, CitableUnit


_re_tag = re.compile(r"[{}]")


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

    return obj


def parse_collection(xml: ET.Element, basedir: str, tree: Dict[str, Collection]) -> Collection:
    obj = parse_metadata(xml)
    obj = Collection(**obj, resource=xml.tag == "resource")
    tree[obj.identifier] = obj
    for member in xml.xpath("./members/*"):
        if member.xpath("./title"):
            parse_collection(member, basedir, tree)
            # ToDo: deal with children ?
        else:
            ingest_catalog(os.path.join(basedir, member.attrib["filepath"]), tree)
    return obj


def ingest_catalog(path: str, tree: Optional[Dict[str, Collection]] = None) -> Dict[str, Collection]:
    """

    :param path:
    :return:

    >>> ingest_catalog("../../tests/catalog/example-collection.xml")
    """
    xml = ET.parse(path)
    current_dir = os.path.abspath(os.path.dirname(path))

    root: ET.Element = xml.getroot()
    tree = tree or {}
    parse_collection(root, basedir=current_dir, tree=tree)
    return tree
