
def normalize_flavor(flavor: object) -> str | None:
    if isinstance(flavor, str):
        flavor = flavor.strip().lower()
        if len(flavor) == 0:
            raise KeyError('flavor cannot be empty')
        return flavor

    if flavor is not None:
        raise KeyError(f'illegal flavor type: {type(flavor).__name__!r}')
    return None
