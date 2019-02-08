#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This script automatically re-writes sectors where
ATA read errors occur. By re-writing the sectors
(using hdparm), the HDD/SSD will be used to re-allocate
the sectors.

**EXTREMELY DANGEROUS**
This script will NOT ask before overwriting data
and might DESTROY all your data. Use it under your
own responsibility and only if you know EXACTLY
what you're doing (or if you don't care).
Expect fixhdd.py to contain critical bugs.

Runs on linux only. hdparm must be installed.

fixhdd.py must be run as root. It will only write to sectors
if reading them using hdparm yields an error.

Use fixhdd.py --loop to watch the syslog for read errors
and rewrite all sectors where errors occur. The script will
check the log every five seconds and won't exit.

Use fixhdd.py -a -o <offset> to scan for bad blocks starting at
LBA <offset>. Use this mode if a SMART selftest indicates an error
at a specific LBA and select an offset smaller than the given LBA.
Scanning a large number of LBAs takes a significant amount of time,
especially if many LBAs yield errors.

Use fixhdd -s <sector> to rewrite a specific LBA, but only
if reading it . Use this for correcting errors indicated by SMART
if you don't see the need for actively scanning a significant number
of blocks.

Use Ctrl+C to stop fixhdd.py.

Changelog:
    Revision 1.1: Fix --loop causing unary function to be called without arguments
    Revision 1.2: Fix hardcoded /dev/sda, various small improvements & fixes ; fix active scan
    Revision 1.3: Python3 ready
    Revision 1.4: Python3 fixes, fix bad/missing sense data & unusable logging
