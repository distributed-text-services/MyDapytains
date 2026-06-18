import os.path

import pytest

from dapytains.tei.citeStructure import CitableUnit
from dapytains.tei.document import Document
from lxml.etree import tostring

local_dir = os.path.join(os.path.dirname(__file__), "tei")


def test_single_passage():
    """Test that a single passage matching works"""
    doc = Document(f"{local_dir}/base_tei.xml")
    assert tostring(
        doc.get_passage("Luke 1:1"), encoding=str
    ) == ('<TEI xmlns="http://www.tei-c.org/ns/1.0"><text>\n'
 '    <body>\n'
 '    <div n="Luke">\n'
 '        <div>\n'
 '            <div>Text</div>\n'
 '            </div>\n'
 '    </div>\n'
 '    </body>\n'
 '    </text>\n'
 '</TEI>')


def test_simple_range():
    """Test that a range with two different xpath work"""
    doc = Document(f"{local_dir}/base_tei.xml")
    assert tostring(
        doc.get_passage(ref_or_start="Luke 1:1", end="Luke 1#1"), encoding=str
    ) == ('<TEI xmlns="http://www.tei-c.org/ns/1.0"><text>\n'
 '    <body>\n'
 '    <div n="Luke">\n'
 '        <div>\n'
 '            <div>Text</div>\n'
 '            <div>Text 2</div>\n'
 '            <l>Text 3</l>\n'
 '        </div>\n'
 '    </div>\n'
 '    </body>\n'
 '    </text>\n'
 '</TEI>')


def test_different_level_range():
    """Test that a range with two different xpath and two different level work"""
    doc = Document(f"{local_dir}/tei_with_two_traversing_with_n.xml")
    assert tostring(
        doc.get_passage(ref_or_start="Luke 1:1", end="Luke 1#3"), encoding=str
    ) == ('<TEI xmlns="http://www.tei-c.org/ns/1.0"><text>\n'
     '    <body>\n'
     '    <div n="Luke">\n'
     '        <div n="1">\n'
     '            <div n="1">Text</div>\n'
     '            <div n="2">Text 2</div>\n'
     '            <lg>\n'
     '                <l n="1">Text 3</l>\n'
     '                <l n="2">Text 4</l>\n'
     '            </lg>\n'
     '            <l n="3">Text 5</l>\n'
     '        </div>\n'
     '    </div>\n'
     '    </body>\n'
     '    </text>\n'
     '</TEI>')

    assert tostring(
        doc.get_passage(ref_or_start="Luke 1:1", end="Luke 1#1"), encoding=str
    ) == ('<TEI xmlns="http://www.tei-c.org/ns/1.0"><text>\n'
 '    <body>\n'
 '    <div n="Luke">\n'
 '        <div n="1">\n'
 '            <div n="1">Text</div>\n'
 '            <div n="2">Text 2</div>\n'
 '            <lg>\n'
 '                <l n="1">Text 3</l>\n'
 '                </lg>\n'
 '            </div>\n'
 '    </div>\n'
 '    </body>\n'
 '    </text>\n'
 '</TEI>')


def test_different_level_range_fails_on_position():
    doc = Document(f"{local_dir}/tei_with_two_traversing.xml")
    # This should fail, because //something[position()=3] does not go from one element to another. Yet another
    #   reason to NOT use it.
    with pytest.raises(TypeError):
        print(doc.get_passage(ref_or_start="Luke 1:1", end="Luke 1#3"))


