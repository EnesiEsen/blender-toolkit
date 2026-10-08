"""Asset names. GTA looks assets up by the hash of the lower-case name, so spaces, capitals and Blender's .001
suffixes break it."""

import re


def asset_name(name):
    """`My Crate.001` -> `my_crate`."""
    base = re.sub(r"\.\d{3}$", "", name).lower()
    base = re.sub(r"[^a-z0-9_]+", "_", base).strip("_")
    return re.sub(r"_+", "_", base) or "asset"


def is_valid(name):
    return name == asset_name(name) and not re.search(r"\.\d{3}$", name)


def unique(name, taken):
    """`crate` -> `crate`, `crate_2`, ... the first one not in `taken`."""
    if name not in taken:
        return name
    n = 2
    while f"{name}_{n}" in taken:
        n += 1
    return f"{name}_{n}"
