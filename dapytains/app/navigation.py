from typing import List, Dict, Any, Optional, Tuple
from dapytains.errors import InvalidRangeOrder


def get_member_by_path(data: List[Dict[str, Any]], path: List[int]) -> Optional[Dict[str, Any]]:
    """
    Retrieve the member at the specified path in the nested data structure.

    :param data: The nested data structure (list of dictionaries).
    :param path: A list of indices that represent the path to the desired member.
    :return: The member at the specified path, or None if the path is invalid.
    """
    current_level = data

    path_copy = [] + path
    while path_copy:
        index = path_copy.pop(0)
        try:
            current_level = current_level[index]
            if 'members' in current_level and path_copy:
                current_level = current_level['members']
        except (IndexError, KeyError):
            return None

    return current_level


def strip_members(obj: Dict[str, Any], add_type: bool = False) -> Dict[str, Any]:
    obj = {k: v for k, v in obj.items() if k != "members"}
    if add_type:
        obj["@type"] = "CitableUnit"
    return obj


def generate_paths(data: List[Dict[str, Any]], path: Optional[List[int]] = None) -> Dict[str, List[int]]:
    """
    Generate a dictionary mapping each 'ref' in a nested data structure to its path.

    The path is represented as a list of indices that show how to access each 'ref'
    in the nested structure.

    :param data: The nested data structure (list of dictionaries). Each dictionary
                 can have a 'ref' and/or 'members' key.
    :param path: A list of indices representing the current path in the nested data
                 structure. Used internally for recursion. Defaults to None for the
                 initial call.
    :return: A dictionary where each key is a 'ref' and each value is a list of indices
             representing the path to that 'ref' in the nested structure.
    """
    if path is None:
        path = []

    paths = {}

    def recurse(items, current_path):
        for index, item in enumerate(items):
            ref = item.get('identifier')
            if ref:
                # Record the path for the current reference
                paths[ref] = current_path + [index]

            members = item.get('members')
            if members:
                # Recurse into the 'members' list
                recurse(members, current_path + [index])

    recurse(data, [])
    return paths


def get_nav(
        refs: List[Dict[str, Any]],
        paths: Dict[str, List[int]],
        start_or_ref: Optional[str] = None,
        end: Optional[str] = None,
        down: Optional[int] = 1
) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """ Given a references set and a path set, provide the CitableUnit from start to end at down level.

    """

    paths_index = list(paths.keys())
    start_index, end_index = None, len(paths_index)

    if end:
        # For end, as end is inclusive, we check for the last partial match
        #   (ie, if Mark is [1], we want everything starting
        #   by [1].)
        end_index = paths_index.index(end)
        len_end = len(paths[end])
        for idx, reference in enumerate(paths_index[end_index+1:]):
            if paths[reference][:len_end] == paths[end]:
                end_index = end_index+idx
            else:
                break

    if start_or_ref:
        start_index = paths_index.index(start_or_ref)
        if not end:
            if down == 0:
                end_index = len(paths_index)
            else:
                for index, reference in enumerate(paths_index[start_index+1:]):
                    if len(paths[start_or_ref]) == len(paths[reference]):
                        end_index = index + start_index
        if start_index > end_index:
            raise InvalidRangeOrder

    paths = dict(list(paths.items())[start_index:end_index+1])

    current_level = []
    start_path, end_path = None, None
    if start_or_ref:
        start_path = paths[start_or_ref]
        current_level.append(len(start_path))
    if end:
        end_path = paths[end]
        current_level.append(len(end_path))

    current_level = max(current_level) if current_level else 0

    if down == 0:
        paths = {key: value for key, value in paths.items() if len(value) == current_level}
    elif down == -1:
        paths = {key: value for key, value in paths.items() if current_level <= len(value)}
    else:
        paths = {key: value for key, value in paths.items() if current_level <= len(value) <= down + current_level}

    return (
        [
            strip_members(get_member_by_path(refs, path), add_type=True) for path in paths.values()
        ],
        strip_members(get_member_by_path(refs, start_path), add_type=True) if start_path else None,
        strip_members(get_member_by_path(refs, end_path), add_type=True) if end_path else None
    )
