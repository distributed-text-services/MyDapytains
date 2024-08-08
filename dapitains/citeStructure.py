import re
from typing import Dict, List
import saxonche


def _cite_structures(elem: saxonche.PyXdmNode, processor: saxonche.PySaxonProcessor) -> List[saxonche.PyXdmNode]:
    xpath = processor.new_xpath_processor()
    xpath.set_context(xdm_item=elem)
    xpath.declare_namespace("", "http://www.tei-c.org/ns/1.0")
    xpath = xpath.evaluate("./citeStructure")
    if xpath is not None:
        return list(iter(xpath))
    return []


class CiteStructureParser:
    """

    ToDo: Add the ability to use CiteData. This will mean moving from len(element) to len(element.xpath("./citeStructure"))
    ToDo: Add the ability to use citationTree labels
    """
    def __init__(self, root: saxonche.PyXdmNode, processor: saxonche.PySaxonProcessor):
        self.root = root
        self.xpathes: Dict[str, str] = {}
        self.regex_pattern, dts_like_trees = self.build_regex_and_xpath(self.root, processor=processor)
        self.levels = dts_like_trees

    def build_regex_and_xpath(self, element, processor: saxonche.PySaxonProcessor, accumulated_units=""):
        unit = element.get_attribute_value("unit")
        match = element.get_attribute_value("match")
        use = element.get_attribute_value("use")
        delim = element.get_attribute_value('delim')

        dts_like_tree = {"citeType": unit}

        children_cite_struct = _cite_structures(element, processor=processor)

        # Accumulate unit names for unique regex group names
        accumulated_units = f"{accumulated_units}__{unit}" if accumulated_units else unit

        if not match or not use:
            return "", ""

        allowed_values = "."
        if len(children_cite_struct):
            allowed_values = rf"[^{re.escape(''.join([child.get_attribute_value('delim') for child in children_cite_struct]))}]"

        # Base regex for the current unit
        if delim:
            current_regex = rf"(?:{re.escape(delim)}(?P<{accumulated_units}>{allowed_values}+))"
        else:
            current_regex = rf"(?P<{accumulated_units}>{allowed_values}+)"

        xpath_part = f"{match}[{use}='{{{accumulated_units}}}']"

        xpath_parts = [xpath_part]
        child_regexes = []
        child_dts_like_trees = []

        for child in children_cite_struct:
            child_regex, child_cite_structure = self.build_regex_and_xpath(
                child,
                accumulated_units=accumulated_units,
                processor=processor
            )
            child_regexes.append(child_regex)
            child_dts_like_trees.append(child_cite_structure)

        if child_dts_like_trees:
            dts_like_tree["citeStructure"] = child_dts_like_trees

        if child_regexes:
            # Join child regex patterns with logical OR (|) and ensure proper delimiters
            if len(child_regexes) > 1:
                combined_child_regex = f"(?:{'|'.join(['(?:'+cr+')' for cr in child_regexes])})?"
            else:
                combined_child_regex = f"(?:{child_regexes[0]})?"
            current_regex += combined_child_regex

        # Combine all XPath parts
        self.xpathes[accumulated_units] = "/".join(xpath_parts)

        return current_regex, dts_like_tree

    def generate_xpath(self, reference):
        match = re.match(self.regex_pattern, reference)
        if not match:
            raise ValueError(f"Reference '{reference}' does not match the expected format.")

        match = {k:v for k, v in match.groupdict().items() if v}
        xpath = "/".join([self.xpathes[key].format(**{key: value}) for key, value in match.items()])
        return xpath


if __name__ == "__main__":
    processor = saxonche.PySaxonProcessor()
    # Example usage:
    xml_string = """
    <citeStructure unit="book" match="//body/div" use="@n" xmlns="http://www.tei-c.org/ns/1.0">
        <citeStructure unit="chapter" match="div" use="position()" delim=" ">
            <citeStructure unit="verse" match="div" use="position()" delim=":"/>
            <citeStructure unit="bloup" match="l" use="position()" delim="#"/>
        </citeStructure>
    </citeStructure>
    """
    root = processor.parse_xml(xml_text=xml_string)[0]
    parser = CiteStructureParser(root, processor)

    # Generate XPath for "Luke 1:2"
    assert parser.generate_xpath("Luke 1:2") == "//body/div[@n='Luke']/div[position()='1']/div[position()='2']"

    # Generate XPath for "Luke 1#3"
    assert parser.generate_xpath("Luke 1#3") == "//body/div[@n='Luke']/div[position()='1']/l[position()='3']"

    # Generate XPath for "Luke 1" (partial match)
    assert parser.generate_xpath("Luke 1") == "//body/div[@n='Luke']/div[position()='1']"

    # Generate XPath for "Luke 1" (partial match)
    assert parser.generate_xpath("Luke") == "//body/div[@n='Luke']"
