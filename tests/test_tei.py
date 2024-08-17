import os.path

import pytest
from dapitains.local.tei import Document
from lxml.etree import tostring

local_dir = os.path.join(os.path.dirname(__file__), "tei")


def test_single_passage():
    """Test that a single passage matching works"""
    doc = Document(f"{local_dir}/base_tei.xml")
    assert tostring(
        doc.get_passage("Luke 1:1"), encoding=str
    ) == ('<TEI xmlns="http://www.tei-c.org/ns/1.0" xmlns:py="http://codespeak.net/lxml/objectify/pytype"'
          ' py:pytype="TREE"><text><body>'
          '<div n="Luke"><div><div>Text</div></div></div></body></text></TEI>')


def test_simple_range():
    """Test that a range with two different xpath work"""
    doc = Document(f"{local_dir}/base_tei.xml")
    assert tostring(
        doc.get_passage(ref_or_start="Luke 1:1", end="Luke 1#1"), encoding=str
    ) == ('<TEI xmlns="http://www.tei-c.org/ns/1.0" xmlns:py="http://codespeak.net/lxml/objectify/pytype"'
          ' py:pytype="TREE"><text><body><div n="Luke"><div><div>Text</div><div>Text 2</div><l>Text 3</l></div>'
          '</div></body></text></TEI>')


def test_different_level_range():
    """Test that a range with two different xpath and two different level work"""
    doc = Document(f"{local_dir}/tei_with_two_traversing_with_n.xml")
    assert tostring(
        doc.get_passage(ref_or_start="Luke 1:1", end="Luke 1#3"), encoding=str
    ) == """<TEI xmlns="http://www.tei-c.org/ns/1.0" xmlns:py="http://codespeak.net/lxml/objectify/pytype" py:pytype="TREE"><text><body><div n="Luke"><div n="1"><div n="1">Text</div><div n="2">Text 2</div><lg>
   <l n="1">Text 3</l>
   <l n="2">Text 4</l>
</lg><l n="3">Text 5</l></div></div></body></text></TEI>"""

    assert tostring(
        doc.get_passage(ref_or_start="Luke 1:1", end="Luke 1#1"), encoding=str
    ) == ('<TEI xmlns="http://www.tei-c.org/ns/1.0" xmlns:py="http://codespeak.net/lxml/objectify/pytype" '
          'py:pytype="TREE"><text><body><div n="Luke"><div n="1"><div n="1">Text</div><div n="2">Text 2</div><lg>'
          '<l n="1">Text 3</l></lg></div></div></body></text></TEI>')


def test_different_level_range_fails_on_position():
    doc = Document(f"{local_dir}/tei_with_two_traversing.xml")
    # This should fail, because //something[position()=3] does not go from one element to another. Yet another
    #   reason to NOT use it.
    with pytest.raises(TypeError):
        doc.get_passage(ref_or_start="Luke 1:1", end="Luke 1#3")

