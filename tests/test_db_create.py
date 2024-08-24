import flask
from dapitains.app.ingest import generate_paths, get_member_by_path, get_nav, strip_members
from dapitains.tei.document import Document
import os


local_dir = os.path.join(os.path.dirname(__file__))


def test_simple_path():
    """Check that a document can be parsed and that path are corrects"""
    doc = Document(f"{local_dir}/tei/multiple_tree.xml")
    refs = {
        tree: [ref.json() for ref in obj.find_refs(doc.xml, structure=obj.units)]
        for tree, obj in doc.citeStructure.items()
    }
    paths = {tree: generate_paths(ref) for tree, ref in refs.items()}
    assert paths == {
        'nums': {
            'I': [0], '1': [1], 'A': [2], '4': [3], 'V': [4]
        },
        None: {
            'I': [0], '1': [1], 'A': [2], '4': [3], 'V': [4]
        },
        'alpha': {
            'div-a1': [0], 'div-002': [1], 'div-xyz': [2], 'div-004': [3], 'div-v5': [4]
        }
    }
    # Second part of the test
    doc = Document(f"{local_dir}/tei/base_tei.xml")
    refs = {
        tree: [ref.json() for ref in obj.find_refs(doc.xml, structure=obj.units)]
        for tree, obj in doc.citeStructure.items()
    }
    paths = {tree: generate_paths(ref) for tree, ref in refs.items()}
    assert paths == {
        None: {
            "Luke": [0],
            "Luke 1": [0, 0],
            "Luke 1:1": [0, 0, 0],
            "Luke 1:2": [0, 0, 1],
            "Luke 1#1": [0, 0, 2],
            "Mark": [1],
            "Mark 1": [1, 0],
            "Mark 1:1": [1, 0, 0],
            "Mark 1:2": [1, 0, 1],
            "Mark 1#1": [1, 0, 2],
            "Mark 1:3": [1, 0, 3]
        }
    }
    assert strip_members(get_member_by_path(refs[None], paths[None]["Luke"])) == {'citeType': 'book', 'ref': 'Luke'}
    assert get_member_by_path(refs[None], paths[None]["Mark 1:3"]) == {'citeType': 'verse', 'ref': 'Mark 1:3'}


def test_navigation():
    doc = Document(f"{local_dir}/tei/base_tei.xml")
    refs = {
        tree: [ref.json() for ref in obj.find_refs(doc.xml, structure=obj.units)]
        for tree, obj in doc.citeStructure.items()
    }
    paths = {tree: generate_paths(ref) for tree, ref in refs.items()}
    assert get_nav(refs[None], paths[None], start_or_ref=None, end=None, down=1) == ([
        {'citeType': 'book', 'ref': 'Luke'},
        {'citeType': 'book', 'ref': 'Mark'}
    ], None, None)
    assert get_nav(refs[None], paths[None], start_or_ref="Luke 1:1", end="Luke 1#1", down=0) == ([
        {'citeType': 'verse', 'ref': 'Luke 1:1'},
        {'citeType': 'verse', 'ref': 'Luke 1:2'},
        {'citeType': 'bloup', 'ref': 'Luke 1#1'}
    ], {'citeType': 'verse', 'ref': 'Luke 1:1'}, {'citeType': 'bloup', 'ref': 'Luke 1#1'})
    assert get_nav(refs[None], paths[None], start_or_ref="Luke 1:1", end="Mark 1:2", down=0) == ([
        {'citeType': 'verse', 'ref': 'Luke 1:1'},
        {'citeType': 'verse', 'ref': 'Luke 1:2'},
        {'citeType': 'bloup', 'ref': 'Luke 1#1'},
        {'citeType': 'verse', 'ref': 'Mark 1:1'},
        {'citeType': 'verse', 'ref': 'Mark 1:2'}
    ], {'citeType': 'verse', 'ref': 'Luke 1:1'}, {'citeType': 'verse', 'ref': 'Mark 1:2'})