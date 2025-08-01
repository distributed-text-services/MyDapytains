from saxonche import PyXPathProcessor

from dapytains.tei.citeStructure import CiteStructureParser, CitableUnit
from dapytains.processor import get_xpath_proc, get_processor, saxonlib
from typing import Optional, List, Tuple, Dict, Union
from lxml.etree import fromstring, tostring, ElementTree, ElementBase
from lxml.objectify import Element, SubElement, StringElement, ObjectifiedElement
from lxml import objectify
import re
from dapytains.errors import UnknownTreeName

COPY_UNTIL_END = -1
_namespace = re.compile(r"Q{(?P<namespace>[^}]+)}(?P<tagname>.+)")


def xpath_split(string: str) -> List[str]:
    return [x for x in re.split(r"/(/?[^/]+)", string) if x]


def xpath_walk(xpath: List[str]) -> Tuple[str, List[str], List[str]]:
    """ Format at XPath for perform XPath

    :param xpath: XPath element lists
    :return: Tuple where the first element is an XPath representing the next node to retrieve and the second the list \
    of other elements to find
    """
    if len(xpath) > 1:
        current, queue = xpath[0], xpath[1:]
        current_filled = "./{}[./{}]".format(
            current,
            "/".join(queue)
        )
    else:
        current_filled, queue = "./{}".format(xpath[0]), []

    return current_filled, queue, [xpath[0]] if len(xpath) > 1 else []


def is_traversing_xpath(parent: saxonlib.PyXdmNode, xpath: str, processor: saxonlib.PySaxonProcessor) -> bool:
    """ Check if an XPath is traversing more than one level

    :param parent:
    :param xpath:
    :return:
    """
    xpath_proc = get_xpath_proc(parent, processor=processor)
    if xpath.startswith(".//"):
        # If the XPath starts with .//, we try to see if we have a direct child that matches
        drct_xpath = xpath.replace(".//", "./", 1)
        if xpath_proc.effective_boolean_value(f"head({xpath}) is head({drct_xpath})"):
            return False
        else:
            return True
    return False


def xpath_walk_step(parent: saxonlib.PyXdmNode, xpath: str, processor: saxonlib.PySaxonProcessor
                    ) -> Tuple[saxonlib.PyXdmItem, bool]:
    """ Perform an XPath on an element to find a child that is part of the XPath.
    If the child is a direct member of the path, returns a False boolean indicating to move
        onto the next element.
    If the child is not directly mentioned in the path (such as through //xpath),
        provide a true boolean indicating that the XPath that was run is still valid.

    :param parent: XML Node on which to perform XPath
    :param xpath: XPath to run
    :return: (Result, Validity of the original XPath)
    """
    xpath_proc = get_xpath_proc(parent, processor=processor)
    # We check first for loops, because that changes the xpath
    if xpath.startswith(".//"):
        if is_traversing_xpath(parent, xpath, processor=processor):
            return xpath_proc.evaluate_single(f"./*[{xpath}]"), True
        else:
            return xpath_proc.evaluate_single(xpath), False
    else:
        return xpath_proc.evaluate_single(xpath), False


def _get_text(context, xpath: str, processor: saxonlib.PySaxonProcessor) -> Optional[str]:
    _xq = processor.new_xquery_processor()
    _xq.set_context(xdm_item=context)
    return _xq.run_query_to_string(query_text=(
        "declare namespace output = 'http://www.w3.org/2010/xslt-xquery-serialization';"
        "declare option output:omit-xml-declaration 'yes';"
        f"{xpath}"
    ))

def _get_sibling_xpath(node_xpath: str, prefix: str = ".", ancestor: str = "") -> str:
    if node_xpath == "node()":
        return "./following-sibling::node()"

    return (f"let $end := following-sibling::node()[{prefix}/descendant-or-self::{node_xpath}] "
            f"return (./following-sibling::node() [. << $end])")



