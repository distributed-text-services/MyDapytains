import re
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from collections import namedtuple, defaultdict
from dapytains.processor import get_xpath_proc, saxonlib

_pos_re = re.compile(r'\[(\d+)\]')


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
    match: str = ""
    # True when this unit's matched element is self-closing (a "milestone", e.g. <cb/>),
    # meaning any nested citeStructure children are siblings bounded by the next milestone
    # of the same kind, not actual descendants.
    milestone: bool = False

    def get(self, ref: str):
        if self.use != "position()":
            return f"{self.match}[{self.use}='{ref}']"
        return f"{self.match}[{self.use}={ref}]"

    def json(self):
        out = {
            "citeType": self.citeType,
        }
        if self.children:
            out["citeStructure"] = [
                child.json()
                for child in self.children
            ]
        return out


@dataclass
class CitableUnit:
    citeType: str
    ref: str
    children: List["CitableUnit"] = field(default_factory=list)
    node: Optional[saxonlib.PyXdmNode] = None
    dublinCore: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))
    extension: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))
    level: int = 1
    parent: Optional[str] = None

    def json(self):
        out = {
            "citeType": self.citeType,
            "identifier": self.ref,
            "level": self.level,
            "parent": self.parent
        }
        if self.children:
            out["members"] = [
                member.json()
                for member in self.children
            ]
        if self.dublinCore:
            out["dublinCore"] = dict(self.dublinCore)
        if self.extension:
            out["extension"] = dict(self.extension)
        return out


_simple_node = namedtuple("SimpleNode", ["citation", "xpath", "struct"])


def get_children_cite_structures(elem: saxonlib.PyXdmNode, processor: saxonlib.PySaxonProcessor) -> List[saxonlib.PyXdmNode]:
    xpath = get_xpath_proc(elem=elem, processor=processor).evaluate("./citeStructure")
    if xpath is not None:
        return list(iter(xpath))
    return []


