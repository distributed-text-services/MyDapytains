"""
Tests for processor-reuse stability: verifies that sharing or reusing Saxon
XPath/XQuery processors across successive calls and across multiple Document
instances does not corrupt context or results.
"""
import os.path

from lxml.etree import tostring

from dapytains.processor import get_processor, get_xpath_proc
from dapytains.tei.citeStructure import CiteStructureParser
from dapytains.tei.document import Document

local_dir = os.path.join(os.path.dirname(__file__), "tei")
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))




# ─────────────────────────────────────────────────────────────
# Successive calls on the SAME Document instance
# ─────────────────────────────────────────────────────────────

def test_successive_single_passages():
    """get_passage called repeatedly on one Document must give stable results."""
    doc = Document(f"{local_dir}/base_tei.xml")
    expected_1_1 = tostring(doc.get_passage("Luke 1:1"), encoding=str)
    expected_1_2 = tostring(doc.get_passage("Luke 1:2"), encoding=str)

    # Call again — shared XPath processor state must not bleed between calls
    assert tostring(doc.get_passage("Luke 1:1"), encoding=str) == expected_1_1
    assert tostring(doc.get_passage("Luke 1:2"), encoding=str) == expected_1_2
    assert tostring(doc.get_passage("Luke 1:1"), encoding=str) == expected_1_1


def test_successive_range_then_single():
    """A range call followed by a single-ref call must not corrupt context.

    reconstruct_doc calls xpath_proc.set_context(result_end) mid-function;
    this test confirms that state does not leak into the next call.
    """
    doc = Document(f"{local_dir}/base_tei.xml")
    expected_single = tostring(doc.get_passage("Luke 1:1"), encoding=str)
    expected_range  = tostring(doc.get_passage("Luke 1:1", "Luke 1#1"), encoding=str)

    for _ in range(3):
        assert tostring(doc.get_passage("Luke 1:1", "Luke 1#1"), encoding=str) == expected_range
        assert tostring(doc.get_passage("Luke 1:1"),             encoding=str) == expected_single


def test_successive_reffs_and_passage():
    """get_reffs and get_passage interleaved on the same Document must be stable."""
    doc = Document(f"{local_dir}/base_tei.xml")
    reffs_1 = [r.ref for r in doc.get_reffs()]
    passage  = tostring(doc.get_passage("Luke 1:1"), encoding=str)
    reffs_2 = [r.ref for r in doc.get_reffs()]

    assert reffs_1 == reffs_2, (
        "get_reffs must return the same refs before and after get_passage"
    )
    assert tostring(doc.get_passage("Luke 1:1"), encoding=str) == passage


def test_successive_calls_with_traversing_xpath():
    """Documents using .// XPaths exercise is_traversing_xpath; calls must be stable."""
    doc = Document(f"{local_dir}/tei_with_two_traversing_with_n.xml")
    expected_wide   = tostring(doc.get_passage("Luke 1:1", "Luke 1#3"), encoding=str)
    expected_narrow = tostring(doc.get_passage("Luke 1:1", "Luke 1#1"), encoding=str)

    for _ in range(3):
        assert tostring(doc.get_passage("Luke 1:1", "Luke 1#3"), encoding=str) == expected_wide
        assert tostring(doc.get_passage("Luke 1:1", "Luke 1#1"), encoding=str) == expected_narrow


def test_successive_calls_lb_milestone():
    """Milestone (lb) documents: successive range and single calls stay consistent."""
    doc = Document(f"{local_dir}/lb_same_ab.xml")
    single = tostring(doc.get_passage("2"),      encoding=str)
    rng    = tostring(doc.get_passage("2", "4"), encoding=str)
    last   = tostring(doc.get_passage("5"),      encoding=str)

    for _ in range(3):
        assert tostring(doc.get_passage("2"),      encoding=str) == single
        assert tostring(doc.get_passage("2", "4"), encoding=str) == rng
        assert tostring(doc.get_passage("5"),      encoding=str) == last


