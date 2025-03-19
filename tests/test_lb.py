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
        start_siblings="lb[@n='2']//following-sibling::node()[following-sibling::lb[@n='3']]",
    )
    assert _to_string(x) == """<TEI xmlns="http://www.tei-c.org/ns/1.0"><text>
<body>
<div xml:lang="grc" type="edition" xml:space="preserve">
<ab>
<lb n="2"/>Καίσαρος <unclear>Ο</unclear><supplied reason="lost">ὐεσ</supplied>πασιανοῦ <expan><unclear>Σεβα</unclear><ex>στοῦ</ex></expan>
</ab>
</div>
</body>
</text>
</TEI>"""
    assert _to_string(x) == _to_string(doc.get_passage("2"))


def test_simple_range_lb():
    doc = Document(os.path.join(p, "tei/lb_same_ab.xml"))
    {'new_tree': None, 'start_xpath': ['/body', 'div', "/lb[@n='2']"], 'end_xpath': ['/body', 'div', "/lb[@n='4']"],
     'start_siblings': None,
     'end_siblings': "lb[@n='4']/following-sibling::node()[following-sibling::lb[@n='5'] or following-sibling::*[.//lb[@n='5']]]"}
    x = reconstruct_doc(
        doc.xml,
        start_xpath=normalize_xpath(xpath_split("/TEI/text/body/div/ab/lb[@n='2']")),
        end_xpath=normalize_xpath(xpath_split("/TEI/text/body/div/ab/lb[@n='4']")),
        end_siblings="/TEI/text/body/div/ab/lb[@n='4']//following-sibling::node()[following-sibling::lb[@n='5']]"
    )
    assert _to_string(x) == """<TEI xmlns="http://www.tei-c.org/ns/1.0"><text>
<body>
<div xml:lang="grc" type="edition" xml:space="preserve">
<ab>
<lb n="2"/>Καίσαρος <unclear>Ο</unclear><supplied reason="lost">ὐεσ</supplied>πασιανοῦ <expan><unclear>Σεβα</unclear><ex>στοῦ</ex></expan>
<lb n="3"/>τύχην ταῖς ἀληθείαις οὕτως
<lb n="4"/>ἔχειν.  εὐορκοῦντι μέν μοι
</ab>
</div>
</body>
</text>
</TEI>"""
    assert _to_string(x) == _to_string(doc.get_passage("2", "4"))



def test_overlapping_range_lb():
    doc = Document(os.path.join(p, "tei/lb_diff_ab.xml"))
    x = reconstruct_doc(
        doc.xml,
        start_xpath=normalize_xpath(xpath_split("/TEI/text/body/div/ab/lb[@n='2']")),
        end_xpath=normalize_xpath(xpath_split("/TEI/text/body/div/ab/lb[@n='4']")),
        end_siblings="/TEI/text/body/div/ab/lb[@n='4']//following-sibling::node()[following-sibling::lb[@n='5']]"
    )
    assert _to_string(x) == """<TEI xmlns="http://www.tei-c.org/ns/1.0"><text>
<body>
<div xml:lang="grc" type="edition" xml:space="preserve">
<ab>
<lb n="2"/>Καίσαρος <unclear>Ο</unclear><supplied reason="lost">ὐεσ</supplied>πασιανοῦ <expan><unclear>Σεβα</unclear><ex>στοῦ</ex></expan>
<lb n="3"/>τύχην ταῖς ἀληθείαις οὕτως
</ab>
<ab>
<lb n="4"/>ἔχειν.  εὐορκοῦντι μέν μοι
</ab>
</div>
</body>
</text>
</TEI>"""
    assert _to_string(x) == _to_string(doc.get_passage("2", "4"))


if __name__ == "__main__":
    doc = Document(os.path.join(p, "tei/lb_diff_ab.xml"))
    x = reconstruct_doc(
        doc.xml,
        start_xpath=normalize_xpath(xpath_split("/TEI/text/body/div/ab/lb[@n='2']")),
        end_xpath=normalize_xpath(xpath_split("/TEI/text/body/div/ab/lb[@n='4']")),
        end_siblings="/TEI/text/body/div/ab/lb[@n='4']//following-sibling::node()[following-sibling::lb[@n='5']]"
    )