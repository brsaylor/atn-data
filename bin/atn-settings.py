#!/usr/bin/env python3

""" Prints configuration property-value pairs.

Access properties in shell scripts by including
eval $(atn-settings.py)
at the top of the script.
"""

from atntools import settings

settings.print_configuration()
