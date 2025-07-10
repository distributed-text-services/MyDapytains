import flask
from dapytains.app.navigation import get_member_by_path, strip_members, generate_paths, get_nav
from dapytains.tei.document import Document
import os


local_dir = os.path.join(os.path.dirname(__file__))


def test_simple_path():
    """Check that a document can be parsed and that path are corrects"""
    doc = Document(f"{local_dir}/tei/multiple_tree.xml")
    refs = {
        tree: [ref.json() for ref in doc.get_reffs(tree)]
        for tree, obj in doc.citeStructure.items()
    }
    paths = {tree: generate_paths(ref) for tree, ref in refs.items()}
    assert paths == {
        'nums': {
            'I': [0], '1': [1], 'A': [2], '4': [3], 'V': [4]
        },
        'alpha': {
            'div-a1': [0], 'div-002': [1], 'div-xyz': [2], 'div-004': [3], 'div-v5': [4]
        }
    }
    # Second part of the test
    doc = Document(f"{local_dir}/tei/base_tei.xml")
    refs = {
        tree: [ref.json() for ref in doc.get_reffs(tree)]
        for tree, obj in doc.citeStructure.items()
    }
    paths = {tree: generate_paths(ref) for tree, ref in refs.items()}
    assert paths == {
         "default": {
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
    assert strip_members(
        get_member_by_path(refs[doc.default_tree], paths[doc.default_tree]["Luke"])
    ) == {'citeType': 'book', 'identifier': 'Luke', "level": 1, "parent": None}, "Check that members are stripped"
    assert get_member_by_path(
        refs[doc.default_tree], paths[doc.default_tree]["Mark 1:3"]
    ) == {'citeType': 'verse', 'identifier': 'Mark 1:3', "level": 3, "parent": "Mark 1"}


def test_navigation():
    doc = Document(f"{local_dir}/tei/base_tei.xml")
    refs = {
        tree: [ref.json() for ref in obj.find_refs(doc.xml, structure=obj.structure)]
        for tree, obj in doc.citeStructure.items()
    }
    paths = {tree: generate_paths(ref) for tree, ref in refs.items()}

    assert get_nav(
        refs[doc.default_tree],
        paths[doc.default_tree],
        start_or_ref=None,
        end=None,
        down=1
    ) == ([
        {'@type': 'CitableUnit', 'citeType': 'book', 'identifier': 'Luke', "level": 1, "parent": None},
        {'@type': 'CitableUnit', 'citeType': 'book', 'identifier': 'Mark', "level": 1, "parent": None}
    ], None, None), "Check that base function works"

    assert get_nav(refs[doc.default_tree], paths[doc.default_tree], start_or_ref="Luke 1:1", end="Luke 1#1", down=0) == (
        [
            {'@type': 'CitableUnit', 'citeType': 'verse', 'identifier': 'Luke 1:1', "level": 3, "parent": "Luke 1"},
            {'@type': 'CitableUnit', 'citeType': 'verse', 'identifier': 'Luke 1:2', "level": 3, "parent": "Luke 1"},
            {'@type': 'CitableUnit', 'citeType': 'bloup', 'identifier': 'Luke 1#1', "level": 3, "parent": "Luke 1"}
        ],
        {'@type': 'CitableUnit', 'citeType': 'verse', 'identifier': 'Luke 1:1', "level": 3, "parent": "Luke 1"},
        {'@type': 'CitableUnit', 'citeType': 'bloup', 'identifier': 'Luke 1#1', "level": 3, "parent": "Luke 1"}
    ), "Check that ?start/end works"

    assert get_nav(refs[doc.default_tree], paths[doc.default_tree], start_or_ref="Luke 1:1", end="Mark 1:2", down=0) == (
        [
            {'@type': 'CitableUnit', 'citeType': 'verse', 'identifier': 'Luke 1:1', "level": 3, "parent": "Luke 1"},
            {'@type': 'CitableUnit', 'citeType': 'verse', 'identifier': 'Luke 1:2', "level": 3, "parent": "Luke 1"},
            {'@type': 'CitableUnit', 'citeType': 'bloup', 'identifier': 'Luke 1#1', "level": 3, "parent": "Luke 1"},
            {'@type': 'CitableUnit', 'citeType': 'verse', 'identifier': 'Mark 1:1', "level": 3, "parent": "Mark 1"},
            {'@type': 'CitableUnit', 'citeType': 'verse', 'identifier': 'Mark 1:2', "level": 3, "parent": "Mark 1"}
        ],
        {'@type': 'CitableUnit', 'citeType': 'verse', 'identifier': 'Luke 1:1', "level": 3, "parent": "Luke 1"},
        {'@type': 'CitableUnit', 'citeType': 'verse', 'identifier': 'Mark 1:2', "level": 3, "parent": "Mark 1"}
    ), "Check that ?start/end works across parents"

    assert get_nav(refs[doc.default_tree], paths[doc.default_tree], start_or_ref="Luke 1", down=1) == (
        [
            {'@type': 'CitableUnit', 'citeType': 'chapter', 'identifier': 'Luke 1', "level": 2, "parent": "Luke"},
            {'@type': 'CitableUnit', 'citeType': 'verse', 'identifier': 'Luke 1:1', "level": 3, "parent": "Luke 1"},
            {'@type': 'CitableUnit', 'citeType': 'verse', 'identifier': 'Luke 1:2', "level": 3, "parent": "Luke 1"},
            {'@type': 'CitableUnit', 'citeType': 'bloup', 'identifier': 'Luke 1#1', "level": 3, "parent": "Luke 1"}
        ],
        {'@type': 'CitableUnit', 'citeType': 'chapter', 'identifier': 'Luke 1', "level": 2, "parent": "Luke"},
        None
    ), "Check that ?ref works"

    assert get_nav(refs[doc.default_tree], paths[doc.default_tree], start_or_ref="Luke", down=1) == (
        [
            {'@type': 'CitableUnit', 'citeType': 'book', 'identifier': 'Luke', "level": 1, "parent": None},
            {'@type': 'CitableUnit', 'citeType': 'chapter', 'identifier': 'Luke 1', "level": 2, "parent": "Luke"},
        ],
        {'@type': 'CitableUnit', 'citeType': 'book', 'identifier': 'Luke', "level": 1, "parent": None},
        None
    ), "Check that ?ref works"

    assert get_nav(refs[doc.default_tree], paths[doc.default_tree], start_or_ref=None, end=None, down=2) == (
        [
            {'@type': 'CitableUnit', 'citeType': 'book', 'identifier': 'Luke', "level": 1, "parent": None},
            {'@type': 'CitableUnit', 'citeType': 'chapter', 'identifier': 'Luke 1', "level": 2, "parent": "Luke"},
            {'@type': 'CitableUnit', 'citeType': 'book', 'identifier': 'Mark', "level": 1, "parent": None},
            {'@type': 'CitableUnit', 'citeType': 'chapter', 'identifier': 'Mark 1', "level": 2, "parent": "Mark"}
        ],
        None,
        None
    ), "Check that down=2 works"