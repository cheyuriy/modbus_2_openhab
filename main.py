#!/usr/bin/env python3

import argparse
import os
import codecs
import importlib
import logging
import itertools
from ruamel.yaml import YAML
from openhab_generators import read_project, build_project
from config import config

def main() -> None:
    if config['general']['verbose_logging']:
        logging.basicConfig(level=logging.INFO)
    logging.info("Started modbus2openhab")

    args = get_args()

    # opening modbus configuration file with specified encoding (see command line arguments)
    with codecs.open(args.input_file, "r", encoding=args.encoding) as opened_file:
        logging.info("Opening modbus config file: {}".format(args.input_file))
        opened_file_content = opened_file.read()

    # parsing modbus configuration file, using parsing module in 'controllers' directory
    # name of the module must correspond to provided argument (see command line arguments)
    # every parsing module must provide function 'parse', which receives content of modbus configuration file 
    # and returns dict with modbus requests, addresses, types and native names  
    requests_spec = None
    parsing_module_name = "{}.{}".format("controllers", args.config_type)
    logging.info("Loading controller-specific module for parsing modbus config: {}".format(parsing_module_name))
    controller = importlib.import_module(parsing_module_name)
    logging.info("Parsing modbus config")
    requests_spec = controller.parse(opened_file_content)
    logging.info("Parsed config consists of {} requests".format(len(requests_spec.keys())))

    # there must be subdirectory in 'projects' directory with the same name as provided project name (see command line arguments)
    # project directory must contain map.yaml and site.yaml files, which describes OpenHab's structure
    # building project based on project's structure and parsed modbus configuration
    build_project(args.project, requests_spec)
    logging.info("Done")


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
                           dest="project",
                           help='specify project name to use (should be a subdirectory inside /projects folder)')                       
    args = argParser.parse_args()

    return args


if __name__ == '__main__':
    main()