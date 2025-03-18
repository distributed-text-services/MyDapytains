import os.path
import lxml.etree as et
from lxml import objectify
from dapitains.tei.document import Document, reconstruct_doc,  normalize_xpath, xpath_split

p = os.path.dirname(os.path.abspath(__file__))


def _to_string(x: et.ElementBase) -> str:
    objectify.deannotate(x, cleanup_namespaces=True)
    return et.tostring(x, encoding=str)


def test_simple_single_lb():
    doc = Document(os.path.join(p, "tei/lb_same_ab.xml"))
    x = reconstruct_doc(
        doc.xml,
        start_xpath=normalize_xpath(xpath_split("/TEI/text/body/div/ab/lb[@n='2']")),
        end_xpath=normalize_xpath(xpath_split("/TEI/text/body/div/ab/lb[@n='2']")),
        # end_xpath=normalize_xpath(xpath_split("/TEI/text/body/div/ab/lb[@n='4']")),
        start_siblings="lb[@n='2']//following-sibling::node()[following-sibling::lb[@n='3']]",
        # end_siblings="/TEI/text/body/div/ab/lb[@n='4']//following-sibling::node()[following-sibling::lb[@n='5']]"
    )
    assert _to_string(x) == """<TEI xmlns="http://www.tei-c.org/ns/1.0"><text>
<body>
<div xml:lang="grc" type="edition" xml:space="preserve">
<ab>
<lb n="2"/>Καίσαρος <unclear>Ο</unclear><supplied reason="lost">ὐεσ</supplied>πασιανοῦ <expan><unclear>Σεβα</unclear><ex>στοῦ</ex></expan></ab></div></body></text></TEI>"""

def test_simple_range_lb():
    doc = Document(os.path.join(p, "tei/lb_same_ab.xml"))
    x = reconstruct_doc(
        doc.xml,
        start_xpath=normalize_xpath(xpath_split("/TEI/text/body/div/ab/lb[@n='2']")),
        end_xpath=normalize_xpath(xpath_split("/TEI/text/body/div/ab/lb[@n='4']")),
        # end_xpath=normalize_xpath(xpath_split("/TEI/text/body/div/ab/lb[@n='4']")),
        # start_siblings="lb[@n='2']//following-sibling::node()[following-sibling::lb[@n='3']]",
        end_siblings="/TEI/text/body/div/ab/lb[@n='4']//following-sibling::node()[following-sibling::lb[@n='5']]"
    )
    assert _to_string(x) == """<TEI xmlns="http://www.tei-c.org/ns/1.0"><text>
<body>
<div xml:lang="grc" type="edition" xml:space="preserve">
<ab>
<lb n="2"/>Καίσαρος <unclear>Ο</unclear><supplied reason="lost">ὐεσ</supplied>πασιανοῦ <expan><unclear>Σεβα</unclear><ex>στοῦ</ex></expan>
<lb n="3"/>τύχην ταῖς ἀληθείαις οὕτως
<lb n="4"/>ἔχειν.  εὐορκοῦντι μέν μοι
</ab></div></body></text></TEI>"""


def test_overlapping_range_lb():
    doc = Document(os.path.join(p, "tei/lb_diff_ab.xml"))
    x = reconstruct_doc(
        doc.xml,
        start_xpath=normalize_xpath(xpath_split("/TEI/text/body/div/ab/lb[@n='2']")),
        end_xpath=normalize_xpath(xpath_split("/TEI/text/body/div/ab/lb[@n='4']")),
        # end_xpath=normalize_xpath(xpath_split("/TEI/text/body/div/ab/lb[@n='4']")),
        # start_siblings="lb[@n='2']//following-sibling::node()[following-sibling::lb[@n='3']]",
        # start_siblings="/TEI/text/body/div/ab/lb[@n='2']//following-sibling::node()[following-sibling::lb[@n='5']]",
        end_siblings="/TEI/text/body/div/ab/lb[@n='4']//following-sibling::node()[following-sibling::lb[@n='5']]"
    )
    print(_to_string(x))
    assert _to_string(x) == """<TEI xmlns="http://www.tei-c.org/ns/1.0"><text>
<body>
<div xml:lang="grc" type="edition" xml:space="preserve">
<ab>
<lb n="2"/>Καίσαρος <unclear>Ο</unclear><supplied reason="lost">ὐεσ</supplied>πασιανοῦ <expan><unclear>Σεβα</unclear><ex>στοῦ</ex></expan>
<lb n="3"/>τύχην ταῖς ἀληθείαις οὕτως
</ab><ab>
<lb n="4"/>ἔχειν.  εὐορκοῦντι μέν μοι
</ab></div></body></text></TEI>"""


if __name__ == "__main__":
    doc = Document(os.path.join(p, "tei/lb_diff_ab.xml"))
    x = reconstruct_doc(
        doc.xml,
        start_xpath=normalize_xpath(xpath_split("/TEI/text/body/div/ab/lb[@n='2']")),
        end_xpath=normalize_xpath(xpath_split("/TEI/text/body/div/ab/lb[@n='4']")),
        # end_xpath=normalize_xpath(xpath_split("/TEI/text/body/div/ab/lb[@n='4']")),
        # start_siblings="lb[@n='2']//following-sibling::node()[following-sibling::lb[@n='3']]",
        # start_siblings="/TEI/text/body/div/ab/lb[@n='2']//following-sibling::node()[following-sibling::lb[@n='5']]",
        end_siblings="/TEI/text/body/div/ab/lb[@n='4']//following-sibling::node()[following-sibling::lb[@n='5']]"
    )
    print(_to_string(x))