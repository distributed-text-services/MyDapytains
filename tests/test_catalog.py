import os.path

from dapitains.metadata.xml_parser import parse
from dapitains.metadata.classes import *


local_dir = os.path.join(os.path.dirname(__file__))


def test_ingestion():
    tree, _ = parse(f"{local_dir}/catalog/example-collection.xml")

    assert tree.objects == {
        "https://foo.bar/default": Collection(
            identifier='https://foo.bar/default',
            title='A collection', description=None,
            dublin_core=[
                DublinCore(term='abstract', value='This is a perfect example of an absract.', language=None),
                DublinCore(term='abstract', value='Et je peux traduire en français', language='fr')], extensions=[],
            resource=False,
            filepath=None
        ),
        "https://example.org/collection1": Collection(
            identifier='https://example.org/collection1',
            title='My First Collection',
            description=None,
            dublin_core=[
                DublinCore(term='creator', value='John Doe', language=None),
                DublinCore(term='subject', value='History', language=None),
                DublinCore(term='date', value='2023-08-24', language=None)
            ],
            extensions=[],
            resource=False,
            filepath=None
        ),
        "https://example.org/resource1": Collection(
            identifier='https://example.org/resource1',
            title='Historical Document',
            description='A document about historical events.',
            dublin_core=[
                DublinCore(term='subject', value='World War II', language=None),
                DublinCore(term='language', value='en', language=None)
            ],
            extensions=[], resource=True,
            filepath=os.path.abspath(f"{local_dir}/tei/multiple_tree.xml")
        ),
        "https://foo.bar/text": Collection(
            identifier='https://foo.bar/text',
            title='A simple resource',
            description='With a description',
            dublin_core=[
                DublinCore(term='title', value='A simple resource', language=None)
            ],
            extensions=[],
            resource=True,
            filepath=os.path.abspath(f"{local_dir}/tei/base_tei.xml")
        )
    }

    assert sorted(tree.relationships) == [
        ('https://example.org/collection1', 'https://example.org/resource1'),
        ('https://foo.bar/default', 'https://example.org/collection1'),
        ('https://foo.bar/default', 'https://example.org/resource1',),
        ('https://foo.bar/default', 'https://foo.bar/text')
    ]
