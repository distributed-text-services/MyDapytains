import os.path

import pytest

from dapytains.errors import UnresolvableReference
from dapytains.processor import get_processor, get_xpath_proc
from dapytains.tei.document import Document

p = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def doc():
    # Column 1 comes back twice: letter B only exists under its later occurrences.
    return Document(os.path.join(p, "tei/cb_repeated_column.xml"))


def test_resolvable_reference_still_works(doc):
    assert doc.citeStructure[doc.default_tree].generate_xpath("1.A") == "/TEI[1]/text[1]/body[1]/div[1]/p[1]/milestone[1]"
    assert doc.citeStructure[doc.default_tree].generate_xpath("2.A") == "/TEI[1]/text[1]/body[1]/div[1]/p[2]/milestone[1]"


def test_child_of_a_later_occurrence_raises(doc):
    """ Used to hand None to Saxon as an XPath context, which segfaulted. """
    with pytest.raises(UnresolvableReference) as error:
        doc.citeStructure[doc.default_tree].generate_xpath("1.B")
    assert error.value.reference == "1.B"


def test_missing_parent_raises_instead_of_matching_elsewhere(doc):
    """ There is no column 9: "9.A" used to resolve to the first letter A of the document. """
    assert doc.citeStructure[doc.default_tree].resolve_node("9.A") is None
    with pytest.raises(UnresolvableReference):
        doc.citeStructure[doc.default_tree].generate_xpath("9.A")


def test_get_passage_raises(doc):
    with pytest.raises(UnresolvableReference):
        doc.get_passage("1.B")
    with pytest.raises(UnresolvableReference):
        doc.get_passage("9.A")


def test_unresolvable_reference_is_a_value_error():
    """ Callers catching ValueError (e.g. malformed references) keep working. """
    assert issubclass(UnresolvableReference, ValueError)


def test_get_xpath_proc_refuses_none():
    with pytest.raises(TypeError):
        get_xpath_proc(None, processor=get_processor())
