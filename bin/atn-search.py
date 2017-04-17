#!/usr/bin/env python3

"""
TODO
"""

import sys
import argparse
import json

from atntools import searchprocess

parser = argparse.ArgumentParser(description=globals()['__doc__'])
subparsers = parser.add_subparsers(dest='subparser_name')

parser_generate = subparsers.add_parser('start', help="Start a new search sequence")
parser_generate.add_argument('food_web_id', help="Food web ID")
parser_generate.add_argument('metaparameter_template', help="Template for metaparameters.json")

parser_regenerate = subparsers.add_parser('iterate', help="Run a search iteration")
parser_regenerate.add_argument('sequence_num', type=int, help="Search sequence number")

args = parser.parse_args()

if not args.subparser_name:
    # No sub-command given
    parser.print_usage()
    sys.exit(1)

if args.subparser_name == 'start':
    with open(args.metaparameter_template) as f:
        metaparameter_template = json.load(f)
    searchprocess.start_sequence(args.food_web_id, metaparameter_template)

elif args.subparser_name == 'iterate':
    searchprocess.do_iteration(args.sequence_num)
