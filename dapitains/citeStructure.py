import re
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from saxonche import PyXdmNode, PySaxonProcessor, PyXPathProcessor


@dataclass
class CitableStructure:
    citeType: str
    xpath: str
    delim: str = ""
    children: List["CitableStructure"] = field(default_factory=list)


@dataclass
class CitableUnit:
    citeType: str
    identifier: str
    children: List["CitableUnit"] = field(default_factory=list)
    node: Optional[PyXdmNode] = None


def _get_xpath_proc(processor: PySaxonProcessor, elem: PyXdmNode) -> PyXPathProcessor:
    xpath = processor.new_xpath_processor()
    xpath.declare_namespace("", "http://www.tei-c.org/ns/1.0")
    xpath.set_context(xdm_item=elem)
    return xpath


def get_children_cite_structures(elem: PyXdmNode, processor: PySaxonProcessor) -> List[PyXdmNode]:
    xpath = _get_xpath_proc(processor, elem=elem).evaluate("./citeStructure")
    if xpath is not None:
        return list(iter(xpath))
    return []


class CiteStructureParser:
    """

    ToDo: Add the ability to use CiteData. This will mean moving from len(element) to len(element.xpath("./citeStructure"))
    ToDo: Add the ability to use citationTree labels
    """
    def __init__(self, root: PyXdmNode, processor: PySaxonProcessor):
        self.root = root
        self.xpath_matcher: Dict[str, str] = {}
        self.regex_pattern, cite_structure = self.build_regex_and_xpath(self.root, processor=processor)
        self.units: CitableStructure = cite_structure

    def build_regex_and_xpath(
            self,
            element,
            processor: PySaxonProcessor,
            accumulated_units=""
    ):
        """

        :param element:
        :param processor:
        :param accumulated_units:
        :return:
        """
        unit = element.get_attribute_value("unit")
        match = element.get_attribute_value("match")
        use = element.get_attribute_value("use")
        delim = element.get_attribute_value('delim')

        cite_structure = CitableStructure(
            citeType=unit,
            xpath="",
            delim=delim or ""
        )

        children_cite_struct = get_children_cite_structures(element, processor=processor)

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

        # Combine all XPath parts
        if use != "position()":
            self.xpath_matcher[accumulated_units] = f"{match}[{use}='{{{accumulated_units}}}']"
        else:
            self.xpath_matcher[accumulated_units] = f"{match}[{use}={{{accumulated_units}}}]"
        cite_structure.xpath = f"{match}/{use}"

        child_regexes = []
        parsed_children_cite_structure = []

        for child in children_cite_struct:
            child_regex, child_cite_structure = self.build_regex_and_xpath(
                child,
                accumulated_units=accumulated_units,
                processor=processor
            )
            child_regexes.append(child_regex)
            parsed_children_cite_structure.append(child_cite_structure)

        if parsed_children_cite_structure:
            cite_structure.children = parsed_children_cite_structure

        if child_regexes:
            # Join child regex patterns with logical OR (|) and ensure proper delimiters
            if len(child_regexes) > 1:
                combined_child_regex = f"(?:{'|'.join(['(?:'+cr+')' for cr in child_regexes])})?"
            else:
                combined_child_regex = f"(?:{child_regexes[0]})?"
            current_regex += combined_child_regex

        return current_regex, cite_structure

    def generate_xpath(self, reference):
        match = re.match(self.regex_pattern, reference)
        if not match:
            raise ValueError(f"Reference '{reference}' does not match the expected format.")

        match = {k:v for k, v in match.groupdict().items() if v}
        xpath = "/".join([self.xpath_matcher[key].format(**{key: value}) for key, value in match.items()])
        return xpath

    def find_refs(
            self,
            root: PyXdmNode,
            processor: PySaxonProcessor,
            structure: CitableStructure = None,
            unit: Optional[CitableUnit] = None
    ) -> List[CitableUnit]:
        xpath_proc = _get_xpath_proc(processor, elem=root)
        prefix = (unit.identifier+structure.delim) if unit else ""
        units = []
        xpath_prefix = "./" if unit else ""
        for value in xpath_proc.evaluate(f"{xpath_prefix}{structure.xpath}"):
            child = CitableUnit(
                citeType=structure.citeType,
                identifier=f"{prefix}{value.string_value}"
            )
            if unit:
                unit.children.append(child)
            else:
                units.append(child)

            if structure.children:
                target = self.generate_xpath(child.identifier)
                for child_structure in structure.children:
                    self.find_refs(
                        root=xpath_proc.evaluate_single(target),
                        processor=processor,
                        structure=child_structure,
                        unit=child
                    )
        return units


if __name__ == "__main__":
    processor = PySaxonProcessor()
    # Example usage:
    xml_string = """<TEI xmlns="http://www.tei-c.org/ns/1.0">
    <teiHeader>
        <refsDecl>
            <citeStructure unit="book" match="//body/div" use="@n">
                <citeStructure unit="chapter" match="div" use="position()" delim=" ">
                    <citeStructure unit="verse" match="div" use="position()" delim=":"/>
                    <citeStructure unit="bloup" match="l" use="position()" delim="#"/>
                </citeStructure>
            </citeStructure>
        </refsDecl>
    </teiHeader>
    <text>
    <body>
    <div n="Luke">
        <div>
            <div>Text</div>
            <div>Text 2</div>
            <l>Text 3</l>
        </div>
    </div>
    <div n="Mark">
        <div>
            <div>Text A</div>
            <div>Text B</div>
            <l>Text C</l>
        </div>
    </div>
    </body>
    </text>
    </TEI>
    """
    TEI = processor.parse_xml(xml_text=xml_string)
    xpath = _get_xpath_proc(processor, elem=TEI)
    citeStructure = xpath.evaluate_single("/TEI/teiHeader/refsDecl/citeStructure")
    parser = CiteStructureParser(citeStructure, processor)

    print(parser.find_refs(root=TEI, structure=parser.units, processor=processor))

    # Generate XPath for "Luke 1:2"
    assert parser.generate_xpath("Luke 1:2") == "//body/div[@n='Luke']/div[position()=1]/div[position()=2]"

    # Generate XPath for "Luke 1#3"
    assert parser.generate_xpath("Luke 1#3") == "//body/div[@n='Luke']/div[position()=1]/l[position()=3]"

    # Generate XPath for "Luke 1" (partial match)
    assert parser.generate_xpath("Luke 1") == "//body/div[@n='Luke']/div[position()=1]"

    # Generate XPath for "Luke 1" (partial match)
    assert parser.generate_xpath("Luke") == "//body/div[@n='Luke']"
