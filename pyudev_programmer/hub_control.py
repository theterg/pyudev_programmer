#! /usr/bin/python2

"""
hub_ctrl.py - a tool to control port power/led of USB hub

Copyright (C) 2006, 2011 Free Software Initiative of Japan

Author: NIIBE Yutaka  <gniibe@fsij.org>

This file is a part of Gnuk, a GnuPG USB Token implementation.

Gnuk is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Gnuk is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public
License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

Modified 2014 Paul Adams - updated to be compatible with pyusb 1.0.0b1
Modified 2015 Andrew Tergis - trimmed away all but critical functionality
  for LED indication
"""

import usb.core

COMMAND_SET_NONE = 0
COMMAND_SET_LED = 1
COMMAND_SET_POWER = 2
HUB_LED_GREEN = 2

USB_RT_HUB = (usb.TYPE_CLASS | usb.RECIP_DEVICE)
USB_RT_PORT	= (usb.TYPE_CLASS | usb.RECIP_OTHER)
USB_PORT_FEAT_RESET	= 4
USB_PORT_FEAT_POWER	= 8
USB_PORT_FEAT_INDICATOR = 22
USB_DIR_IN = 0x80		 # device to host

COMMAND_SET_NONE = 0
COMMAND_SET_LED = 1
COMMAND_SET_POWER = 2

HUB_LED_GREEN = 2


def find_hub(vendor, product, timeout=1000):
    dev = usb.core.find(idVendor=vendor, idProduct=product)
    if dev is None:
        return None
    desc = dev.ctrl_transfer(USB_DIR_IN | USB_RT_HUB,
                             usb.REQ_GET_DESCRIPTOR,
                             wValue=usb.DT_HUB << 8,
                             wIndex=0,
                             data_or_wLength=1024, timeout=timeout)
    # We need to be able to read the device descriptor to tell if
    # it supports the indication feature
    if not desc:
        return None
    # Check bit for LED indication control
    if (desc[3] & 0x80) == 0:
        return None
    return dev

def control_led(device, port, value):
    request = usb.REQ_SET_FEATURE
    feature = USB_PORT_FEAT_INDICATOR
    index = (value << 8) | port

    return device.ctrl_transfer(USB_RT_PORT, request, wValue=feature,
            wIndex=index, data_or_wLength=None, timeout=1000)
