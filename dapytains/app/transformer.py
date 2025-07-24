from typing import Dict, Set, Callable
import json
import lxml.etree as et
from flask import Response
from .database import Collection
from dataclasses import field
from saxonche import PySaxonProcessor, PyXsltExecutable



class Transformer(object):
    def __init__(self, supported_media_types: Set[str] = None):
        self.supported_media_types: Set[str] = supported_media_types or set()

    def transform(self, media: str, collection: Collection, document: et.ElementTree) -> Response:
        if media not in self.supported_media_types:
            return Response(json.dumps({"message": f"Unsupported/invalid media type {media}"}), status=403, mimetype="application/json")



class GeneralisticXSLTransformer(Transformer):
    """ A transformer that applies the same XSL for all file using only the media type for transformation scenario

    :param xslts: A dictionary of STR -> PATH where str is a media type and PATH a path to an xslt
    :param media_type_mapping: (Optional) Provides a query media type string (e.g. json) to a correct mimetype (application/json)
    """
    def __init__(self, xslts: Dict[str, str], media_type_mapping: Dict[str, str] = None):
        super().__init__(supported_media_types=set(xslts.keys()))
        self.xslts = xslts
        self.active_xslts: Dict[str, PyXsltExecutable] = {}
        self.mapping: Dict[str, str] = media_type_mapping or {}
        with PySaxonProcessor(license=False) as proc:
            for key, xsl_path in xslts.items():
                try:
                    compiler = proc.new_xslt_compiler()
                    self.active_xslts[key]  = compiler.compile_stylesheet(stylesheet_file=xsl_path)
                except Exception as e:
                    print(f"Error compiling {xsl_path}: {e}")

    def transform(self, media: str, collection: Collection, document: et.ElementTree) -> Response:
        if media not in self.supported_media_types:
            return super().transform(media, collection, document)

        transformer = self.active_xslts[media].load()
        transformer.set_source_text(et.tostring(document, encoding=str))  # Pass XML as string
        result = transformer.transform_to_string()  # or transform_to_value()

        return Response(result, status=200, mimetype=self.mapping.get(media, media))