def test_multiple_trees():
    """Check that having multiple trees work"""
    doc = Document(f"{local_dir}/multiple_tree.xml")
    assert tostring(
        doc.get_passage(tree=None, ref_or_start="I"), encoding=str
    ) == ('<TEI xmlns="http://www.tei-c.org/ns/1.0"><text>\n'
 '        <body>\n'
 '            <div xml:id="div-a1" n="I">\n'
 '                <p>Lorem ipsum dolor sit amet.</p>\n'
 '            </div>\n'
 '            </body>\n'
 '    </text>\n'
 '</TEI>'), "Default works"
    assert tostring(
        doc.get_passage(tree="alpha", ref_or_start="div-002"), encoding=str
    ) == ('<TEI xmlns="http://www.tei-c.org/ns/1.0"><text>\n'
 '        <body>\n'
 '            <div xml:id="div-002" n="1">\n'
 '                <p>Consectetur adipiscing elit.</p>\n'
 '            </div>\n'
 '            </body>\n'
 '    </text>\n'
 '</TEI>'), "Secondary works"
    assert tostring(doc.get_passage("div-002", tree="alpha"), encoding=str
                    ) == tostring(doc.get_passage("1", tree=None), encoding=str), "Both system work"
    assert tostring(doc.get_passage("1", tree=None), encoding=str
                    ) == tostring(doc.get_passage("1", tree="nums"), encoding=str), "Naming and default work"


def test_get_next_on_last():
    """Check that having multiple trees work"""
    doc = Document(f"{local_dir}/lb_same_ab.xml")
    assert tostring(
        doc.get_passage(tree=None, ref_or_start="5"), encoding=str
    ) == ('<TEI xmlns="http://www.tei-c.org/ns/1.0"><text>\n'
         '<body>\n'
         '<div xml:lang="grc" type="edition" xml:space="preserve">\n'
         '<ab>\n'
         '<lb n="5"/>εὖ εἴη, ἐφιορκοῦντι δὲ τὰ ἐναντία.\n'
         '</ab>\n'
         '</div>\n'
         '</body>\n'
         '</text>\n'
         '</TEI>'), "Default works"
    assert tostring(
        doc.get_passage(tree=None, ref_or_start="4", end="5"), encoding=str
    ) == ('<TEI xmlns="http://www.tei-c.org/ns/1.0"><text>\n'
         '<body>\n'
         '<div xml:lang="grc" type="edition" xml:space="preserve">\n'
         '<ab>\n'
         '<lb n="4"/>ἔχειν.  εὐορκοῦντι μέν μοι\n'
         '<lb n="5"/>εὖ εἴη, ἐφιορκοῦντι δὲ τὰ ἐναντία.\n'
         '</ab>\n'
         '</div>\n'
         '</body>\n'
         '</text>\n'
         '</TEI>'), "Default works"

    # And now uneven
    doc = Document(f"{local_dir}/lb_uneven_ab.xml")
    assert tostring(
        doc.get_passage(tree=None, ref_or_start="7"), encoding=str
    ) == ('<TEI xmlns="http://www.tei-c.org/ns/1.0"><text>\n'
         '<body>\n'
         '<div xml:lang="grc" type="edition" xml:space="preserve">\n'
         '<ab>\n'
         '<w><lb n="7"/>εὖ</w> εἴη, ἐφιορκοῦντι δὲ τὰ ἐναντία.\n'
         '</ab>\n'
         '</div>\n'
         '</body>\n'
         '</text>\n'
         '</TEI>'), "Default works"
    assert tostring(
        doc.get_passage(tree=None, ref_or_start="6", end="7"), encoding=str
    ) == ('<TEI xmlns="http://www.tei-c.org/ns/1.0"><text>\n'
         '<body>\n'
         '<div xml:lang="grc" type="edition" xml:space="preserve">\n'
         '<ab>\n'
         '<w><lb n="6"/>a</w> b\n'
         '<w><lb n="7"/>εὖ</w> εἴη, ἐφιορκοῦντι δὲ τὰ ἐναντία.\n'
         '</ab>\n'
         '</div>\n'
         '</body>\n'
         '</text>\n'
         '</TEI>'), "Default works"
    # And now uneven with an ending node
    doc = Document(f"{local_dir}/lb_uneven_ab_ending_node.xml")
    assert tostring(
        doc.get_passage(tree=None, ref_or_start="7"), encoding=str
    ) == ('<TEI xmlns="http://www.tei-c.org/ns/1.0"><text>\n'
         '<body>\n'
         '<div xml:lang="grc" type="edition" xml:space="preserve">\n'
         '<ab>\n'
         '<w><lb n="7"/>εὖ</w> εἴη, ἐφιορκοῦντι δὲ τὰ ἐναντία.<span>There is something there<w>'
          'That never changes</w></span>\n'
         '</ab>\n'
         '</div>\n'
         '</body>\n'
         '</text>\n'
         '</TEI>'), "Default works"