class CiteStructureParser:
    """

    ToDo: Add the ability to use CiteData. This will mean moving from len(element) to len(element.xpath("./citeStructure"))
    ToDo: Add the ability to use citationTree labels
    """
    def __init__(self, root: saxonlib.PyXdmNode, processor: saxonlib.PySaxonProcessor):
        self.root = root
        self.processor: saxonlib.PySaxonProcessor = processor
        self.xpath_matcher: Dict[str, str] = {}
        self.structure_by_key: Dict[str, CitableStructure] = {}
        # `root` is the <refsDecl> element, not the document root: milestone-mode helpers need
        # the actual document node since they evaluate relative ("./...") match expressions
        # globally (bounded by document order), not relative to <refsDecl>.
        self.doc_root: saxonlib.PyXdmNode = get_xpath_proc(self.root, processor=processor).evaluate_single("/")
        self.regex_pattern, cite_structure = self.build_regex_and_xpath(
            get_xpath_proc(self.root, processor=processor).evaluate_single("./citeStructure[1]")
        )
        self.structure: CitableStructure = cite_structure

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

        children_cite_struct = get_children_cite_structures(element, processor=self.processor)

        citeDatas = get_xpath_proc(element, processor=self.processor).evaluate("./citeData")
        if citeDatas is not None:
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
        cite_structure.match = match
        self.structure_by_key[accumulated_units] = cite_structure

        if children_cite_struct:
            first_match = get_xpath_proc(self.doc_root, processor=self.processor).evaluate_single(f"({match})[1]")
            if first_match is not None and not len(first_match.children):
                cite_structure.milestone = True

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

    def _milestone_boundary(
            self,
            start_node: saxonlib.PyXdmNode,
            parent_match: str
    ) -> Optional[saxonlib.PyXdmNode]:
        """ Find the next node matching `parent_match` after `start_node`, i.e. the next
        milestone of the same kind (e.g. the next <cb/> after the current one). """
        xpath_proc = get_xpath_proc(self.doc_root, processor=self.processor)
        xpath_proc.declare_variable("__start")
        xpath_proc.set_parameter("__start", start_node)
        return xpath_proc.evaluate_single(f"({parent_match})[. >> $__start][1]")

    def _milestone_window(
            self,
            start_node: saxonlib.PyXdmNode,
            boundary_node: Optional[saxonlib.PyXdmNode],
            child_xpath: str
    ):
        """ Evaluate `child_xpath` against the whole document and restrict the result to nodes
        occurring after `start_node` and (if given) before `boundary_node`, in document order. """
        xpath_proc = get_xpath_proc(self.doc_root, processor=self.processor)
        xpath_proc.declare_variable("__start")
        xpath_proc.set_parameter("__start", start_node)
        if boundary_node is not None:
            xpath_proc.declare_variable("__boundary")
            xpath_proc.set_parameter("__boundary", boundary_node)
            return xpath_proc.evaluate(f"({child_xpath})[. >> $__start][not(. >> $__boundary)]")
        return xpath_proc.evaluate(f"({child_xpath})[. >> $__start]")

    def _absolute_path(self, node: saxonlib.PyXdmNode) -> str:
        """ Turn a concrete node into its real, DOM-accurate absolute positional XPath
        (e.g. /TEI[1]/text[1]/body[1]/div[1]/ab[1]/lb[5]), so it can flow through the rest of
        the pipeline (document.py's reconstruct_doc) exactly like any other absolute XPath. """
        xpath_proc = get_xpath_proc(node, processor=self.processor)
        return str(xpath_proc.evaluate_single(
            "string-join(for $n in (ancestor-or-self::*) "
            "return concat('/', name($n), '[', 1 + count($n/preceding-sibling::*[name() = name($n)]), ']'), '')"
        ))

    def _parse_reference(self, reference: str) -> List[tuple]:
        match = re.match(self.regex_pattern, reference)
        if not match:
            raise ValueError(f"Reference '{reference}' does not match the expected format.")
        return [(k, v) for k, v in match.groupdict().items() if v]

    def is_milestone_nested(self, reference: str) -> bool:
        """ True if `reference`'s deepest unit is nested (directly or transitively) under a
        milestone-mode parent (e.g. a <lb/> under a <cb/>), in which case any tag/attribute
        based xpath fragment derived from it is not safe to reuse as a sibling-boundary match
        (the same attribute value can occur in other milestones, e.g. line "1" of every column). """
        groups = self._parse_reference(reference)
        return any(self.structure_by_key[key].milestone for key, _ in groups[:-1])

    def _resolve_groups(self, groups: List[tuple]) -> Optional[saxonlib.PyXdmNode]:
        """ Resolve a (possibly partial, e.g. groups[:-1]) ordered list of (key, value) ref
        groups to its concrete node, walking the chain level by level so that ancestor
        disambiguation (e.g. "which page's column 2") is preserved at every step. """
        xpath_proc = get_xpath_proc(self.doc_root, processor=self.processor)
        concrete_node = None
        prev_structure: Optional[CitableStructure] = None
        for key, value in groups:
            formatted = self.xpath_matcher[key].format(**{key: value})
            structure = self.structure_by_key[key]
            if concrete_node is None:
                concrete_node = xpath_proc.evaluate_single(f"({formatted})[1]")
            elif prev_structure.milestone:
                boundary = self._milestone_boundary(concrete_node, prev_structure.match)
                concrete_node = (self._milestone_window(concrete_node, boundary, formatted) or [None])[0]
            else:
                local_proc = get_xpath_proc(concrete_node, processor=self.processor)
                concrete_node = local_proc.evaluate_single(f"./{formatted}")
            prev_structure = structure
        return concrete_node

    def resolve_node(self, reference: str) -> Optional[saxonlib.PyXdmNode]:
        """ Resolve `reference` to its concrete node. """
        return self._resolve_groups(self._parse_reference(reference))

    def generate_xpath(self, reference):
        groups = self._parse_reference(reference)

        # Fast path: untouched, original behavior when no ancestor in the chain is a milestone.
        if not any(self.structure_by_key[key].milestone for key, _ in groups[:-1]):
            xpath = "/".join([self.xpath_matcher[key].format(**{key: value}) for key, value in groups])
            # This is a VERY dirty trick in case we have // down the road
            return xpath.replace("///", "//")

        # Milestone-aware path: resolve to a concrete node step by step, since milestone parents
        # (self-closing elements like <cb/>) cannot be joined with their children via "/", then
        # turn it into its real, DOM-accurate absolute positional XPath so it flows through the
        # rest of the pipeline (document.py's reconstruct_doc) like any other absolute XPath.
        return self._absolute_path(self.resolve_node(reference))

    def get_next_milestone_boundary(self, reference: str) -> Optional[saxonlib.PyXdmNode]:
        """ If `reference`'s deepest unit is nested directly under a milestone-mode parent
        (e.g. a <lb/> under a <cb/>), return the concrete node of the next occurrence of that
        parent unit (e.g. the next <cb/>). Used as an upper bound for passage extraction when
        there is no next sibling within the current milestone (e.g. last line of a column),
        so content does not bleed into the next milestone's content (e.g. the next column).
        Returns None if not applicable (no milestone parent, or no next occurrence). """
        groups = self._parse_reference(reference)
        if len(groups) < 2:
            return None

        parent_key, _ = groups[-2]
        parent_structure = self.structure_by_key[parent_key]
        if not parent_structure.milestone:
            return None

        # Resolve the parent through the full ancestor chain (groups[:-1]), not just its own
        # value in isolation: e.g. "column 2" is ambiguous on its own when nested under "page",
        # since column @n values repeat across pages.
        start_node = self._resolve_groups(groups[:-1])
        return self._milestone_boundary(start_node, parent_structure.match)

    def _dispatch(
            self,
            child_xpath: str,
            structure: CitableStructure,
            xpath_processor: saxonlib.PyXPathProcessor,
            unit: CitableUnit,
            level: int):
        # target = self.generate_xpath(child.ref)
        target_root = xpath_processor.evaluate_single(child_xpath)
        milestone_match = structure.match if structure.milestone else None
        if len(structure.children) == 1:
            self.find_refs(
                root=target_root,
                structure=structure.children[0],
                unit=unit,
                level=level,
                milestone_match=milestone_match
            )
        else:
            self.find_refs_from_branches(
                root=target_root,
                structure=structure.children,
                unit=unit,
                level=level,
                milestone_match=milestone_match
            )

    def find_refs(
            self,
            root: saxonlib.PyXdmNode,
            structure: CitableStructure = None,
            unit: Optional[CitableUnit] = None,
            level: int = 1,
            milestone_match: Optional[str] = None
    ) -> List[CitableUnit]:
        xpath_proc = get_xpath_proc(elem=root, processor=self.processor)
        prefix = (unit.ref + structure.delim) if unit else ""
        units = []

        if milestone_match is not None:
            # `root` is a self-closing milestone node (e.g. <cb/>): its "children" are
            # whatever matches structure.xpath between it and the next node matching
            # milestone_match (the next milestone of the same kind), not its descendants.
            boundary = self._milestone_boundary(root, milestone_match)
            values = self._milestone_window(root, boundary, structure.xpath) or []
        else:
            xpath_prefix = "./" if unit else ""
            # .evaluate returns None instead of an empty list...
            values = xpath_proc.evaluate(f"{xpath_prefix}{structure.xpath}") or []

        for value in values:
            child = CitableUnit(
                citeType=structure.citeType,
                ref=f"{prefix}{value.string_value}",
                parent=unit.ref if unit else None,
                level=level
            )

            if structure.metadata:
                local_xproc = get_xpath_proc(xpath_proc.evaluate_single(self.generate_xpath(child.ref)),
                                             processor=self.processor)
                for cite_data in structure.metadata:
                    if metadata_found := local_xproc.evaluate(cite_data.xpath):
                        for metadata_value in metadata_found:
                            child.__getattribute__(cite_data.key)[cite_data.name].append(
                                metadata_value.get_string_value()
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
                    unit=child,
                    level=level+1
                )
        return units

    def find_refs_from_branches(
            self,
            root: saxonlib.PyXdmNode,
            structure: List[CitableStructure],
            unit: Optional[CitableUnit] = None,
            level: int = 1,
            milestone_match: Optional[str] = None
    ) -> List[CitableUnit]:
        xpath_proc = get_xpath_proc(elem=root, processor=self.processor)
        prefix = (unit.ref) if unit else ""  # ToDo: Reinject delim
        units = []
        xpath_prefix = "./" if unit else ""

        boundary = self._milestone_boundary(root, milestone_match) if milestone_match is not None else None

        unsorted = []
        for s in structure:
            if milestone_match is not None:
                results = self._milestone_window(root, boundary, s.xpath)
            else:
                results = xpath_proc.evaluate(f"{xpath_prefix}{s.xpath}")
            if results is not None:
                unsorted.extend(
                    [
                        (f"{prefix}{s.delim}{value}", s)
                        for value in results
                    ]
                )

        unsorted = [
            _simple_node(ref, self.generate_xpath(ref), struct)
            for ref, struct in unsorted
        ]
        # Generate a positional path key for each node once (O(n) JVM calls) and sort
        # natively, rather than calling back into Saxon for every pairwise comparison
        # (which would cost O(n log n) JVM round-trips).
        def _doc_order_key(node):
            # Count ALL preceding element siblings (not just same-name) so that
            # mixed-name siblings at the same level sort in document order.
            path_str = str(xpath_proc.evaluate_single(
                f"string-join(for $n in ({node.xpath}/ancestor-or-self::*) "
                f"return concat('/', name($n), '[', 1 + count($n/preceding-sibling::*), ']'), '')"
            ))
            return tuple(int(x) for x in _pos_re.findall(path_str))

        unsorted = sorted(unsorted, key=_doc_order_key)

        units = []
        for elem in unsorted:
            child_unit = CitableUnit(
                citeType=elem.struct.citeType,
                ref=elem.citation,
                level=level,
                parent=unit.ref if unit else None
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
                    unit=child_unit,
                    level=level+1
                )
        return units

