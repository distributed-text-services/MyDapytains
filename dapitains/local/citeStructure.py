import re
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from saxonche import PyXdmNode, PyXPathProcessor
from collections import namedtuple, defaultdict
from functools import cmp_to_key
from dapitains.constants import PROCESSOR, get_xpath_proc


@dataclass
class CiteData:
    xpath: str
    name: str
    _key: str = None

    @property
    def key(self) -> str:
        if self._key:
            return self._key
        if self.name.startswith("http://purl.org/dc/terms/"):
            self._key = "dublinCore"
        else:
            self._key = "extension"
        return self._key


@dataclass
class CitableStructure:
    citeType: str
    xpath: str
    xpath_match: str
    use: str
    delim: str = ""
    children: List["CitableStructure"] = field(default_factory=list)
    metadata: List["CiteData"] = field(default_factory=list)


@dataclass
class CitableUnit:
    citeType: str
    ref: str
    children: List["CitableUnit"] = field(default_factory=list)
    node: Optional[PyXdmNode] = None
    dublinCore: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))
    extension: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))

    def to_dts(self):
        out = {
            "citeType": self.citeType,
            "ref": self.ref
        }
        if self.children:
            out["members"] = [
                member.to_dts()
                for member in self.children
            ]
        if self.dublinCore:
            out["dublinCore"] = self.dublinCore
        if self.extension:
            out["extension"] = self.dublinCore
        return out


_simple_node = namedtuple("SimpleNode", ["citation", "xpath", "struct"])


def get_children_cite_structures(elem: PyXdmNode) -> List[PyXdmNode]:
    xpath = get_xpath_proc(elem=elem).evaluate("./citeStructure")
    if xpath is not None:
        return list(iter(xpath))
    return []


class CiteStructureParser:
    """

    ToDo: Add the ability to use CiteData. This will mean moving from len(element) to len(element.xpath("./citeStructure"))
    ToDo: Add the ability to use citationTree labels
    """
    def __init__(self, root: PyXdmNode):
        self.root = root
        self.xpath_matcher: Dict[str, str] = {}
        self.regex_pattern, cite_structure = self.build_regex_and_xpath(
            get_xpath_proc(self.root).evaluate_single("./citeStructure[1]")
        )
        self.units: CitableStructure = cite_structure

    def build_regex_and_xpath(
            self,
            element,
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
            xpath_match="",
            use=use,
            delim=delim or ""
        )

        children_cite_struct = get_children_cite_structures(element)

        citeDatas = get_xpath_proc(element).evaluate("./citeData")
        if citeDatas:
            for element in citeDatas:
                cite_structure.metadata.append(CiteData(
                    xpath=element.get_attribute_value("use"),
                    name=element.get_attribute_value("property")
                ))

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
        cite_structure.xpath_match = f"{match}[{use}]"

        child_regexes = []
        parsed_children_cite_structure = []

        for child in children_cite_struct:
            child_regex, child_cite_structure = self.build_regex_and_xpath(
                child,
                accumulated_units=accumulated_units
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
        # This is a VERY dirty trick in case we have // down the road
        xpath = xpath.replace("///", "//")
        return xpath

    def _dispatch(
            self,
            child_xpath: str,
            structure: CitableStructure,
            xpath_processor: PyXPathProcessor,
            unit: CitableUnit):
        # target = self.generate_xpath(child.ref)
        if len(structure.children) == 1:
            self.find_refs(
                root=xpath_processor.evaluate_single(child_xpath),
                structure=structure.children[0],
                unit=unit
            )
        else:
            self.find_refs_from_branches(
                root=xpath_processor.evaluate_single(child_xpath),
                structure=structure.children,
                unit=unit
            )

    def find_refs(
            self,
            root: PyXdmNode,
            structure: CitableStructure = None,
            unit: Optional[CitableUnit] = None
    ) -> List[CitableUnit]:
        xpath_proc = get_xpath_proc(elem=root)
        prefix = (unit.ref + structure.delim) if unit else ""
        units = []
        xpath_prefix = "./" if unit else ""

        for value in xpath_proc.evaluate(f"{xpath_prefix}{structure.xpath}"):
            child = CitableUnit(
                citeType=structure.citeType,
                ref=f"{prefix}{value.string_value}"
            )
            if unit:
                unit.children.append(child)
            else:
                units.append(child)

            if structure.children:
                self._dispatch(
                    child_xpath=self.generate_xpath(child.ref),
                    structure=structure,
                    xpath_processor=xpath_proc,
                    unit=child
                )
        return units

    def find_refs_from_branches(
            self,
            root: PyXdmNode,
            structure: List[CitableStructure],
            unit: Optional[CitableUnit] = None
    ) -> List[CitableUnit]:
        xpath_proc = get_xpath_proc(elem=root)
        prefix = (unit.ref) if unit else ""  # ToDo: Reinject delim
        units = []
        xpath_prefix = "./" if unit else ""

        # Custom comparison function to compare nodes by document order
        def compare_nodes_by_doc_order(node1, node2):
            # Check if node1 precedes node2 in document order
            precedes = xpath_proc.evaluate_single(f'{node1.xpath} << {node2.xpath}').string_value
            if precedes == "true":
                return -1  # node1 comes before node2

            return 1

        unsorted = []
        for s in structure:
            unsorted.extend(
                [
                    (f"{prefix}{s.delim}{value}", s)
                    for value in xpath_proc.evaluate(f"{xpath_prefix}{s.xpath}")
                ]
            )

        unsorted = [
            _simple_node(ref, self.generate_xpath(ref), struct)
            for ref, struct in unsorted
        ]
        unsorted = sorted(unsorted, key=cmp_to_key(compare_nodes_by_doc_order))

        units = []
        for elem in unsorted:
            child_unit = CitableUnit(
                citeType=elem.struct.citeType,
                ref=elem.citation
            )

            if unit:
                unit.children.append(child_unit)
            else:
                units.append(child_unit)

            if elem.struct.children:
                self._dispatch(
                    child_xpath=self.generate_xpath(child_unit.ref),
                    structure=elem.struct,
                    xpath_processor=xpath_proc,
                    unit=child_unit
                )
        return units

