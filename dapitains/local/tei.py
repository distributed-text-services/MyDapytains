from dapitains.local.citeStructure import CiteStructureParser
from dapitains.constants import PROCESSOR, get_xpath_proc
from typing import Optional, List, Tuple, Dict
from lxml.etree import fromstring
from lxml.objectify import Element, SubElement
from lxml import objectify
from saxonche import PyXdmNode, PyXPathProcessor
import re
from dapitains.errors import UnknownTreeName


_namespace = re.compile(r"Q{(?P<namespace>[^}]+)}(?P<tagname>.+)")


def xpath_walk(xpath: List[str]) -> Tuple[str, List[str]]:
    """ Format at XPath for perform XPath

    :param xpath: XPath element lists
    :return: Tuple where the first element is an XPath representing the next node to retrieve and the second the list \
    of other elements to find
    """
    if len(xpath) > 1:
        current, queue = xpath[0], xpath[1:]
        current = "./{}[./{}]".format(
            current,
            "/".join(queue)
        )
    else:
        current, queue = "./{}".format(xpath[0]), []

    return current, queue


def is_traversing_xpath(parent: PyXdmNode, xpath: str) -> bool:
    """ Check if an XPath is traversing more than one level

    :param parent:
    :param xpath:
    :return:
    """
    xpath_proc = get_xpath_proc(parent)
    if xpath.startswith(".//"):
        # If the XPath starts with .//, we try to see if we have a direct child that matches
        drct_xpath = xpath.replace(".//", "./", 1)
        if xpath_proc.effective_boolean_value(f"head({xpath}) is head({drct_xpath})"):
            return False
        else:
            return True
    return False


def xpath_walk_step(parent: PyXdmNode, xpath: str) -> Tuple[PyXdmNode, bool]:
    """ Perform an XPath on an element to find a child that is part of the XPath.
    If the child is a direct member of the path, returns a False boolean indicating to move
        onto the next element.
    If the child is not directly mentioned in the path (such as through //xpath),
        provide a true boolean indicating that the XPath that was run is still valid.

    :param parent: XML Node on which to perform XPath
    :param xpath: XPath to run
    :return: (Result, Validity of the original XPath)
    """
    xpath_proc = get_xpath_proc(parent)
    # We check first for loops, because that changes the xpath
    if xpath.startswith(".//"):
        if is_traversing_xpath(parent, xpath):
            return xpath_proc.evaluate_single(f"./*[{xpath}]"), True
        else:
            return xpath_proc.evaluate_single(xpath), False
    else:
        return xpath_proc.evaluate_single(xpath), False