def _add_space_tail(element: ElementBase, node: saxonlib.PyXdmNode, processor: saxonlib.PySaxonProcessor) -> None:
    """ This function reintroduces whitespace between nodes. We use xQuery processor which does not strip space..."""
    if node.node_kind_str == "text":
        return

    if len(node.children) and node.children[0] is not None:
        possible_indent: saxonlib.PyXdmNode = node.children[0]
        if possible_indent.node_kind_str == "text" and not (element.text and element.text.strip()):
            if content := _get_text(possible_indent, ".", processor=processor):
                if not content.strip():
                    if hasattr(element, "_setText"):
                        element._setText(content)
                    else:
                        element.text = content

    if element.tail is None or len(element.tail) == 0:
        tail = _get_text(node, "following-sibling::node()[1]", processor=processor)
        if tail is not None and not tail.strip():
            element.tail = str(tail)


def _prune(node: saxonlib.PyXdmNode, milestone: str, processor: saxonlib.PySaxonProcessor) -> str:
    xq = processor.new_xquery_processor()
    xq.set_context(xdm_item=node)
    query = """declare namespace output = 'http://www.w3.org/2010/xslt-xquery-serialization';
declare default element namespace 'http://www.tei-c.org/ns/1.0';
declare option output:omit-xml-declaration 'yes';
declare function local:prune($node) {
  if ($node instance of element()) then
    let $before := $node/node()[. << $node/descendant-or-self::"""+milestone+"""[1]]
    return  (: Missing return here :)
      if (not($node/descendant-or-self::"""+milestone+""")) then $node
      else element {name($node)} {
        $node/@*,  (: Preserve attributes :)
        for $child in $before return local:prune($child)  (: Recursively process children :)
      }
  else $node  (: Preserve text, comments, etc. :)
};
local:prune(.)"""
    x = xq.run_query_to_string(query_text=query)
    return x


def copy_node(
        node: saxonlib.PyXdmNode,
        processor: saxonlib.PySaxonProcessor,
        include_children=False,
        parent: Optional[Element] = None,
        remove_milestone: Optional[Union[str, int]] = None
):
    """ Copy an XML Node

    :param node: Etree Node
    :param include_children: Copy children nodes if set to True
    :param parent: Append copied node to parent if given
    :param include_spaces: Include the tailing spaces
    :return: New Element
    """
    if include_children:
        # We simply go from the element as a string to an element as XML.
        # We need to workaround false indentation through this xQuery
        if isinstance(remove_milestone, str):
            element = _prune(node, remove_milestone, processor=processor)
        else:
            xq = processor.new_xquery_processor()
            xq.set_context(xdm_item=node)
            element = xq.run_query_to_string(query_text=(
                "declare namespace output = 'http://www.w3.org/2010/xslt-xquery-serialization';"
                "declare option output:omit-xml-declaration 'yes';"
                "."
            ))
        if element.startswith("<"):
            element = fromstring(element)
            if parent is not None:
                parent.append(element)
            _add_space_tail(element, node, processor=processor)
            return element
        elif parent is not None:
            if not parent.getchildren():
                if not isinstance(parent, (StringElement, ObjectifiedElement)):
                    parent.text = (parent.text or "") + element
            else:
                parent.getchildren()[-1].tail = element
            return parent

    if node is None:
        raise TypeError("A None element has been provided to copy-node")

    attribs = {
        attr.name.replace("Q{", "{"): attr.string_value  # Q{ => xml:id
        for attr in node.attributes
    }
    namespace, node_name = _namespace.match(node.name).groups()

    kwargs = dict(
        _tag=node_name,
        nsmap={None: namespace},
        **attribs  # Somehow, using that instead of attribs will
                   # force SubElement to create a <text> tag instead of text()
    )

    if parent is not None:
        element = SubElement(parent, **kwargs)
        _add_space_tail(element, node, processor=processor)
    else:
        element = Element(**kwargs)

    return element


def normalize_xpath(xpath: List[str]) -> List[str]:
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


def reverse_ancestor(xpaths: List[str]) -> str:
    if not xpaths:
        return ""
    strip = re.compile(r"^([./]+)")
    here = f"[ancestor::{strip.sub('', xpaths[0])}{reverse_ancestor(xpaths[1:]) if len(xpaths) > 1 else ''}]"
    return here


