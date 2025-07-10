import os.path

import pytest
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
