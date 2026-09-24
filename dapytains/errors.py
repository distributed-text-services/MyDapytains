class UnknownTreeName(Exception):
    """This exception is raised when a requested tree is unknown """

class InvalidRangeOrder(Exception):
    """Error raised when a range is in the wrong order (start > end) """


class UnresolvableReference(ValueError):
    """Error raised when a reference matches no node of the document: it does not exist, or one of
    its units only exists under a later occurrence of a repeated milestone parent (e.g. a column the
    text comes back to), which resolution, following the first occurrence, cannot reach. """

    def __init__(self, reference: str):
        self.reference = reference
        super().__init__(f"Reference '{reference}' cannot be resolved to a node of the document.")