def test_successive_calls_multiple_trees():
    """Switching between trees on the same Document must always return correct results."""
    doc = Document(f"{local_dir}/multiple_tree.xml")
    default_passage = tostring(doc.get_passage("I"),          encoding=str)
    alpha_passage   = tostring(doc.get_passage("div-002", tree="alpha"), encoding=str)

    for _ in range(3):
        assert tostring(doc.get_passage("I"),                   encoding=str) == default_passage
        assert tostring(doc.get_passage("div-002", tree="alpha"), encoding=str) == alpha_passage
        assert tostring(doc.get_passage("I"),                   encoding=str) == default_passage


# ─────────────────────────────────────────────────────────────
# Multiple Document instances in memory simultaneously
# ─────────────────────────────────────────────────────────────

def test_two_docs_in_memory_independent():
    """Two Document objects with separate processors must not share state."""
    doc_a = Document(f"{local_dir}/base_tei.xml")
    doc_b = Document(f"{local_dir}/simple_doc.xml")

    result_a = tostring(doc_a.get_passage("Luke 1:1"), encoding=str)
    result_b = tostring(doc_b.get_passage("1"),        encoding=str)

    # Re-query after the other document has been used
    assert tostring(doc_a.get_passage("Luke 1:1"), encoding=str) == result_a
    assert tostring(doc_b.get_passage("1"),        encoding=str) == result_b


def test_two_docs_same_file_independent():
    """Two Document objects from the same file must produce identical, independent results."""
    doc_a = Document(f"{local_dir}/base_tei.xml")
    doc_b = Document(f"{local_dir}/base_tei.xml")

    single_a = tostring(doc_a.get_passage("Luke 1:1"), encoding=str)
    single_b = tostring(doc_b.get_passage("Luke 1:1"), encoding=str)
    assert single_a == single_b

    range_a = tostring(doc_a.get_passage("Luke 1:1", "Luke 1#1"), encoding=str)
    range_b = tostring(doc_b.get_passage("Luke 1:1", "Luke 1#1"), encoding=str)
    assert range_a == range_b

    # Using doc_a must not affect doc_b
    tostring(doc_a.get_passage("Luke 1:2"), encoding=str)
    assert tostring(doc_b.get_passage("Luke 1:1"),             encoding=str) == single_b
    assert tostring(doc_b.get_passage("Luke 1:1", "Luke 1#1"), encoding=str) == range_b


def test_interleaved_calls_two_different_docs():
    """Interleave passage calls between two structurally different documents."""
    doc_a = Document(f"{local_dir}/base_tei.xml")
    doc_b = Document(f"{local_dir}/tei_with_two_traversing_with_n.xml")

    expected_a = tostring(doc_a.get_passage("Luke 1:1"), encoding=str)
    expected_b = tostring(doc_b.get_passage("Luke 1:1", "Luke 1#3"), encoding=str)

    for _ in range(3):
        assert tostring(doc_a.get_passage("Luke 1:1"),             encoding=str) == expected_a
        assert tostring(doc_b.get_passage("Luke 1:1", "Luke 1#3"), encoding=str) == expected_b
        assert tostring(doc_a.get_passage("Luke 1:1"),             encoding=str) == expected_a


def test_three_docs_in_memory():
    """Three Document objects alive simultaneously all return correct results."""
    doc_a = Document(f"{local_dir}/base_tei.xml")
    doc_b = Document(f"{local_dir}/simple_doc.xml")
    doc_c = Document(f"{local_dir}/lb_same_ab.xml")

    expected_a = tostring(doc_a.get_passage("Luke 1:1"), encoding=str)
    expected_b = tostring(doc_b.get_passage("2", "3"),   encoding=str)
    expected_c = tostring(doc_c.get_passage("2", "4"),   encoding=str)

    # Query in rotated order
    assert tostring(doc_c.get_passage("2", "4"),   encoding=str) == expected_c
    assert tostring(doc_a.get_passage("Luke 1:1"), encoding=str) == expected_a
    assert tostring(doc_b.get_passage("2", "3"),   encoding=str) == expected_b
    assert tostring(doc_b.get_passage("2", "3"),   encoding=str) == expected_b
    assert tostring(doc_c.get_passage("2", "4"),   encoding=str) == expected_c
    assert tostring(doc_a.get_passage("Luke 1:1"), encoding=str) == expected_a


