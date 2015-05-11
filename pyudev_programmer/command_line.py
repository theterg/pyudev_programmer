import argparse
import logging
import sys
import os
import pyudev
import re
from copy import copy
import time
from commands import getstatusoutput
import hub_control
from DFUProcess import DFUProcess
from threading import Event

context = pyudev.Context()

logger = logging.getLogger(__name__)

instances = []
instance_activity = Event()
display = None
gfx = None

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
    parser.add_argument('--OLED', choices=['SSD1331'],
            help='Display status on external OLED display (Raspberry Pi Only)')

    return parser.parse_args()


def clear_instance(p):
    try:
        instances.remove(p)
    except ValueError:
        return

def draw_update():
    if display is not None and gfx is not None:
        gfx.clearLines(11, 64)
        instances_copy = copy(instances)
        for idx in range(0, len(instances_copy)):
            p = instances_copy[idx]
            if p.returncode is None:
                gfx.drawText((0, ((5-idx)*10)),
                    '%s:%d%%' % (p.serial, p.progress), (255,255,255))
            elif p.returncode:
                gfx.drawText((0, ((5-idx)*10)),
                    '%s:%d%%' % (p.serial, p.progress), (255,0,0))
            else:
                gfx.drawText((0, ((5-idx)*10)),
                    '%s:%d%%' % (p.serial, p.progress), (0,255,0))
        gfx.display()
            

def instance_update(p, progress, complete, error):
    if complete:
        # Find the entry in the list
        if error:
            logging.error('Error uploading to device %s: %s', p.serial, p.last_error)
            logging.debug('Dump from last failure: %s' % ('\n'.join(p.line_log)))
        else:
            logging.info('Device %s successfully updated', p.serial)
        draw_update()
    if complete or error:
        clear_instance(p)
        # Attempt to remove self from list in 60 seconds
        # Timer(60.0, clear_instance, p)
    # Inform "UI thread" that an update is available
    instance_activity.set()
    #if blink_led
    #    if hub is not None:
    #        hub_control.control_led(hub, int(device['DEVPATH'][-1]), 0)

def deploy_firmware(device, vendor, model, filename, alt):
    #if blink_led:
    #    hub = hub_control.find_hub(int(device.parent['ID_VENDOR_ID'], 16),
    #            int(device.parent['ID_MODEL_ID'], 16))
    #    if hub is not None:
    #        hub_control.control_led(hub, int(device['DEVPATH'][-1]), 1)
    #    else:
    #        logging.warn("Cannot find hub or hub doesn't support indication")
    logging.info('Deploying firmware to %s' % device['ID_SERIAL_SHORT'])
    p = DFUProcess('dfu-util -nR -a %d -S %s -D %s' %\
            (alt, device['ID_SERIAL_SHORT'], filename),
            serial=device['ID_SERIAL_SHORT'], prog_callback=instance_update)
    instances.append(p)

def get_real_basename(filename):
    if os.path.islink(filename):
        p = os.readlink(filename)
        if os.path.isabs(p):
            return os.path.basename(p)
        return os.path.basename(os.path.join(os.path.dirname(filename), p))
    else:
        return os.path.basename(filename)

def main():
    global display
    global gfx
    args = parse_arguments()
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
        logger.debug('Debug level enabled')
    else:
        logging.basicConfig(level=logging.INFO)
    if args.OLED is not None:
        print 'Importing '+str(args.OLED)
        if args.OLED == 'SSD1331':
            from SSD1331 import SSD1331, PILGFX
            display = SSD1331()
            gfx = PILGFX(display)
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
            logging.debug('Found a new DFU device %s' % str(device))
            deploy_firmware(device, args.vendor, args.model, args.file, args.alt)

    observer = pyudev.MonitorObserver(monitor, found_device)
    observer.start()
    logging.info('Now listening for devices, press Ctrl-C to exit')
    while(True):
        instance_activity.wait(1.0)
        if instance_activity.isSet():
            statusmsg = []
            for i in range(len(instances)):
                p = instances[i]
                if p.returncode is not None:
                    clear_instance(p)
                statusmsg.append('%s: %d%% ' % (p.serial, p.progress))
                draw_update()
            # Print status to screen!
            sys.stdout.write('\r'+''.join(statusmsg))
            sys.stdout.flush()
        # Rate limit the console output
        time.sleep(0.2)
        if display is not None and gfx is not None:
            gfx.drawText((0,0), get_real_basename(args.file), (255,255,255))
            gfx.display()

if __name__ == '__main__':
    main()
