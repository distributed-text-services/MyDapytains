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

## Guidelines

### Document level guidelines

1. For TEI document to be accessible in full, no specific requirements are necessary.
2. For TEI document to have a single citation tree, they must provide at least one element 
   at the XPath `/TEI/teiHeader/encodingDesc/refsDecl[@default='true']/citeStructure`.
3. For TEI document to have multiple citation trees, they must provide at least one element 
   at the XPath `/TEI/teiHeader/encodingDesc/refsDecl[@default='true']/citeStructure` and any number of element matching
   the XPath `/TEI/teiHeader/encodingDesc/refsDecl[@n]/citeStructure`, where `@n` holds the citation tree name.

We are currently figuring out the Resource level metadata.

### Collection and Resource level guidelines

Collection and Resource level guidelines can be provided through file named dts-metadata.xml in each subfolder of a 
given repository. We are currently looking at the reuse of former [Capitains V2 guidelines](https://github.com/Capitains/guidelines/blob/edde0323c2e94b3d0d687094e55cb32cac548752/capitains.rng)

