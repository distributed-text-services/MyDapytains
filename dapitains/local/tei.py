from dapitains.local.citeStructure import CiteStructureParser
from dapitains.constants import PROCESSOR, get_xpath_proc
from typing import Optional, List


def normalizeXpath(xpath: List[str]) -> List[str]:
    """ Normalize XPATH split around slashes

    :param xpath: List of xpath elements
    :type xpath: [str]
    :return: List of refined xpath
    :rtype: [str]
    """
    new_xpath = []
    for x in range(0, len(xpath)):
        if x > 0 and len(xpath[x-1]) == 0:
            new_xpath.append("/"+xpath[x])
        elif len(xpath[x]) > 0:
            new_xpath.append(xpath[x])
    return new_xpath


class Document:
    def __init__(self, file_path: str):
        self.xml = PROCESSOR.parse_xml(xml_file_name=file_path)
        self.xpath_processor = get_xpath_proc(elem=self.xml)
        self.citeStructure = CiteStructureParser(
            self.xpath_processor.evaluate_single("/TEI/teiHeader/refsDecl/citeStructure")
        )

    def get_passage(self, ref: Optional[str], start: Optional[str], end: Optional[str] = None):
        """

        :param ref:
        :param start:
        :param end:
        :return:
        """
        if ref:
            start, end = ref, ref
        elif not start or not end:
            raise ValueError("Start/End or Ref are necessary to get a passage")
        start, end = normalizeXpath(start.split("/")[2:]), normalizeXpath(end.split("/")[2:])

        xml = self.textObject.xml

        if isinstance(xml, etree._Element):
            root = copyNode(xml)
        else:
            root = copyNode(xml.getroot())

        root = passageLoop(xml, root, start, end)

print(Document("/home/tclerice/dev/MyDapytains/tests/base_tei.xml"))
