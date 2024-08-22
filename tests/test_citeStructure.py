from dapitains.local.citeStructure import CiteStructureParser
from dapitains.constants import PROCESSOR, get_xpath_proc
import pytest


def test_parsing():
    xml_string = """<TEI xmlns="http://www.tei-c.org/ns/1.0">
    <teiHeader>
        <refsDecl>
            <citeStructure unit="book" match="//body/div" use="@n">
                <citeStructure unit="chapter" match="div" use="position()" delim=" ">
                    <citeStructure unit="verse" match="div" use="position()" delim=":"/>
                    <citeStructure unit="bloup" match="l" use="position()" delim="#"/>
                </citeStructure>
            </citeStructure>
        </refsDecl>
    </teiHeader>
    <text>
    <body>
    <div n="Luke">
        <div>
            <div>Text</div>
            <div>Text 2</div>
            <l>Text 3</l>
        </div>
    </div>
    <div n="Mark">
        <div>
            <div>Text A</div>
            <div>Text B</div>
            <l>Text C</l>
            <div>Text D</div>
        </div>
    </div>
    </body>
    </text>
    </TEI>
    """
    TEI = PROCESSOR.parse_xml(xml_text=xml_string)
    xpath = get_xpath_proc(elem=TEI)
    citeStructure = xpath.evaluate_single("/TEI/teiHeader/refsDecl[1]")
    parser = CiteStructureParser(citeStructure)

    # Generate XPath for "Luke 1:2"
    assert parser.generate_xpath("Luke 1:2") == "//body/div[@n='Luke']/div[position()=1]/div[position()=2]"

    # Generate XPath for "Luke 1#3"
    assert parser.generate_xpath("Luke 1#3") == "//body/div[@n='Luke']/div[position()=1]/l[position()=3]"

    # Generate XPath for "Luke 1" (partial match)
    assert parser.generate_xpath("Luke 1") == "//body/div[@n='Luke']/div[position()=1]"

    # Generate XPath for "Luke 1" (partial match)
    assert parser.generate_xpath("Luke") == "//body/div[@n='Luke']"

    assert [root.to_dts() for root in parser.find_refs(root=TEI, structure=parser.units)] == [
        {'citeType': 'book', 'ref': 'Luke', 'members': [
            {'citeType': 'chapter', 'ref': 'Luke 1', 'members': [
                {'citeType': 'verse', 'ref': 'Luke 1:1'},
                {'citeType': 'verse', 'ref': 'Luke 1:2'},
                {'citeType': 'bloup', 'ref': 'Luke 1#1'}
                ]}
        ]},
        {'citeType': 'book', 'ref': 'Mark', 'members': [
            {'citeType': 'chapter', 'ref': 'Mark 1', 'members': [
                {'citeType': 'verse', 'ref': 'Mark 1:1'},
                {'citeType': 'verse', 'ref': 'Mark 1:2'},
                {'citeType': 'bloup', 'ref': 'Mark 1#1'},
                {'citeType': 'verse', 'ref': 'Mark 1:3'}
            ]}
        ]}
    ]
