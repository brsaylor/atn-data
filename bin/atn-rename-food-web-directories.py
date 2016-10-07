#!/usr/bin/env python3

import os
import sys

from atntools import foodwebs


if len(sys.argv) < 2:
    print("Renames the given food web directories from species-ID-based names\n"
          + "to node-ID-based names.", file=sys.stdout)
    print("Usage: atn-rename-food-web-directories.py DIR [DIR]...", file=sys.stdout)
    sys.exit(1)

serengeti = foodwebs.read_serengeti()
id_map = foodwebs.species_node_id_map(serengeti)

for old_dir in sys.argv[1:]:
    species_ids = [int(x) for x in old_dir.split('-')]
    node_ids = [id_map[x] for x in species_ids]
    new_dir = '-'.join(map(str, sorted(node_ids)))
    print("Renaming  {}  to  {}".format(old_dir, new_dir))
    os.rename(old_dir, new_dir)