# ─────────────────────────────────────────────────────────────
# Multiple XML nodes via a SHARED PySaxonProcessor
# ─────────────────────────────────────────────────────────────

def test_shared_processor_two_docs():
    """Two Documents sharing a PySaxonProcessor must stay independent."""
    processor = get_processor()
    doc_a = Document(f"{local_dir}/base_tei.xml",   processor=processor)
    doc_b = Document(f"{local_dir}/simple_doc.xml", processor=processor)

    result_a = tostring(doc_a.get_passage("Luke 1:1"), encoding=str)
    result_b = tostring(doc_b.get_passage("1"),        encoding=str)

    for _ in range(3):
        assert tostring(doc_a.get_passage("Luke 1:1"), encoding=str) == result_a
        assert tostring(doc_b.get_passage("1"),        encoding=str) == result_b


def test_shared_processor_interleaved_reffs():
    """get_reffs on two docs sharing a processor must return independent, stable results."""
    processor = get_processor()
    doc_a = Document(f"{local_dir}/base_tei.xml",   processor=processor)
    doc_b = Document(f"{local_dir}/simple_doc.xml", processor=processor)

    reffs_a1 = [r.ref for r in doc_a.get_reffs()]
    reffs_b1 = [r.ref for r in doc_b.get_reffs()]

    # Query in the opposite order
    reffs_b2 = [r.ref for r in doc_b.get_reffs()]
    reffs_a2 = [r.ref for r in doc_a.get_reffs()]

    assert reffs_a1 == reffs_a2, "doc_a refs must be stable"
    assert reffs_b1 == reffs_b2, "doc_b refs must be stable"
    assert set(reffs_a1) != set(reffs_b1), "different documents must have different top-level refs"


def test_shared_processor_passage_and_reffs_interleaved():
    """Mix get_passage and get_reffs across two docs on a shared processor."""
    processor = get_processor()
    doc_a = Document(f"{local_dir}/base_tei.xml",   processor=processor)
    doc_b = Document(f"{local_dir}/simple_doc.xml", processor=processor)

    passage_a = tostring(doc_a.get_passage("Luke 1:1"), encoding=str)
    reffs_b   = [r.ref for r in doc_b.get_reffs()]
    passage_b = tostring(doc_b.get_passage("2"),        encoding=str)
    reffs_a   = [r.ref for r in doc_a.get_reffs()]

    assert tostring(doc_a.get_passage("Luke 1:1"), encoding=str) == passage_a
    assert [r.ref for r in doc_b.get_reffs()]      == reffs_b
    assert tostring(doc_b.get_passage("2"),        encoding=str) == passage_b
    assert [r.ref for r in doc_a.get_reffs()]      == reffs_a


# ─────────────────────────────────────────────────────────────
# CiteStructureParser successive calls and multiple parsers
# ─────────────────────────────────────────────────────────────

_MIXED_CHILDREN_XML = """<TEI xmlns="http://www.tei-c.org/ns/1.0">
<teiHeader><encodingDesc><refsDecl>
    <citeStructure unit="book" match="//body/div" use="@n">
        <citeStructure unit="chapter" match="div" use="position()" delim=" ">
            <citeStructure unit="verse" match="div" use="position()" delim=":"/>
            <citeStructure unit="bloup" match="l"   use="position()" delim="#"/>
        </citeStructure>
    </citeStructure>
</refsDecl></encodingDesc></teiHeader>
<text><body>
<div n="Luke"><div><div>T1</div><div>T2</div><l>T3</l></div></div>
<div n="Mark"><div><div>A</div><l>B</l><div>C</div></div></div>
</body></text></TEI>"""


