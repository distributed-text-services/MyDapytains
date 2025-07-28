import os.path
import lxml.etree as et
from lxml import objectify
from dapytains.tei.document import Document, reconstruct_doc,  normalize_xpath, xpath_split
from dapytains.processor import get_processor

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
        start_siblings="lb[@n='3']",
        processor=doc.xml_processor
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
    x = reconstruct_doc(
        doc.xml,
        start_xpath=normalize_xpath(xpath_split("/TEI/text/body/div/ab/lb[@n='2']")),
        end_xpath=normalize_xpath(xpath_split("/TEI/text/body/div/ab/lb[@n='4']")),
        end_siblings="lb[@n='5']",
        processor=doc.xml_processor
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
        end_siblings="lb[@n='5']",
        processor=doc.xml_processor
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


def test_overlapping_range_lb_simulate_double_slash():
    doc = Document(os.path.join(p, "tei/lb_diff_ab.xml"))
    doc.citeStructure["default"].structure.xpath = doc.citeStructure["default"].structure.xpath.replace("ab/", "/")
    doc.citeStructure["default"].structure.xpath_match = doc.citeStructure["default"].structure.xpath_match.replace("ab/", "/")
    x = reconstruct_doc(
        doc.xml,
        start_xpath=normalize_xpath(xpath_split("/TEI/text/body/div/ab/lb[@n='2']")),
        end_xpath=normalize_xpath(xpath_split("/TEI/text/body/div/ab/lb[@n='4']")),
        end_siblings="lb[@n='5']",
        processor=doc.xml_processor
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


def test_overlapping_single_uneven_lb_at_the_start():
    doc = Document(os.path.join(p, "tei/lb_uneven_ab.xml"))
    x = reconstruct_doc(
        doc.xml,
        start_xpath=normalize_xpath(xpath_split("/TEI/text/body/div/ab//lb[@n='2']")),
        end_xpath=normalize_xpath(xpath_split("/TEI/text/body/div/ab//lb[@n='2']")),
        start_siblings="lb[@n='3']",
        processor=doc.xml_processor
    )
    assert _to_string(x) == """<TEI xmlns="http://www.tei-c.org/ns/1.0"><text>
<body>
<div xml:lang="grc" type="edition" xml:space="preserve">
<ab>
<w><lb n="2"/>Καίσαρος</w> <unclear>Ο</unclear><supplied reason="lost">ὐεσ</supplied>πασιανοῦ <expan><unclear>Σεβα</unclear><ex>στοῦ</ex></expan>
</ab>
</div>
</body>
</text>
</TEI>"""
    assert _to_string(x) == _to_string(doc.get_passage("2"))


def test_overlapping_single_uneven_lb_at_the_end():
    doc = Document(os.path.join(p, "tei/lb_uneven_ab.xml"))
    x = reconstruct_doc(
        doc.xml,
        start_xpath=normalize_xpath(xpath_split("/TEI/text/body/div/ab//lb[@n='1']")),
        end_xpath=normalize_xpath(xpath_split("/TEI/text/body/div/ab//lb[@n='1']")),
        start_siblings="lb[@n='2']",
        processor=doc.xml_processor
    )
    assert _to_string(x) == """<TEI xmlns="http://www.tei-c.org/ns/1.0"><text>
<body>
<div xml:lang="grc" type="edition" xml:space="preserve">
<ab>
<lb n="1"/><gap reason="lost" extent="unknown" unit="line"/><w>end of line 1
</w> </ab>
</div>
</body>
</text>
</TEI>"""
    assert _to_string(x) == _to_string(doc.get_passage("1"))


def test_overlapping_single_uneven_lb_range():
    doc = Document(os.path.join(p, "tei/lb_uneven_ab.xml"))
    x = reconstruct_doc(
        doc.xml,
        start_xpath=normalize_xpath(xpath_split("/TEI/text/body/div/ab//lb[@n='2']")),
        end_xpath=normalize_xpath(xpath_split("/TEI/text/body/div/ab//lb[@n='5']")),
        end_siblings="lb[@n='6']",
        processor=doc.xml_processor
    )
    assert _to_string(x) == """<TEI xmlns="http://www.tei-c.org/ns/1.0"><text>
<body>
<div xml:lang="grc" type="edition" xml:space="preserve">
<ab>
<w><lb n="2"/>Καίσαρος</w> <unclear>Ο</unclear><supplied reason="lost">ὐεσ</supplied>πασιανοῦ <expan><unclear>Σεβα</unclear><ex>στοῦ</ex></expan>
<lb n="3"/>τύχην ταῖς ἀληθείαις οὕτως
</ab>
<ab>
<lb n="4"/>ἔχειν.  εὐορκοῦντι μέν μοι
</ab>
<ab>
<lb n="5"/>εὖ εἴη, ἐφιορκοῦντι δὲ τὰ ἐναντία. <w>b
</w></ab>
</div>
</body>
</text>
</TEI>"""
    assert _to_string(x) == _to_string(doc.get_passage("2", "5"))


def test_double_matching_lb_as_ref():
    doc = Document(os.path.join(p, "tei/double_tree_lb.xml"))
    assert normalize_xpath(xpath_split("/TEI/text/body/div[@type='edition']//lb[@n='1']")
                           ) == ['TEI', 'text', 'body', "div[@type='edition']", "/lb[@n='1']"]
    x = reconstruct_doc(
        doc.xml,
        start_xpath=normalize_xpath(xpath_split("/TEI/text/body/div[@type='edition']//lb[@n='1']")),
        end_xpath=normalize_xpath(xpath_split("/TEI/text/body/div[@type='edition']//lb[@n='1']")),
        start_siblings="lb[@n='2']",
        processor=doc.xml_processor
    )
    assert _to_string(x) == """<TEI xmlns="http://www.tei-c.org/ns/1.0"><text>
        <body>
            <div type="edition">
                <ab>
                    <lb n="1"/>Ἰουλίας ΒαλΛίλλης· </ab>
                </div>
            </body>
    </text>
</TEI>"""
    assert _to_string(x) == _to_string(doc.get_passage("1", tree="default"))

def test_double_matching_lb_as_range():
    doc = Document(os.path.join(p, "tei/double_tree_lb.xml"))
    x = reconstruct_doc(
        doc.xml,
        start_xpath=normalize_xpath(xpath_split("/TEI/text/body/div[@type='edition']//lb[@n='2']")),
        end_xpath=normalize_xpath(xpath_split("/TEI/text/body/div[@type='edition']//lb[@n='5']")),
        end_siblings="lb[@n='6']",
        processor=doc.xml_processor
    )
    assert _to_string(x) == """<TEI xmlns="http://www.tei-c.org/ns/1.0"><text>
        <body>
            <div type="edition">
                <ab>
                    <lb n="2"/>ὅτε ἤκουσε τοῦ Μέμνος <lb n="3"/>ὁ
                    Σεβαστὸς Ἁδριανός. </ab>
                <lg>
                    <l n="1">
                        <lb n="4"/>Μέμνονα πυνθανόμαν Αἰγύπτιον, ἀλίω αὔγαι</l>
                    <l n="2">
                        <lb n="5"/>αἰθόμενον, φώνην ΘηβαΐΧω ’πυ λίθω.</l>
                    <l n="3">
                        </l>
                    </lg>
            </div>
            </body>
    </text>
</TEI>"""
    assert _to_string(x) == _to_string(doc.get_passage("2", '5', tree="default"))


def test_long_files_even():
    processor = get_processor()
    document_builder = processor.new_document_builder()
    xdm_node = document_builder.parse_xml(xml_text=f"""<TEI xmlns="http://www.tei-c.org/ns/1.0"><teiHeader>
     <encodingDesc>
        <refsDecl default="true" n="default">
           <citeStructure match="/TEI/text/body//lb" use="@n" unit="line"/>
        </refsDecl>
     </encodingDesc></teiHeader><text><body>
{' '.join(['<lb n="' + str(i) + '"/>'  for i in range(10000)])}
</body>
</text>
</TEI>""")
    x = reconstruct_doc(
        xdm_node,
        start_xpath=normalize_xpath(xpath_split("/TEI/text/body//lb[@n='400']")),
        end_xpath=normalize_xpath(xpath_split("/TEI/text/body//lb[@n='499']")),
        end_siblings="lb[@n='500']",
        processor=processor
    )
    assert _to_string(x) == f"""<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
{' '.join(['<lb n="' + str(i) + '"/>'  for i in range(400, 500)])} </body>
</text>
</TEI>"""

def test_long_files_uneven():
    processor = get_processor()
    document_builder = processor.new_document_builder()
    xdm_node = document_builder.parse_xml(xml_text=f"""<TEI xmlns="http://www.tei-c.org/ns/1.0"><teiHeader>
     <encodingDesc>
        <refsDecl default="true" n="default">
           <citeStructure match="/TEI/text/body//lb" use="@n" unit="line"/>
        </refsDecl>
     </encodingDesc></teiHeader><text><body>
{' '.join(['<lb n="' + str(i) + '"/>' if i != 500 else '<a>b<lb n="'+str(i)+'" /></a>' for i in range(10000)])}
</body>
</text>
</TEI>""")
    x = reconstruct_doc(
        xdm_node,
        start_xpath=normalize_xpath(xpath_split("/TEI/text/body//lb[@n='400']")),
        end_xpath=normalize_xpath(xpath_split("/TEI/text/body//lb[@n='499']")),
        end_siblings="lb[@n='500']",
        processor=processor
    )
    assert _to_string(x) == f"""<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
{' '.join(['<lb n="' + str(i) + '"/>' if i != 499 else '<lb n="' + str(i) + '"/> <a>b</a>' for i in range(400, 500)])} </body>
</text>
</TEI>"""