def test_passage_simple():
    """Test that a single passage matching works"""
    doc = Document(f"{local_dir}/simple_doc.xml")
    assert tostring(
        doc.get_passage("1"), encoding=str
    ) == ('<TEI xmlns="http://www.tei-c.org/ns/1.0"><text>\n'
 '        <body>\n'
 '            <div>\n'
 '                <p n="1">Lorem</p>\n'
 '                </div>\n'
 '        </body>\n'
 '    </text>\n'
 '</TEI>')

def test_passage_ranger_simple():
    """Test that a single range passage matching works"""
    doc = Document(f"{local_dir}/simple_doc.xml")
    assert tostring(
        doc.get_passage("2", "3"), encoding=str
    ) == ('<TEI xmlns="http://www.tei-c.org/ns/1.0"><text>\n'
 '        <body>\n'
 '            <div>\n'
 '                <p n="2">Ipsum</p>\n'
 '                <p n="3">Dolorem</p>\n'
 '            </div>\n'
 '        </body>\n'
 '    </text>\n'
 '</TEI>')


def test_xml_entity():
    """Test that a single range passage matching works"""
    doc = Document(f"{local_dir}/xml_entity.xml")
    assert tostring(
        doc.get_passage("2", "3"), encoding=str
    ) == ('<TEI xmlns="http://www.tei-c.org/ns/1.0"><text>\n'
 '        <body>\n'
 '            <div>\n'
 '                <p n="2">&amp; Ipsum</p>\n'
 '                <p n="3">Dolorem</p>\n'
 '            </div>\n'
 '        </body>\n'
 '    </text>\n'
 '</TEI>')
    doc = Document(f"{local_dir}/xml_entity_tail.xml")
    assert tostring(
        doc.get_passage("2", "3"), encoding=str
    ) == ('<TEI xmlns="http://www.tei-c.org/ns/1.0"><text>\n'
 '        <body>\n'
 '            <div>\n'
 '                <p>\n'
 '                <lb n="2"/>&amp; Ipsum\n'
 '                <lb n="3"/>Dolorem &amp;\n'
 '                </p>\n'
 '            </div>\n'
 '        </body>\n'
 '    </text>\n'
 '</TEI>')


def _flat_refs(refs: list[CitableUnit]) -> list[str]:
    data = []
    for ref in refs:
        data.append(ref.ref)
        data.extend(_flat_refs(ref.children))
    return data


def test_ref_parsing_uneven_tree():
    """Test that a level that can contain data is not missed"""
    doc = Document(f"{local_dir}/uneven_parent_level.xml")
    assert _flat_refs(doc.get_reffs()) == ['Luke', 'Luke 1', 'Luke 1#1', 'Luke:1', 'Mark', 'Mark:1', 'Mark:2']