def test_citestructure_successive_find_refs():
    """find_refs called multiple times on the same parser must produce stable results."""
    processor = get_processor()
    TEI = processor.parse_xml(xml_text=_MIXED_CHILDREN_XML)
    xp = get_xpath_proc(elem=TEI, processor=processor)
    parser = CiteStructureParser(
        xp.evaluate_single("/TEI/teiHeader/encodingDesc/refsDecl[1]"),
        processor=processor
    )

    for _ in range(3):
        roots = parser.find_refs(root=TEI, structure=parser.structure)
        refs = [r.ref for r in roots]
        assert refs == ["Luke", "Mark"], "top-level refs must be stable"

        luke_children = [c.ref for c in roots[0].children[0].children]
        assert luke_children == ["Luke 1:1", "Luke 1:2", "Luke 1#1"], (
            "mixed-type children must stay in document order"
        )

        mark_children = [c.ref for c in roots[1].children[0].children]
        assert mark_children == ["Mark 1:1", "Mark 1#1", "Mark 1:2"], (
            "mixed-type children in Mark must follow document order"
        )


def test_citestructure_two_parsers_shared_processor():
    """Two CiteStructureParsers on different XML nodes sharing a processor must not interfere."""
    processor = get_processor()

    tei_a = processor.parse_xml(xml_text="""<TEI xmlns="http://www.tei-c.org/ns/1.0">
    <teiHeader><encodingDesc><refsDecl>
        <citeStructure unit="section" match="//body/div" use="@n"/>
    </refsDecl></encodingDesc></teiHeader>
    <text><body><div n="1">A</div><div n="2">B</div></body></text></TEI>""")

    tei_b = processor.parse_xml(xml_text="""<TEI xmlns="http://www.tei-c.org/ns/1.0">
    <teiHeader><encodingDesc><refsDecl>
        <citeStructure unit="section" match="//body/div" use="@n"/>
    </refsDecl></encodingDesc></teiHeader>
    <text><body><div n="alpha">X</div><div n="beta">Y</div></body></text></TEI>""")

    xp_a = get_xpath_proc(elem=tei_a, processor=processor)
    xp_b = get_xpath_proc(elem=tei_b, processor=processor)
    parser_a = CiteStructureParser(
        xp_a.evaluate_single("/TEI/teiHeader/encodingDesc/refsDecl[1]"), processor=processor
    )
    parser_b = CiteStructureParser(
        xp_b.evaluate_single("/TEI/teiHeader/encodingDesc/refsDecl[1]"), processor=processor
    )

    refs_a = [r.ref for r in parser_a.find_refs(root=tei_a, structure=parser_a.structure)]
    refs_b = [r.ref for r in parser_b.find_refs(root=tei_b, structure=parser_b.structure)]

    assert refs_a == ["1", "2"]
    assert refs_b == ["alpha", "beta"]

    # Swap query order — must still give correct results
    assert [r.ref for r in parser_b.find_refs(root=tei_b, structure=parser_b.structure)] == refs_b
    assert [r.ref for r in parser_a.find_refs(root=tei_a, structure=parser_a.structure)] == refs_a


def test_citestructure_generate_xpath_stable():
    """generate_xpath must return consistent results across repeated calls."""
    processor = get_processor()
    TEI = processor.parse_xml(xml_text=_MIXED_CHILDREN_XML)
    xp = get_xpath_proc(elem=TEI, processor=processor)
    parser = CiteStructureParser(
        xp.evaluate_single("/TEI/teiHeader/encodingDesc/refsDecl[1]"),
        processor=processor
    )

    for _ in range(5):
        assert parser.generate_xpath("Luke 1:2") == "//body/div[@n='Luke']/div[position()=1]/div[position()=2]"
        assert parser.generate_xpath("Mark 1#1") == "//body/div[@n='Mark']/div[position()=1]/l[position()=1]"
        assert parser.generate_xpath("Luke")     == "//body/div[@n='Luke']"

