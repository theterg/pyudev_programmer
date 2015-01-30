import argparse
import logging
import sys
import pyudev
import re
import threading
import usb.core
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

def find_parent_hub(device):
    vendor = int(device.parent['ID_VENDOR_ID'], 16)
    product = int(device.parent['ID_MODEL_ID'], 16)
    hub = usb.core.find(bDeviceClass=usb.CLASS_HUB, idVendor=vendor, idProduct=product)
    if hub is None:
        return None
    port = (usb.TYPE_CLASS | usb.RECIP_DEVICE)
    dir = 0x80 # USB_DIR_IN
    desc = hub.ctrl_transfer(dir | port,
                                 usb.REQ_GET_DESCRIPTOR,
                                 wValue = usb.DT_HUB << 8,
                                 wIndex = 0,
                                 data_or_wLength = 1024, timeout = 1000)
    if not desc:
        return None
    logging.debug("Got desc: "+str(desc))
    return hub

def set_led_on_hub(hub, port, led):
    request = usb.REQ_SET_FEATURE
    feature = 22 # USB_PORT_FEAT_INDICATOR
    port_type = (usb.TYPE_CLASS | usb.RECIP_OTHER)
    index = (led << 8) | port
    hub.ctrl_transfer(port_type, request, wValue=feature, wIndex=index, data_or_wLength=None, timeout=1000)

def deploy_firmware(device, vendor, model, filename, alt):
    t = threading.Thread(target=firmware_deploy_thread, args=(device, alt, filename))
    t.start()

def firmware_deploy_thread(device, alt, filename):
    hub = find_parent_hub(device)
    port = int(device['DEVPATH'][-1])
    if hub is not None:
        set_led_on_hub(hub, port, 1)
    logging.info('Deploying firmware to '+device['ID_SERIAL_SHORT'])
    code, ret = getstatusoutput('dfu-util -nR -a %d -S %s -D %s' % (alt, device['ID_SERIAL_SHORT'], filename))
    logging.debug(ret)
    if hub is not None:
        set_led_on_hub(hub, port, 0)


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