"""
import subprocess
import time
import os
import stat
import sys

__author__ = "Uli Köhler"
__copyright__ = "Copyright 2015-2016 Uli Koehler"
__license__ = "Apache License v2.0"
__version__ = "1.4"
__maintainer__ = "Uli Köhler"
__email__ = "ukoehler@techoverflow.net"
__status__ = "Development"


DISCLAIMER = '''
===========================[ WARNING ]===========================

	DON'T RUN THIS SCRIPT IF YOU ARE AFFRAID OF
			LOOSING DATA!

	This script WILL erase data found on bad sectors on the
disk. Even if the sector can still be partially read, it WILL
BE ERASED and the partial data in said sector WILL BE LOST!

	The aim of this script is to recover a DISK to a usable
state, NOT TO RECOVER DATA!!

        Sometimes, is still possible to retrieve the data in a
bad sector, which this script WON'T attempt to do!!

	This script will overwrite any reported bad sectors with
ZERO bytes (0), forcing the hard driver controller to remap the
sector to a spare pool of sectors reserved by the manufacture for
this purpose. After a susccesfull remap, the sector will work as
if nothing happened, and in most cases, the disk just keep working
normally again, without weird slow dows. I had disks that worked
for years after "fixing" bad sectors this way. (They are still
working to this date - Feb/2019)

	BE CAREFULL!! This method of fixing bad sectors can (and 
probably will) render a filesystem in the disk unnaccessible 
denpending on the filesystem used. XFS, Ext4 and ZFS are remarkable
filesystems, and I was able to fix these filesystem after running 
this script, most of the times, by running a checkdisk utility
xfs_repair, fsck, scrub, etc), with minimal to none lost of files.
For the times I couldn't fix, I didn't had important data on the
disks, so I just reformated then and kept using.

	For disks in RAID5/6 or ZFS ZRAID1/2 it's fairly safe to 
use this script, since the RAID/ZRAID system will re-create the 
lost data in said sector. In this case, make sure to run a disk 
scrub after running this script on a disk and before trying to 
run on another one.

        THE AUTHOR/CONTRIBUTOR(S) OF THIS SCRIPT HAVE NO
          RESPONSABILITY ABOUT ANY LOSS OF DATA CAUSED
           BY THIS SCRIPT! USE IT AT YOUR OWN RISK!
             BY ANSWERING "Yes" BELLOW, YOU AGREE
                    WITH THIS DISCLAIMER!!

===========================[ WARNING ]===========================\n
'''

DISCLAIMER2 = '''
=====================[ EVEN MORE WARNING!! ]======================\n
	USING '--loop all' IS VERY DANGEROUS IN ANY CASE,
	       INCLUDING RAID AND ZRAID!!!!!!!!

	'--loop all' WILL SCAN AND FIX ALL DISKS!! THIS MEANS
	IT  CAN ERASE DATA ON MULTIPLE DISKS ON A RAID/ZRAID
	   AT THE SAME TIME, MAKING IT IMPOSSIBLE FOR THE
	    RAID/ZRAID REPAIR MECHANISMS TO RECONSTRUCT
	                     LOST DATA!!!

	ONLY USE '--loop all' IF YOU KNOWN WHAT YOU DOING AND
	          ARE NOT AFFRAID TO LOOSE DATA!!

=================[ SERIOUSLY... BE CAREFULL MAN!! ]=================\n

Are you REALLY sure you want to run with '--loop all'? (Yes I am sure!/No) '''


#Get list of recent bad sectors via dmesg
def getBadSectors(device):
    "Parse a list of recently read bad sectors from the syslog"
    #TODO this gets ALL bad sectors from ALL devices, not only the selected device
    try:
        out = str(subprocess.check_output('egrep "end_request: I/O error|print_req_error: I/O error" /var/log/syslog | grep %s' % device.split('/')[-1], shell=True))
        for line in out.replace('\\n','\n').replace("'",'').split("\n"):
            line = line.strip()
            if not line: continue
            sector = int(line.rpartition(" ")[2])
            yield sector
    except subprocess.CalledProcessError:
        #usually this indicates grep has not found anything
        return


def isSectorBad(device, sector):
    try:
        output = subprocess.check_output('hdparm --read-sector %d %s' % (sector, device), shell=True, stderr=subprocess.STDOUT)
        output = output.decode("utf-8")
        # Special case: process succeeds but with error message:
        # SG_IO: bad/missing sense data
        if "bad/missing sense data" in output:
            return True
        # Else: Success => sector is not bad
        return False
    except:
        return True


def resetSectorHDParm(device, sector):
    """Write to a sector using hdparm only if reading it yields a HDD error"""
    #Will throw exception on non-zero exit code
    if isSectorBad(device, sector):
        print(("Sector %d (%s) is damaged, rewriting..." % (sector, device)))
        #Maaan, this is VERY DANGEROUS!
        #Really, no kidding. Might even make things worse.
        #It could work, but it probably doesn't. Ever.
        #Don't use if your data is worth a single dime to you.
	#ps from hradec: If your disk is in a ZFS ZRAID, don't worry... running a scrub after fixing the bad sector
        #                will re-create any lost data on the disk. Just don't do it in more than one disk at a time, 
        #                and allways run scrub before attempting another disk!
        out = subprocess.check_output('hdparm --write-sector  %d --yes-i-know-what-i-am-doing %s' % (sector, device), shell=True)
        out = out.decode("utf-8")
        if "succeeded" not in out:
            print (red(out.decode("utf-8").replace("\n")))
    else:
        print(("Sector %d (%s) is OK, ignoring" % (sector,device)))
  
def fixBadSectors(device, badSectors):
    "One-shot fixing of bad sectors"
    print(("Checking/Fixing %d sectors" % len(badSectors)))
    [resetSectorHDParm(device, sector) for sector in badSectors]
      
def checkDmesgBadSectors(device, knownGoodSectors, feedback=True):
    #Grab sector list from dmesg
    devices=device
    if type(device) != type([]):
        devices=[device]

    for device in devices:
       dmesgBadSectors = set(getBadSectors(device))
       dmesgBadSectors.difference_update(knownGoodSectors)
       if len(dmesgBadSectors) == 0:
           if feedback == True:
               print ("No new sector errors found in syslog for device %s:-)" % device)
       else:
           #Update set of sectors which are known to be good
           fixBadSectors(device, dmesgBadSectors)
           knownGoodSectors.update(dmesgBadSectors)

def loopCheckForBadSectors(device, feedback=True):
    knownGoodSectors = set()
    devices=device
    if type(device) != type([]):
        devices=[device]
    while True:
        if feedback == True:
            print("Waiting 5 seconds (hit Ctrl+C to interrupt)...")
        time.sleep(5)
        #Try again after timeout
        for device in devices:
            checkDmesgBadSectors(device, knownGoodSectors, feedback)

def isBlockDevice(filename):
    "Return if the given filename represents a valid block device"
    return stat.S_ISBLK(os.stat(filename).st_mode)

def getNumberOfSectors(device):
    "Get the physical number of LBAs for the given device"
    #Line like: 255 heads, 63 sectors/track, 60801 cylinders, total 976773168 sectors
    sectorsLine = subprocess.check_output("LANG=C fdisk -l {0} 2>/dev/null | grep ^Disk | grep sectors".format(device), shell=True)
    print(sectorsLine)
    return int(sectorsLine.strip().split(b" ")[-2])

def performActiveSectorScan(device, offset=0, n=1000):
    "Check all sectors on the hard drive for errors and fix them."
    print(("Performing active sector scan of {0} starting at {1}").format(device, offset))
    print((getNumberOfSectors(device)))
    for i in range(offset, min(getNumberOfSectors(device), offset + n)):
        #Reset sector (only if it is damaged)
        resetSectorHDParm(device, i)

if __name__ == "__main__":
    # Parse arguments
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--sector", nargs="*", default=[], type=int, help="A list of sectors to scan (beyond those listed in ")
    parser.add_argument("--loop", action="store_true", help="Loop and scan for bad sectors every few seconds. By using 'all' as device, it will scan all disks in the system. (VERY DANGEROUS!!)")
    parser.add_argument("-a", "--active-scan", action="store_true", help="Actively scan all blocks for errors. Use --offset to start at a specific block.")
    parser.add_argument("-o", "--offset", default=0, type=int, help="For active scan, the block to start at")
    parser.add_argument("-n", default=1000, type=int, help="For active scan, the number of blocks to scan")
    parser.add_argument("device", default="/dev/sda", help="The device to use")
    args = parser.parse_args()

    if input(DISCLAIMER+'Are you sure you want to use this script? (Yes/No) ') != 'Yes':
        sys.exit(0)

    if args.device != "all":
     #Check if the given device is a block device after all
     if not isBlockDevice(args.device):
        print("Error: device argument must be a block device")
        sys.exit(1)
     print(("Trying to fix bad sectors on %s" % args.device))
     # Always perform one-shot test
     checkDmesgBadSectors(args.device, set())
     # Fix manually added bad sector list
     fixBadSectors(args.device, args.sector)
     # Active sector scan
     if args.active_scan:
        performActiveSectorScan(args.device, args.offset, args.n)

    # If enabled, loop-check
    if args.loop:
        if args.device == "all":

           if input(DISCLAIMER2) == 'Yes I am sure!':
               print( "OK... Brave soul! good luck!! running..." )
               out = subprocess.check_output("/usr/bin/lsscsi  | awk '{print $(NF)}' | grep -v '\-'", shell=True)
               out = [ x.strip() for x in out.decode("utf-8").split('\n') if len(x.strip()) != 0 ]
               # when running as "all", don't spit out idle messages.
               loopCheckForBadSectors(out, feedback=False)
           else:
               print( "Cancelling execution... fiu... :)" )
        else:
           loopCheckForBadSectors(args.device)

