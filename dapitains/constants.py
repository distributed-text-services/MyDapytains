try:
    from saxonche import PySaxonProcessor, PyXdmNode, PyXPathProcessor
except ImportError:
    print("PySaxonC-HE not found")

PROCESSOR = PySaxonProcessor()


def get_xpath_proc(elem: PyXdmNode) -> PyXPathProcessor:
    """ Builds an XPath processor around a given element, with the default TEI namespace

    :param elem: An XML node, root or not
    :return: XPathProccesor
    """
    xpath = PROCESSOR.new_xpath_processor()
    xpath.declare_namespace("", "http://www.tei-c.org/ns/1.0")
    xpath.set_context(xdm_item=elem)
    return xpath
