import xml.etree.ElementTree as ET
import re
from typing import Dict


class CiteStructureParser:
    """

    ToDo: Add the ability to use CiteData. This will mean moving from len(element) to len(element.xpath("./citeStructure"))
    ToDo: Add the ability to return DTS-like citationTree, using @n of the root citeStructure for the label
    """
    def __init__(self, xml_string):
        self.root = ET.fromstring(xml_string)
        self.xpathes: Dict[str, str] = {}
        self.regex_pattern = self.build_regex_and_xpath(self.root)
        self.levels = []

    def build_regex_and_xpath(self, element, accumulated_units="", parent_delim=""):
        unit = element.attrib["unit"]
        match = element.attrib["match"]
        use = element.attrib["use"]
        delim = element.attrib.get('delim', '')

        # Accumulate unit names for unique regex group names
        accumulated_units = f"{accumulated_units}__{unit}" if accumulated_units else unit

        if not match or not use:
            return "", ""

        allowed_values = "."
        if len(element):
            allowed_values = rf"[^{re.escape(''.join([child.attrib['delim'] for child in element]))}]"

        # Base regex for the current unit
        if delim:
            current_regex = rf"(?:{re.escape(delim)}(?P<{accumulated_units}>{allowed_values}+))"
        else:
            current_regex = rf"(?P<{accumulated_units}>{allowed_values}+)"

        xpath_part = f"{match}[{use}='{{{accumulated_units}}}']"

        xpath_parts = [xpath_part]
        child_regexes = []

        for child in element:
            child_regex = self.build_regex_and_xpath(child, accumulated_units, delim)
            child_regexes.append(child_regex)

        if child_regexes:
            # Join child regex patterns with logical OR (|) and ensure proper delimiters
            if len(child_regexes) > 1:
                combined_child_regex = f"(?:{'|'.join(['(?:'+cr+')' for cr in child_regexes])})?"
            else:
                combined_child_regex = f"(?:{child_regexes[0]})?"
            current_regex += combined_child_regex

        # Combine all XPath parts
        self.xpathes[accumulated_units] = "/".join(xpath_parts)

        return current_regex

    def generate_xpath(self, reference):
        match = re.match(self.regex_pattern, reference)
        if not match:
            raise ValueError(f"Reference '{reference}' does not match the expected format.")

        match = {k:v for k, v in match.groupdict().items() if v}
        xpath = "/".join([self.xpathes[key].format(**{key: value}) for key, value in match.items()])
        return xpath


if __name__ == "__main__":

    # Example usage:
    xml_string = """
    <citeStructure unit="book" match="//body/div" use="@n">
        <citeStructure unit="chapter" match="div" use="position()" delim=" ">
            <citeStructure unit="verse" match="div" use="position()" delim=":"/>
            <citeStructure unit="bloup" match="l" use="position()" delim="#"/>
        </citeStructure>
    </citeStructure>
    """
    parser = CiteStructureParser(xml_string)

    # Generate XPath for "Luke 1:2"
    assert parser.generate_xpath("Luke 1:2") == "//body/div[@n='Luke']/div[position()='1']/div[position()='2']"

    # Generate XPath for "Luke 1#3"
    assert parser.generate_xpath("Luke 1#3") == "//body/div[@n='Luke']/div[position()='1']/l[position()='3']"

    # Generate XPath for "Luke 1" (partial match)
    assert parser.generate_xpath("Luke 1") == "//body/div[@n='Luke']/div[position()='1']"

    # Generate XPath for "Luke 1" (partial match)
    assert parser.generate_xpath("Luke") == "//body/div[@n='Luke']"