def copy_node(node: PyXdmNode, include_children=False, parent: Optional[Element] = None):
    """ Copy an XML Node

    :param node: Etree Node
    :param include_children: Copy children nodes if set to True
    :param parent: Append copied node to parent if given
    :return: New Element
    """
    if include_children:
        # We simply go from the element as a string to an element as XML.
        element = fromstring(node.to_string())
        if parent is not None:
            parent.append(element)
        return element

    attribs = {
        attr.name: attr.string_value
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


def reconstruct_doc(
    root: PyXdmNode,
    start_xpath: List[str],
    new_tree: Optional[Element] = None,
    end_xpath: Optional[List[str]] = None
) -> Element:
    """ Loop over passages to construct and increment new tree given a parent and XPaths

    :param root: Parent on which to perform xpath
    :param new_tree: Parent on which to add nodes
    :param start_xpath: List of xpath elements
    :type start_xpath: [str]
    :param end_xpath: List of xpath elements
    :type end_xpath: [str]
    :return: Newly incremented tree
    """
    current_start, queue_start = xpath_walk(start_xpath)
    xproc = get_xpath_proc(root)
    # There are too possibilities:
    #  1. What we call loop is when the first element that match this XPath, such as "//body", then we will need
    #     to loop over ./TEI, then ./text and finally we'll get out of the loop at body.
    #     Basically, in a loop, the XPath does not change until we reach the first element
    #     of the XPath (here ./body)
    #  2. The second option is that we do not loop. Simple he ?
    result_start, start_is_traversing = xpath_walk_step(root, current_start)
    current_end, queue_end = None, None
    if start_is_traversing is True:
        queue_start = start_xpath
        # If we loop and both xpath are the same,
        #    then we have the same current and queue
        if end_xpath == start_xpath:
            current_end, queue_end = current_start, queue_start

    # If we were not in any single edge case for end_xpath, run the xpath_walk
    if current_end is None:
        current_end, queue_end = xpath_walk(end_xpath)

    # Here, we start by comparing both XPath, in case we have a single XPath
    current_1_is_current_2 = start_xpath == end_xpath
    # If they don't match, maybe an XPath comparison of both items will tell use more
    if not current_1_is_current_2:
        # If we don't, we do an XPath check
        current_1_is_current_2 = xproc.effective_boolean_value(f"head({current_start}) is head({current_end})")
    if current_1_is_current_2:
        # We get the children if the XPath stops here
        # We copy the node we found
        copied_node = copy_node(result_start, include_children=len(queue_start) == 0, parent=new_tree)
        # If that's the first element EVER, then we make this child the root node of our new tree
        if new_tree is None:
            new_tree = copied_node
        # Given that both XPath returns the same node, we still need to check if end is looping
        #   We optimize by avoiding this check when start and end are the same
        if start_xpath != end_xpath and is_traversing_xpath(root, current_end):
            queue_end = end_xpath
        # If we have a child XPath, then continue the job
        if len(queue_start):
            reconstruct_doc(root=result_start, new_tree=copied_node, start_xpath=queue_start, end_xpath=queue_end)
    else:
        # If we still don't have the same children as a result of start and end,
        #   We make sure to retrieve the element at the end of 2
        result_end, end_is_traversing = xpath_walk_step(root, current_end)
        # If end_xpath results in a loop, then loop end_xpath
        if end_is_traversing:
            queue_end = end_xpath

        # We start by copying start.
        copy_node(result_start, include_children=len(queue_start) == 0, parent=new_tree)
        # If we have a queue, we run the queue
        if queue_start:
            reconstruct_doc(result_start, start_xpath=queue_start, end_xpath=queue_start)

        # When we don't have similar node, we loop on siblings until we get to the expected element
        #  For this reason, we need to change matching xpath (ie. ./div[position()=1]) into compatible
        #  suffixes with preceding-sibling or following-sibling.
        # We do that for start and end
        if start_is_traversing and current_start.startswith(".//"):
            sib_current_start = f"*[{current_start}]"
        elif not start_is_traversing and current_start.startswith(".//"):
            sib_current_start = current_start[3:]
        else:
            sib_current_start = current_start[2:]
        if end_is_traversing and current_end.startswith(".//"):
            sib_current_end = f"*[{current_end}]"
        elif not end_is_traversing and current_end.startswith(".//"):
            sib_current_end = current_end[3:]
        else:
            sib_current_end = current_end[2:]

        # We look for siblings between start and end matches
        xpath = get_xpath_proc(root)

        for sibling in xpath.evaluate(
                f"./*[preceding-sibling::{sib_current_start} and following-sibling::{sib_current_end}]"):
            copy_node(sibling, include_children=True, parent=new_tree)

        # Here we reached the end, logically.
        node = copy_node(node=result_end, include_children=len(queue_end) == 0, parent=new_tree)
        if queue_end:
            reconstruct_doc(
                root=result_end, new_tree=node, start_xpath=queue_end, end_xpath=queue_end)

    return new_tree


class Document:
    def __init__(self, file_path: str):
        self.xml = PROCESSOR.parse_xml(xml_file_name=file_path)
        self.xpath_processor = get_xpath_proc(elem=self.xml)
        self.citeStructure: Dict[Optional[str], CiteStructureParser] = {}
        for refsDecl in self.xpath_processor.evaluate("/TEI/teiHeader/refsDecl[./citeStructure]"):
            struct = CiteStructureParser(refsDecl)

            self.citeStructure[refsDecl.get_attribute_value("n")] = struct

            if refsDecl.get_attribute_value("default") == "true":
                self.citeStructure[None] = struct

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

        try:
            start = self.citeStructure[tree].generate_xpath(start)
        except KeyError:
            raise UnknownTreeName(tree)

        def xpath_split(string: str) -> List[str]:
            return [x for x in re.split(r"/(/?[^/]+)", string) if x]

        start = normalize_xpath(xpath_split(start))
        if end:
            end = self.citeStructure[tree].generate_xpath(end)
            end = normalize_xpath(xpath_split(end))
        else:
            end = start

        root = reconstruct_doc(
            self.xml,
            new_tree=None,
            start_xpath=start,
            end_xpath=end
        )
        objectify.deannotate(root, cleanup_namespaces=True)
        return root
