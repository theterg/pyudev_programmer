import argparse
import logging
import sys
import pyudev
import re
from commands import getstatusoutput

context = pyudev.Context()

logger = logging.getLogger(__name__)

def parse_arguments():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-v', '--verbose', action='store_true', default=False,
            help='Print debug information to screen')
    parser.add_argument('--vendor', type=str, default='0483',
            help='The USB vendor ID to search for')
    parser.add_argument('--model', type=str, default='df11',
            help='The USB model ID to search for')
    parser.add_argument('--alt', type=int, default=0,
            help='The the Altsetting of the DFU interface (default is usually ok)')
    parser.add_argument('file', type=str,
            help='The DFU firmware file to deploy')

    return parser.parse_args()

def deploy_firmware(device, vendor, model, filename, alt):
    code, ret = getstatusoutput('dfu-util -a %d -D %s' % (alt, filename))
    logging.debug(ret)
    return code

def main():
    args = parse_arguments()
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
        logger.debug('Debug level enabled')
    else:
        logging.basicConfig(level=logging.INFO)
    logging.info('Start')
    existing_devs = list(context.list_devices(subsystem='usb', ID_VENDOR_ID=args.vendor,
        ID_MODEL_ID=args.model))
    logging.info('Found %d existing devices: %s' % (len(existing_devs), str(existing_devs)))
    for device in existing_devs:
        deploy_firmware(device, args.vendor, args.model, args.file, args.alt)
    monitor = pyudev.Monitor.from_netlink(context)
    monitor.filter_by('usb')

    def found_device(action, device):
        logging.debug('%s for %s' % (str(action), str(device)))
        if action != 'add':
            return
        if 'ID_VENDOR_ID' in device and device['ID_VENDOR_ID'] == args.vendor and\
                'ID_MODEL_ID' in device and device['ID_MODEL_ID'] == args.model:
            logging.info('Found a new DFU device %s' % str(device))
            deploy_firmware(device, args.vendor, args.model, args.file, args.alt)

    observer = pyudev.MonitorObserver(monitor, found_device)
    observer.start()
    _ = input('press a key to exit')

if __name__ == '__main__':
    main()
