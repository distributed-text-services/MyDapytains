import logging
import os

try:
    saxon_version = os.getenv("pysaxon", "HE")
    saxon_license = os.getenv("pysaxon_license", "")
    logging.info(f"Using SaxonLib {saxon_version}")
    if saxon_version == "HE":
        import saxonche as saxonlib
        PROCESSOR = saxonlib.PySaxonProcessor()
    elif saxon_version == "PE":
        import saxoncpe as saxonlib
        PROCESSOR = saxonlib.PySaxonProcessor(license=saxon_license)
    elif saxon_version == "PE":
        import saxoncee as saxonlib
        PROCESSOR = saxonlib.PySaxonProcessor(license=saxon_license)
except ImportError:
    print("Unable to import the required PySaxonC version, resorting to PySaxonC-HE")
    import saxonche as saxonlib
    PROCESSOR = saxonlib.PySaxonProcessor()

PROCESSOR.set_configuration_property("indent-space", "0")




def get_xpath_proc(elem: saxonlib.PyXdmNode) -> saxonlib.PyXPathProcessor:
    """ Builds an XPath processor around a given element, with the default TEI namespace

    :param elem: An XML node, root or not
    :return: XPathProccesor
    """
    xpath = PROCESSOR.new_xpath_processor()
    xpath.declare_namespace("", "http://www.tei-c.org/ns/1.0")
    xpath.set_context(xdm_item=elem)
    return xpath
