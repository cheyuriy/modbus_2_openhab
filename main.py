#!/usr/bin/env python3

import logging
import argparse

logger = logging.getLogger('modbus_2_openhab')


def main() -> None:
    """
    Loads file with specified type of controller and starts parsing
    :return: None
    """

    args = get_args()

    print(args.input_file)
    print(args.config_type)


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
                           choices=['segnetics'],
                           default='segnetics',
                           help='specify format type of configuration')
    args = argParser.parse_args()

    return args


if __name__ == '__main__':
    main()