import argparse
import logging
import sys

logger = logging.getLogger(__name__)

def parse_arguments():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-v', '--verbose', action='store_true', default=False,
            help='Print debug information to screen')

    return parser.parse_args()

def main():
    args = parse_arguments()
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
        logger.debug('Debug level enabled')
    else:
        logging.basicConfig(level=logging.INFO)
    logging.info('Start')
    sys.exit(0)

if __name__ == '__main__':
    main()
