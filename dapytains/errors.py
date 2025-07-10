class UnknownTreeName(Exception):
    """This exception is raised when a requested tree is unknown """

class InvalidRangeOrder(Exception):
    """Error raised when a range is in the wrong order (start > end) """