def _treat_siblings(
        context_node: saxonlib.PyXdmNode,
        last_node: ElementBase,
        xpath: str,
        processor: saxonlib.PySaxonProcessor,
        ancestor_list: Optional[List[str]] = None
) -> Optional[ElementBase]:
    """ Copies siblings of the nodes that needs to be copied as content

    :param context_node: Node against which xPath are run
    :param last_node: Node on which data is created
    :param xpath: xPath of the sibling
    :param prefix: Ancestor path for the sibling at this point
    """
    xproc = get_xpath_proc(context_node, processor=processor)
    loc_xpath = "node()" if xpath == COPY_UNTIL_END else xpath
    if ancestor_list:
        loc_xpath += f"{reverse_ancestor(ancestor_list[::-1])}"

    if xproc.effective_boolean_value(f"not(following-sibling::node()[descendant-or-self::{loc_xpath}] or .//{loc_xpath})"):
        new_xpath = _get_sibling_xpath("node()")
    else:
        new_xpath = _get_sibling_xpath(loc_xpath)

    next_nodes = xpath_eval(xproc, new_xpath)
    for node in next_nodes:
        if node.node_kind_str == "text":
            if not last_node.tail:
                last_node.tail = _get_text(node, ".", processor=processor)
        else:
            if xpath != "node()":
                last_node = copy_node(
                    node,
                    include_children=True,
                    parent=last_node.getparent(),
                    remove_milestone=xpath,
                    processor=processor
                )
            else:
                last_node = copy_node(node, include_children=True, parent=last_node.getparent(), processor=processor)

    if next_nodes and loc_xpath != "node()":
        sibling_with_data = xproc.evaluate_single(f"following-sibling::node()[descendant::{loc_xpath}]")
        if sibling_with_data is not None:
            copy_node(
                sibling_with_data,
                include_children=True,
                parent=last_node.getparent(),
                remove_milestone=xpath,
                processor=processor
            )


def xpath_eval(proc: PyXPathProcessor, xpath) -> List:
    return proc.evaluate(xpath) or []


def clean_xpath_for_following(current_xpath: str, traversing: bool) -> str:
    if traversing and current_xpath.startswith(".//"):
        return f"*[{current_xpath}]"
    elif not traversing and current_xpath.startswith(".//"):
        return current_xpath[3:]
    else:
        return current_xpath[2:]


