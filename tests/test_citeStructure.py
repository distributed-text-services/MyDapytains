from dapytains.tei.citeStructure import CiteStructureParser
from dapytains.constants import PROCESSOR, get_xpath_proc
import os.path
import pytest

local_dir = os.path.join(os.path.dirname(__file__), "tei")




def test_parsing():
    xml_string = """<TEI xmlns="http://www.tei-c.org/ns/1.0">
    <teiHeader>
        <encodingDesc>
            <refsDecl>
                <citeStructure unit="book" match="//body/div" use="@n">
                    <citeStructure unit="chapter" match="div" use="position()" delim=" ">
                        <citeStructure unit="verse" match="div" use="position()" delim=":"/>
                        <citeStructure unit="bloup" match="l" use="position()" delim="#"/>
                    </citeStructure>
                </citeStructure>
            </refsDecl>
        </encodingDesc>
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
    citeStructure = xpath.evaluate_single("/TEI/teiHeader/encodingDesc/refsDecl[1]")
    parser = CiteStructureParser(citeStructure)

    # Generate XPath for "Luke 1:2"
    assert parser.generate_xpath("Luke 1:2") == "//body/div[@n='Luke']/div[position()=1]/div[position()=2]"

    # Generate XPath for "Luke 1#3"
    assert parser.generate_xpath("Luke 1#3") == "//body/div[@n='Luke']/div[position()=1]/l[position()=3]"

    # Generate XPath for "Luke 1" (partial match)
    assert parser.generate_xpath("Luke 1") == "//body/div[@n='Luke']/div[position()=1]"

    # Generate XPath for "Luke 1" (partial match)
    assert parser.generate_xpath("Luke") == "//body/div[@n='Luke']"

    assert [root.json() for root in parser.find_refs(root=TEI, structure=parser.structure)] == [
        {'citeType': 'book', 'identifier': 'Luke', 'parent': None, 'level': 1, 'members': [
            {'citeType': 'chapter', 'identifier': 'Luke 1', 'parent': 'Luke', 'level': 2,  'members': [
                {'citeType': 'verse', 'identifier': 'Luke 1:1', 'parent': 'Luke 1', 'level': 3},
                {'citeType': 'verse', 'identifier': 'Luke 1:2', 'parent': 'Luke 1', 'level': 3},
                {'citeType': 'bloup', 'identifier': 'Luke 1#1', 'parent': 'Luke 1', 'level': 3}
                ]
            }
        ]},
        {'citeType': 'book', 'identifier': 'Mark', 'parent': None, 'level': 1, 'members': [
            {'citeType': 'chapter', 'identifier': 'Mark 1', 'parent': 'Mark', 'level': 2, 'members': [
                {'citeType': 'verse', 'identifier': 'Mark 1:1', 'parent': 'Mark 1', 'level': 3},
                {'citeType': 'verse', 'identifier': 'Mark 1:2', 'parent': 'Mark 1', 'level': 3},
                {'citeType': 'bloup', 'identifier': 'Mark 1#1', 'parent': 'Mark 1', 'level': 3},
                {'citeType': 'verse', 'identifier': 'Mark 1:3', 'parent': 'Mark 1', 'level': 3}
            ]}
        ]}
    ]

def test_cite_data():
    TEI = PROCESSOR.parse_xml(xml_file_name=f"{local_dir}/test_citeData.xml")
    xpath = get_xpath_proc(elem=TEI)
    citeStructure = xpath.evaluate_single("/TEI/teiHeader/encodingDesc/refsDecl[1]")
    parser = CiteStructureParser(citeStructure)
    refs = parser.find_refs(root=TEI, structure=parser.structure)
    refs = [ref.json() for ref in refs]
    assert refs == [
        {'citeType': 'book', 'identifier': '1', 'parent': None, 'level': 1, 'dublinCore': {
            'http://purl.org/dc/terms/title': ['Introduction', 'Introduction'],
            'http://purl.org/dc/terms/creator': ['John Doe']}},
        {'citeType': 'book', 'identifier': '2', 'parent': None, 'level': 1, 'dublinCore': {'http://purl.org/dc/terms/title': ["Background", 'Contexte']}},
        {'citeType': 'book', 'identifier': '3', 'parent': None, 'level': 1, 'dublinCore': {
            'http://purl.org/dc/terms/title': ['Methodology', 'Méthodologie'],
            'http://purl.org/dc/terms/creator': ['Albert Einstein']}},
        {'citeType': 'book', 'identifier': '4', 'parent': None, 'level': 1, 'dublinCore': {
            'http://purl.org/dc/terms/title': ['Results', 'Résultats'],
            'http://purl.org/dc/terms/creator': ['Isaac Newton']}},
        {'citeType': 'book', 'identifier': '5', 'parent': None, 'level': 1, 'dublinCore': {
            'http://purl.org/dc/terms/title': ['Conclusion', 'Conclusion'],
            'http://purl.org/dc/terms/creator': ['Marie Curie']
        }}]


def test_advanced_cite_data():
    TEI = PROCESSOR.parse_xml(xml_file_name=f"{local_dir}/test_citeData_two_levels.xml")
    xpath = get_xpath_proc(elem=TEI)
    citeStructure = xpath.evaluate_single("/TEI/teiHeader/encodingDesc/refsDecl[1]")
    parser = CiteStructureParser(citeStructure)
    refs = parser.find_refs(root=TEI, structure=parser.structure)
    refs = [ref.json() for ref in refs]
    assert refs == [
        {'citeType': 'part', 'identifier': 'part-1', 'parent': None, 'level': 1, 'members': [
            {'citeType': 'book', 'identifier': 'part-1.1', 'parent': 'part-1', 'level': 2, 'dublinCore': {
                'http://purl.org/dc/terms/title': ['Introduction', 'Introduction'],
                'http://purl.org/dc/terms/creator': ['John Doe']}},
            {'citeType': 'book', 'identifier': 'part-1.2', 'parent': 'part-1', 'level': 2, 'dublinCore': {
                'http://purl.org/dc/terms/title': ["Background", 'Contexte']
            }}
        ], 'extension': {"http://foo.bar/part": ["1"]}},
        {'citeType': 'part', 'identifier': 'part-2', 'parent': None, 'level': 1, 'members': [
            {'citeType': 'book', 'identifier': 'part-2.3', 'parent': 'part-2', 'level': 2, 'dublinCore': {
                'http://purl.org/dc/terms/title': ['Methodology', 'Méthodologie'],
                'http://purl.org/dc/terms/creator': ['Albert Einstein']}},
            {'citeType': 'book', 'identifier': 'part-2.4', 'parent': 'part-2', 'level': 2, 'dublinCore': {
                'http://purl.org/dc/terms/title': ['Results', 'Résultats'],
                'http://purl.org/dc/terms/creator': ['Isaac Newton']}}
        ], 'extension': {"http://foo.bar/part": ["2"]}},
        {'citeType': 'part', 'identifier': 'part-3', 'parent': None, 'level': 1, 'members': [
            {'citeType': 'book', 'identifier': 'part-3.5', 'parent': 'part-3', 'level': 2, 'dublinCore': {
                'http://purl.org/dc/terms/title': ['Conclusion', 'Conclusion'],
                'http://purl.org/dc/terms/creator': ['Marie Curie']
            }}
        ], 'extension': {"http://foo.bar/part": ["3"]}}]
