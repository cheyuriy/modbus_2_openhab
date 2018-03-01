#!/usr/bin/env python3

import logging
import argparse
import os
import codecs
import importlib
from openhab_generators import read_project, build_project

logger = logging.getLogger('modbus_2_openhab')


def main() -> None:
    args = get_args()

    with codecs.open(args.input_file, "r", encoding=args.encoding) as opened_file:
        opened_file_content = opened_file.read()

    requests_spec = None
    controller = importlib.import_module("{}.{}".format("controllers", args.config_type))
    requests_spec = controller.parse(opened_file_content)

    project = read_project(args.project_dir)
    build_project(project, requests_spec)


def get_args():
    argParser = argparse.ArgumentParser(
        description='Process modbus configuration to produce necessary files for openHAB: things, items, sitemap'
    )
    argParser.add_argument('-f',
                           metavar='Modbus config',
                           type=str,
                           dest='input_file',
                           required=True,
                           help='specify file with modbus configuration')
    argParser.add_argument('-t',
                           metavar='configuration type',
                           type=str,
                           dest="config_type",
                           help='specify format type of configuration')
    argParser.add_argument('-e',
                           metavar='used encoding',
                           type=str,
                           dest="encoding",
                           default='cp1251',
                           help='specify encoding of config file with any known charset for Python')
    argParser.add_argument('-p',
                           metavar='directory with project-specific files',
                           type=str,
                           dest="project_dir",
                           help='specify project name to use (should be a subdirectory inside /projects folder)')                       
    args = argParser.parse_args()

    return args


if __name__ == '__main__':
    main()