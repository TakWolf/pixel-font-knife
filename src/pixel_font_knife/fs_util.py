import os
from os import PathLike


def is_empty_dir(path: str | PathLike[str]) -> bool:
    items = os.listdir(path)
    if '.DS_Store' in items:
        items.remove('.DS_Store')
    return len(items) == 0
