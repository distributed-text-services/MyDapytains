MyDapytains
===========

*The name of the library is completely temporary*.

This library offers a base python implementation of the following functionalities:

- Parsing of machine-actionable citeStructure and citeData to retrieve reference, structure and citable unit metadata within a TEI file 
- Reuse of citeStructure architecture to retrieve and build partial documents, based on provided reference.
- Support for multiple citeStructure, similar to the ?tree parameter of the DTS Specifications.

This library will:

- Provide a base implementation of the DTS API, using python as a server-side language
- Provide some light "caching" features, to avoid reparsing document at query time.

## ToDo

- Support XSL transformation with mediaType dictionary for outputting different data
- Add tests to webapp


## WebApp

You can try the webapp using `python -m dapitains.app.app`. It uses test files at the moment.

## Guidelines

### Document level guidelines

1. For TEI document to be accessible in full, no specific requirements are necessary.
2. For TEI document to have a single citation tree, they must provide at least one element 
   at the XPath `/TEI/teiHeader/encodingDesc/refsDecl[@default='true']/citeStructure`.
3. For TEI document to have multiple citation trees, they must provide at least one element 
   at the XPath `/TEI/teiHeader/encodingDesc/refsDecl[@default='true']/citeStructure` and any number of element matching
   the XPath `/TEI/teiHeader/encodingDesc/refsDecl[@n]/citeStructure`, where `@n` holds the citation tree name.

We are currently figuring out the Resource level metadata.

See one of our test files to check out the minimal requirements: we have one 
[with citeData](./tests/tei/test_citeData_two_levels.xml) and one [with multiple trees](./tests/tei/multiple_tree.xml)

### Collection and Resource level guidelines

Collection and Resource level guidelines can be provided through file named dts-metadata.xml in each subfolder of a 
given repository. We are currently looking at using external file that would help you ingest metadata, while leaving you
the option to load up metadata yourself.

The current schema for the collection catalog ingestion is available in [./tests/catalog/schema.rng](./tests/catalog/schema.rng).