def reconstruct_doc(
    root: saxonlib.PyXdmNode,
    start_xpath: List[str],
    processor: saxonlib.PySaxonProcessor,
    new_tree: Optional[Element] = None,
    end_xpath: Optional[List[str]] = None,
    start_siblings: Optional[Union[str, int]] = None,
    end_siblings: Optional[Union[str, int]] = None,
    copy_until: bool = False
) -> Element:
    """ Loop over passages to construct and increment new tree given a parent and XPaths

    :param root: Parent on which to perform xpath
    :param new_tree: Parent on which to add nodes
    :param start_xpath: List of xpath elements
    :type start_xpath: [str]
    :param end_xpath: List of xpath elements
    :type end_xpath: [str]
    :param start_siblings: If siblings of starts need to be captured, provide the XPATH here. If == COPY_UNTIL_END, copy until ends
    :param end_siblings: If siblings of end need to be captured, provide XPath here.  If == COPY_UNTIL_END, copy until ends
    :return: Newly incremented tree

    """
    current_start, queue_start, ancestor_start = xpath_walk(start_xpath)
    xpath_proc = get_xpath_proc(root, processor=processor)
    # There are too possibilities:
    #  1. What we call loop is when the first element that match this XPath, such as "//body", then we will need
    #     to loop over ./TEI, then ./text and finally we'll get out of the loop at body.
    #     Basically, in a loop, the XPath does not change until we reach the first element
    #     of the XPath (here ./body)
    #  2. The second option is that we do not loop. Simple he ?
    result_start, start_is_traversing = xpath_walk_step(root, current_start, processor=processor)

    current_end, queue_end = None, None

    if start_is_traversing is True:
        queue_start = start_xpath
        # If we loop and both xpath are the same,
        #    then we have the same current and queue
        if end_xpath == start_xpath:
            current_end, queue_end = current_start, queue_start

    # If we were not in any single edge case for end_xpath, run the xpath_walk
    if current_end is None:
        current_end, queue_end, ancestor_end = xpath_walk(end_xpath)

    # Here, we start by comparing both XPath, in case we have a single XPath
    current_1_is_current_2 = start_xpath == end_xpath
    # If they don't match, maybe an XPath comparison of both items will tell us more
    if not current_1_is_current_2:
        # If we don't, we do an XPath check
        current_1_is_current_2 = xpath_proc.effective_boolean_value(f"head({current_start}) is head({current_end})")

    # We check first whether we have the same root
    if current_1_is_current_2:

        # If we need to copy preceding node, because we got uneven weird things
        if new_tree is not None and copy_until:
            _sib_xpath = clean_xpath_for_following(current_start, start_is_traversing)
            for sibling in xpath_eval(
                    xpath_proc,
                    f"./node()[following-sibling::{_sib_xpath}]"
            ):
                copy_node(sibling, include_children=True, parent=new_tree, processor=processor)

        # We get the children if the XPath stops here
        # We copy the node we found
        copied_node = copy_node(
            result_start,
            include_children=len(queue_start) == 0,
            parent=new_tree,
            processor=processor
        )

        # Given that both XPath returns the same node, we still need to check if end is looping
        #   We optimize by avoiding this check when start and end are the same
        if start_xpath != end_xpath and is_traversing_xpath(root, current_end, processor=processor):
            queue_end = end_xpath

        # If we have a child XPath, then continue the job
        if len(queue_start):
            reconstruct_doc(
                root=result_start,
                new_tree=copied_node,
                start_xpath=queue_start,
                end_xpath=queue_end,
                start_siblings=start_siblings,
                end_siblings=end_siblings, processor=processor
            )
        if start_siblings:
            _treat_siblings(context_node=result_start, xpath=start_siblings, last_node=copied_node,
                            ancestor_list=ancestor_start, processor=processor)
        return copied_node
    else:
        # There is a situation where we do not have the same XPath, but we have the same node,
        # typically in // situations
        current_root_positional_path = generate_root_path(xpath_proc, f"self::node()")

        # We did not even have the same root, most likely because of a citeStructure match=//p use=n
        #  which leads to current_root_positional_path to be empty (because the xpath to the root
        #  is empty).
        if not current_root_positional_path:
            common_node = xpath_proc.evaluate_single("/*")
            new_tree = copy_node(
                common_node, processor=processor,
                include_children=False, parent=new_tree
            )

            # Given that both XPath returns the same node, we still need to check if end is looping
            #   We optimize by avoiding this check when start and end are the same
            if start_xpath != end_xpath and is_traversing_xpath(root, current_end, processor=processor):
                queue_end = end_xpath

            reconstruct_doc(
                common_node,
                new_tree=new_tree,
                start_xpath=queue_start,
                end_xpath=queue_end,
                start_siblings=start_siblings,
                end_siblings=end_siblings,
                processor=processor
            )
            return new_tree

        # Otherwise, we check if we do not have similar node even if we don't have the same XPath
        xpath_length = len(current_root_positional_path)
        current_start_positional_path = generate_root_path(xpath_proc, f"{current_start}")
        current_end_positional_path = generate_root_path(xpath_proc, f"{current_end}")
        if current_start_positional_path[:xpath_length+1] == current_end_positional_path[:xpath_length+1]:
            common_node = xpath_proc.evaluate_single("".join(current_start_positional_path[:xpath_length+1]))
            new_tree = copy_node(
                common_node, processor=processor,
                include_children=False, parent=new_tree
            )

            # Given that both XPath returns the same node, we still need to check if end is looping
            #   We optimize by avoiding this check when start and end are the same
            if start_xpath != end_xpath and is_traversing_xpath(root, current_end, processor=processor):
                queue_end = end_xpath

            new_tree = reconstruct_doc(
                common_node,
                new_tree=new_tree,
                start_xpath=queue_start,
                end_xpath=queue_end,
                start_siblings=start_siblings,
                end_siblings=end_siblings,
                processor=processor
            )
            return new_tree

        # If we still don't have the same children as a result of start and end,
        #   We make sure to retrieve the element at the end of 2
        result_end, end_is_traversing = xpath_walk_step(root, current_end, processor=processor)
        # If end_xpath results in a loop, then loop end_xpath
        if end_is_traversing:
            queue_end = end_xpath

        # We start by copying start.
        parent_start = copy_node(
            result_start,
            include_children=len(queue_start) == 0,
            parent=new_tree,
            processor=processor
        )
        # If we have a queue, we run the queue
        if queue_start:
            if end_siblings and not start_siblings:
                # We have an end_siblings elsewhere, what we want is to cover what we find below, and we take everything
                # but the next level !
                start_siblings = "node()"

            reconstruct_doc(
                result_start,
                new_tree=parent_start,
                start_xpath=queue_start,
                end_xpath=queue_start,
                start_siblings=start_siblings,
                processor=processor
            )

        # When we don't have similar node, we loop on siblings until we get to the expected element
        #  For this reason, we need to change matching xpath (ie. ./div[position()=1]) into compatible
        #  suffixes with preceding-sibling or following-sibling.
        # We do that for start and end
        sib_current_start = clean_xpath_for_following(current_start, start_is_traversing)
        sib_current_end = clean_xpath_for_following(current_end, end_is_traversing)

        # We look for siblings between start and end matches
        xpath = get_xpath_proc(root, processor=processor)
        for sibling in xpath_eval(xpath, f"./node()[preceding-sibling::{sib_current_start} and following-sibling::{sib_current_end}]"):
            copy_node(sibling, include_children=True, parent=new_tree, processor=processor)

        # Here we reached the end, logically.
        node = copy_node(node=result_end, include_children=len(queue_end) == 0, parent=new_tree, processor=processor)

        if queue_end:
            # Check if the first element is the same as queue_end
            preview, *_ = xpath_walk(queue_end)
            xpath_proc.set_context(xdm_item=result_end)

            reconstruct_doc(
                root=result_end,
                new_tree=node,
                start_xpath=queue_end,
                end_xpath=queue_end,
                start_siblings=end_siblings,
                copy_until=not xpath_proc.effective_boolean_value(f"head(./element()[1]) is head({preview})"),
                processor=processor
            )
        if end_siblings:
            _treat_siblings(context_node=result_end, xpath=end_siblings, last_node=node, ancestor_list=ancestor_end,
                            processor=processor)
    return new_tree