def test_milestone_cb_lb():
    """Test that nested self-closing milestones (e.g. <cb/> containing <lb/> siblings) work"""
    doc = Document(f"{local_dir}/cb_lb_milestones.xml")

    refs = doc.get_reffs()
    assert [(r.ref, [c.ref for c in r.children]) for r in refs] == [
        ("1", ["1.1", "1.2", "1.3", "1.4"]),
        ("2", ["2.1", "2.2", "2.3", "2.4"]),
    ]

    # Same @n value ("1") in both columns must resolve to different, disambiguated lines
    assert tostring(doc.get_passage("1.1"), encoding=str) == (
        '<TEI xmlns="http://www.tei-c.org/ns/1.0"><text>\n'
        '    <body>\n'
        '      <div type="edition">\n'
        '        <ab>\n\n'
        '          <lb xml:id="c1l1" n="1"/>IMP CAESARI\n'
        '          </ab>\n'
        '      </div>\n'
        '    </body>\n'
        '  </text>\n'
        '</TEI>'
    )
    assert tostring(doc.get_passage("2.1"), encoding=str) == (
        '<TEI xmlns="http://www.tei-c.org/ns/1.0"><text>\n'
        '    <body>\n'
        '      <div type="edition">\n'
        '        <ab>\n\n'
        '          <lb xml:id="c2l1" n="1"/>COS XIII P P\n'
        '          </ab>\n'
        '      </div>\n'
        '    </body>\n'
        '  </text>\n'
        '</TEI>'
    )

    # Last line of column 1 must not bleed into column 2's content
    assert tostring(doc.get_passage("1.4"), encoding=str) == (
        '<TEI xmlns="http://www.tei-c.org/ns/1.0"><text>\n'
        '    <body>\n'
        '      <div type="edition">\n'
        '        <ab>\n\n'
        '          <lb xml:id="c1l4" n="4"/>TRIB POTESTATE X\n\n'
        '          </ab>\n'
        '      </div>\n'
        '    </body>\n'
        '  </text>\n'
        '</TEI>'
    )

    # A range crossing the column boundary should include the <cb/> milestone itself
    assert tostring(doc.get_passage("1.4", "2.1"), encoding=str) == (
        '<TEI xmlns="http://www.tei-c.org/ns/1.0"><text>\n'
        '    <body>\n'
        '      <div type="edition">\n'
        '        <ab>\n\n'
        '          <lb xml:id="c1l4" n="4"/>TRIB POTESTATE X\n\n'
        '          <cb xml:id="c2" n="2"/>\n'
        '          <lb xml:id="c2l1" n="1"/>COS XIII P P\n'
        '          </ab>\n'
        '      </div>\n'
        '    </body>\n'
        '  </text>\n'
        '</TEI>'
    )


def test_milestone_pb_cb_lb():
    """Test a 3-level manuscript milestone hierarchy: page (<pb/>) > column (<cb/>) > line (<lb/>)"""
    doc = Document(f"{local_dir}/pb_cb_lb_milestones.xml")

    assert _flat_refs(doc.get_reffs()) == [
        "1", "1.1", "1.1.1", "1.1.2", "1.2", "1.2.1", "1.2.2",
        "2", "2.1", "2.1.1", "2.1.2", "2.2", "2.2.1", "2.2.2",
    ]

    # Same @n values ("1"/"2") repeat for column and line across every page; each must resolve
    # to its own, disambiguated line.
    assert tostring(doc.get_passage("1.1.1"), encoding=str) == (
        '<TEI xmlns="http://www.tei-c.org/ns/1.0"><text>\n'
        '    <body>\n'
        '      <div type="edition">\n'
        '        <ab>\n\n'
        '          <lb xml:id="p1c1l1" n="1"/>alpha\n'
        '          </ab>\n'
        '      </div>\n'
        '    </body>\n'
        '  </text>\n'
        '</TEI>'
    )
    assert tostring(doc.get_passage("2.2.1"), encoding=str) == (
        '<TEI xmlns="http://www.tei-c.org/ns/1.0"><text>\n'
        '    <body>\n'
        '      <div type="edition">\n'
        '        <ab>\n\n'
        '          <lb xml:id="p2c2l1" n="1"/>eta\n'
        '          </ab>\n'
        '      </div>\n'
        '    </body>\n'
        '  </text>\n'
        '</TEI>'
    )

    # Last line of the last column of page 1 must not bleed into page 2's content, but may
    # include the upcoming <pb/> milestone marker itself
    assert tostring(doc.get_passage("1.2.2"), encoding=str) == (
        '<TEI xmlns="http://www.tei-c.org/ns/1.0"><text>\n'
        '    <body>\n'
        '      <div type="edition">\n'
        '        <ab>\n\n'
        '          <lb xml:id="p1c2l2" n="2"/>delta\n\n'
        '          <pb xml:id="p2" n="2"/>\n'
        '          </ab>\n'
        '      </div>\n'
        '    </body>\n'
        '  </text>\n'
        '</TEI>'
    )

    # A range crossing the page boundary should include both the <pb/> and <cb/> milestones
    assert tostring(doc.get_passage("1.2.2", "2.1.1"), encoding=str) == (
        '<TEI xmlns="http://www.tei-c.org/ns/1.0"><text>\n'
        '    <body>\n'
        '      <div type="edition">\n'
        '        <ab>\n\n'
        '          <lb xml:id="p1c2l2" n="2"/>delta\n\n'
        '          <pb xml:id="p2" n="2"/>\n'
        '          <cb xml:id="p2c1" n="1"/>\n'
        '          <lb xml:id="p2c1l1" n="1"/>epsilon\n'
        '          </ab>\n'
        '      </div>\n'
        '    </body>\n'
        '  </text>\n'
        '</TEI>'
    )
