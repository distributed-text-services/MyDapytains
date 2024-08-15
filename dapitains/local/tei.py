from dapitains.local.citeStructure import CiteStructureParser
from dapitains.constants import PROCESSOR, get_xpath_proc
from typing import Optional, List, Tuple
from lxml.etree import tostring, fromstring
from lxml.objectify import Element, SubElement, ObjectifiedElement
from saxonche import PyXdmNode, PyXPathProcessor
import re


_namespace = re.compile(r"Q{(?P<namespace>[^}]+)}(?P<tagname>.+)")


def xpath_walk(xpath: List[str]) -> Tuple[str, List[str]]:
    """ Format at XPath for perform XPath

    ToDo: Not finished reprocessed

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
    if xpath.startswith(".//"):
        # If the XPath starts with .//, we try to see if we have a direct child that matches
        if result := xpath_proc.evaluate_single(xpath.replace(".//", "./", 1)):
            return result, False
        # Otherwise, we check for any child element having such a child
        else:
            return xpath_proc.evaluate_single(f"./*[{xpath}]"), True
    else:
        return xpath_proc.evaluate_single(xpath), False


def copy_node(node: PyXdmNode, children=False, parent: Optional[Element] = None):
    """ Copy an XML Node

    :param node: Etree Node
    :param children: Copy children nodes if set to True
    :param parent: Append copied node to parent if given
    :return: New Element
    """
    if children:
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
    end_xpath: Optional[List[str]] = None,
    preceding_siblings: bool = False,
    following_siblings: bool = False
):
    """ Loop over passages to construct and increment new tree given a parent and XPaths

    :param root: Parent on which to perform xpath
    :param new_tree: Parent on which to add nodes
    :param start_xpath: List of xpath elements
    :type start_xpath: [str]
    :param end_xpath: List of xpath elements
    :type end_xpath: [str]
    :param preceding_siblings: Append preceding siblings of XPath 1/2 match to the tree
    :param following_siblings: Append following siblings of XPath 1/2 match to the tree
    :return: Newly incremented tree
    """
    current_1, queue_1 = xpath_walk(start_xpath)
    if end_xpath is None:  # In case we need what is following or preceding our node
        result_1, loop = xpath_walk_step(root, current_1)
        if loop is True:
            queue_1 = start_xpath

        central = None
        has_no_queue = len(queue_1) == 0
        # For each sibling, when we need them in the context of a range
        if preceding_siblings or following_siblings:
            for sibling in xmliter(root):
                if sibling == result_1:
                    central = True
                    # We copy the node we looked for (Result_1)
                    child = copy_node(result_1, children=has_no_queue, parent=new_tree)
                    # if we don't have children
                    # we loop over the passage child
                    if not has_no_queue:
                        reconstruct_doc(
                            result_1,
                            new_tree=child,
                            start_xpath=queue_1,
                            end_xpath=None,
                            preceding_siblings=preceding_siblings,
                            following_siblings=following_siblings
                        )
                    # If we were waiting for preceding_siblings, we break it off
                    # As we don't need to go further
                    if preceding_siblings:
                        break
                elif not central and preceding_siblings:
                    copy_node(sibling, parent=new_tree, children=True)
                elif central and following_siblings:
                    copy_node(sibling, parent=new_tree, children=True)
    else:
        result_1, loop = xpath_walk_step(root, current_1)
        if loop is True:
            queue_1 = start_xpath
            if end_xpath == start_xpath:
                current_2, queue_2 = current_1, queue_1
            else:
                current_2, queue_2 = xpath_walk(end_xpath)
        else:
            current_2, queue_2 = xpath_walk(end_xpath)

        if current_1 != current_2:
            result_2, loop = xpath_walk_step(root, current_2)
            if loop is True:
                queue_2 = end_xpath
        else:
            result_2 = result_1

        if result_1 is result_2:
            # We get the children if the XPath stops here
            has_no_queue = len(queue_1) == 0

            # We copy the node we found
            child = copy_node(result_1, children=has_no_queue, parent=new_tree)

            if new_tree is None:
                new_tree = child
            if not has_no_queue:
                reconstruct_doc(
                    root=result_1,
                    new_tree=child,
                    start_xpath=queue_1,
                    end_xpath=queue_2
                )
        else:
            start = False
            # For each sibling
            for sibling in xmliter(root):
                # If we have found start
                # We copy the node because we are between start and end
                if start:
                    # If we are at the end
                    # We break the copy
                    if sibling == result_2:
                        break
                    else:
                        copy_node(sibling, parent=new_tree, children=True)
                # If this is start
                # Then we copy it and initiate star
                elif sibling == result_1:
                    start = True
                    has_no_queue_1 = len(queue_1) == 0
                    node = copy_node(sibling, children=has_no_queue_1, parent=new_tree)
                    if not has_no_queue_1:
                        reconstruct_doc(
                            root=sibling,
                            new_tree=node,
                            start_xpath=queue_1,
                            end_xpath=None,
                            following_siblings=True
                        )

            continue_loop = len(queue_2) == 0
            node = copy_node(result_2, children=continue_loop, parent=new_tree)
            if not continue_loop:
                reconstruct_doc(
                    root=result_2, new_tree=node, start_xpath=queue_2, end_xpath=None, preceding_siblings=True)

    return new_tree


class Document:
    def __init__(self, file_path: str):
        self.xml = PROCESSOR.parse_xml(xml_file_name=file_path)
        self.xpath_processor = get_xpath_proc(elem=self.xml)
        self.citeStructure = CiteStructureParser(
            self.xpath_processor.evaluate_single("/TEI/teiHeader/refsDecl/citeStructure")
        )

    def get_passage(self, ref: Optional[str], start: Optional[str] = None, end: Optional[str] = None):
        """

        :param ref:
        :param start:
        :param end:
        :return:
        """
        if ref:
            start, end = ref, None
        elif not start or not end:
            raise ValueError("Start/End or Ref are necessary to get a passage")

        start = self.citeStructure.generate_xpath(start)
        def xpath_split(string: str) -> List[str]:
            return [x for x in re.split(r"/(/?[^/]+)", string) if x]

        start = normalize_xpath(xpath_split(start))
        if end:
            end = self.citeStructure.generate_xpath(end)
            end = normalize_xpath(end.split("/"))
        else:
            end = start

        root = reconstruct_doc(
            self.xml,
            new_tree=None,
            start_xpath=start,
            end_xpath=end
        )
        return root


if __name__ == "__main__":
    doc = Document("/home/tclerice/dev/MyDapytains/tests/base_tei.xml")

    assert tostring(
        doc.get_passage("Luke 1:1"), encoding=str
    ) == ('<TEI xmlns="http://www.tei-c.org/ns/1.0" xmlns:py="http://codespeak.net/lxml/objectify/pytype"><text><body>'
          '<div n="Luke"><div><div>Text</div></div></div></body></text></TEI>')

