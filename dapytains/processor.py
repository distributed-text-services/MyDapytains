import logging
import os
from typing import Optional
saxon_version = os.getenv("pysaxon", "HE")
saxon_license = os.getenv("pysaxon_license", "")
logging.info(f"Using SaxonLib {saxon_version}")
try:
    if saxon_version == "PE":
        import saxoncpe as saxonlib
    elif saxon_version == "PE":
        import saxoncee as saxonlib
    else:
        import saxonche as saxonlib
except ImportError:
    logging.error("Unable to import the required PySaxonC version, resorting to PySaxonC-HE")
    import saxonche as saxonlib

def get_processor() -> saxonlib.PySaxonProcessor:
    if saxon_version == "PE":
        return saxonlib.PySaxonProcessor(license=saxon_license)
    elif saxon_version == "PE":
        return saxonlib.PySaxonProcessor(license=saxon_license)
    else:
        return saxonlib.PySaxonProcessor()


def get_xpath_proc(elem: saxonlib.PyXdmNode, processor: saxonlib.PySaxonProcessor) -> saxonlib.PyXPathProcessor:
    """ Builds an XPath processor around a given element, with the default TEI namespace

    :param elem: An XML node, root or not
    :return: XPathProccesor
    """
    xpath = processor.new_xpath_processor()
    xpath.declare_namespace("", "http://www.tei-c.org/ns/1.0")
    xpath.set_context(xdm_item=elem)
    return xpath