def test_standoff_all_linking_cases():
    """include_standoff=True resolves three reference directions:
    (1) passage → standOff via @corresp/@ref,
    (2) standOff → passage via @target,
    (3) transitive standOff → standOff via @ana (fixed-point expansion).
    Only elements relevant to the retrieved passage (div n="1") are included.
    """
    doc = Document(f"{local_dir}/tei_with_standoff.xml")
    result = tostring(doc.get_passage("1", include_standoff=True), encoding=str)

    # passage content
    assert 'xml:id="w1"' in result
    assert 'xml:id="w7"' not in result        # div n="2" excluded from passage

    # case 1: passage → standOff
    assert 'xml:id="LATL"' in result           # corresp="#LATL" in passage
    assert 'xml:id="LBHM"' in result           # corresp="#LBHM" in passage
    assert 'xml:id="MLK"' in result            # ref="#MLK" in passage
    assert 'xml:id="LDAL"' not in result       # referenced only from div n="2"
    assert 'xml:id="JFK"' not in result        # not referenced from passage

    # case 2: standOff → passage
    assert 'target="#w1"' in result            # w1 has xml:id in passage
    assert 'target="#w2"' in result
    assert 'target="#w3"' in result
    assert 'target="#w7"' not in result        # w7 not in passage

    # case 3: transitive standOff → standOff
    assert 'xml:id="pos-NNP"' in result        # @ana on included spans
    assert 'xml:id="pos-JJ"' not in result     # @ana only on excluded span (target="#w7")

    # standOff comes after text
    assert result.index('<text') < result.index('<standOff')


def test_include_header():
    """include_header=True prepends the full teiHeader; absent by default."""
    doc = Document(f"{local_dir}/tei_with_standoff.xml")
    without = tostring(doc.get_passage("1"), encoding=str)
    assert '<teiHeader' not in without

    with_header = tostring(doc.get_passage("1", include_header=True), encoding=str)
    assert '<teiHeader' in with_header
    assert with_header.index('<teiHeader') < with_header.index('<text')


def test_include_header_and_standoff():
    """When both flags are set the order is teiHeader → text → standOff."""
    doc = Document(f"{local_dir}/tei_with_standoff.xml")
    result = tostring(doc.get_passage("1", include_header=True, include_standoff=True), encoding=str)
    assert result.index('<teiHeader') < result.index('<text') < result.index('<standOff')


def test_standoff_no_standoff():
    """include_standoff=True on a document with no standOff raises no error."""
    doc = Document(f"{local_dir}/base_tei.xml")
    result = tostring(doc.get_passage("Luke 1:1", include_standoff=True), encoding=str)
    assert '<standOff' not in result