def generate_path(processor: PyXPathProcessor, xpath: str) -> str:
    """Generate the positional xpath of an element

    e.g. `generate_path(proc, "//p[@n='1'")` -> /TEI[1]/text[1]/body[1].../p[1]
    """
    return str(
        processor.evaluate_single(
            f"string-join(\n"
            f"          for $n in ({xpath}/ancestor-or-self::*)\n"
            f"          return\n"
            f"            concat('/', name($n), '[', 1 + count($n/preceding-sibling::*[name() = name($n)]), ']'),\n"
            f"          ''\n"
            f"        )"
        )
    )

def generate_root_path(processor: PyXPathProcessor, xpath: str) -> List[str]:
    """ Get the root element of the current path

    e.g. `generate_root_path(proc, "//p[@n='1'")` -> [/TEI[1]. /text[1], ....]
    """
    return list(map(str, xpath_eval(processor,
            f"          for $n in ({xpath}/ancestor-or-self::*)\n"
            f"          return\n"
            f"            concat('/', name($n), '[', 1 + count($n/preceding-sibling::*[name() = name($n)]), ']')"
        )))




class Document:
    def __init__(self, file_path: str, processor: Optional[saxonlib.PySaxonProcessor] = None):
        self.xml_processor = processor if isinstance(processor, saxonlib.PySaxonProcessor) else get_processor()
        self.xml = self.xml_processor.parse_xml(xml_file_name=file_path)
        self.xpath_processor = get_xpath_proc(elem=self.xml, processor=self.xml_processor)
        self.citeStructure: Dict[Optional[str], CiteStructureParser] = {}

        default = None
        for refsDecl in xpath_eval(self.xpath_processor, "/TEI/teiHeader/encodingDesc/refsDecl[./citeStructure]"):
            struct = CiteStructureParser(refsDecl, processor=self.xml_processor)

            self.citeStructure[refsDecl.get_attribute_value("n") or "default"] = struct

            if refsDecl.get_attribute_value("default") == "true" or default is None:
                default = refsDecl.get_attribute_value("n") or "default"

        self.default_tree: str = default

    def get_passage(self, ref_or_start: Optional[str], end: Optional[str] = None, tree: Optional[str] = None) -> Element:
        """ Retrieve a given passage from the document

        :param ref_or_start: First element of a range or single ref
        :param end: End of a range
        :param tree: Name of a specific tree
        """
        if ref_or_start and not end:
            start, end = ref_or_start, None
        elif ref_or_start and end:
            start, end = ref_or_start, end
        elif ref_or_start is None and end is end:
            return fromstring(self.xml.to_string())
        else:
            raise ValueError("Start/End or Ref are necessary to get a passage")

        tree = tree or self.default_tree
        try:
            start_xpath = self.citeStructure[tree].generate_xpath(start)
        except KeyError:
            raise UnknownTreeName(tree)

        start_xpath_norm = normalize_xpath(xpath_split(start_xpath))
        start_sibling = None
        end_sibling = None

        if end:
            end_xpath = self.citeStructure[tree].generate_xpath(end)
            end_xpath_norm = normalize_xpath(xpath_split(end_xpath))
            if self.xpath_processor.effective_boolean_value(f"count({end_xpath}) and count({end_xpath}/node())=0"):
                next_ref = self.get_next(tree, end)
                if next_ref:
                    next_ref = next_ref.ref
                    next_ref_xpath = normalize_xpath(xpath_split(self.citeStructure[tree].generate_xpath(next_ref)))[-1]
                    end_sibling = next_ref_xpath.strip("/")
                else:
                    end_sibling = COPY_UNTIL_END
        else:
            end_xpath_norm = start_xpath_norm
            if self.xpath_processor.effective_boolean_value(f"count({start_xpath}) and count({start_xpath}/node())=0"):
                next_ref = self.get_next(tree, start)
                if next_ref:
                    next_ref = next_ref.ref
                    next_ref_xpath = normalize_xpath(xpath_split(self.citeStructure[tree].generate_xpath(next_ref)))[-1]
                    start_sibling = next_ref_xpath.strip("/")
                else:
                    start_sibling = COPY_UNTIL_END


        root = reconstruct_doc(
            self.xml,
            new_tree=None,
            start_xpath=start_xpath_norm,
            end_xpath=end_xpath_norm,
            start_siblings=start_sibling,
            end_siblings=end_sibling,
            processor=self.xml_processor
        )
        objectify.deannotate(root, cleanup_namespaces=True)
        return root

    def get_reffs(self, tree: Optional[str] = None):
        tree = self.citeStructure[tree or self.default_tree]
        return tree.find_refs(root=self.xml, structure=tree.structure)

    def get_next(self, tree, unit) -> Optional[CitableUnit]:
        refs = self.get_reffs(tree)
        def _find(haystack, needle) -> Optional[Tuple[int, CitableUnit, List[CitableUnit]]]:
            for idx, r in enumerate(haystack):
                if r.ref == needle:
                    return idx, r, haystack
                else:
                    if c := _find(r.children, unit):
                        return c
            return None
        current_idx, current_unit, siblings = _find(refs, unit)
        if current_idx < len(refs)-1:
            return siblings[current_idx+1]
        return None
