# fixhdd
https://techoverflow.net/blog/2015/01/07/fixing-bad-blocks-on-hdds-using-fixhdd.py/

Fixing bad blocks on HDDs using fixhdd.py
Mi 07 Januar 2015
By Uli Köhler
In Python

Problem:

You hard drive or SMART tool reports errors when reading specific blocks
similar to this message:

[3142.686141] end_request: I/O error, dev sda, sector 31415926
No matter how often you read the block, the hard drive still returns
an error and does not reallocate the block.

Background:

Hard drives are programmed not to reallocate the block until someone writes
to said block. This means that for normal users the program reading the bad
block probably won’t fix the error by itself as most programs exhibit
read-before-write usage patterns often resulting in a crash before any
block is written. By using fixhdd.py, the script presented in this post,
you can force your Linux-based OS to rewrite the blocks, effectively fixing
the block errors if the HDD has reallocation space left. Usage of said
script is only recommended for professional IT personnel.

Solution:

You can use this script, fixhdd.py in order to automatically write the
blocks yielding errors. While the data stored in those blocks will be lost
forever, you won’t any read error after writing to it.

Syslog monitoring mode

fixhdd.py operates in one of several modes including automatic sequential
scan. The most straightforward mode, however, is to continously scan the
system log for error message like that outlined above. The tool
automatically extracts the LBA (logical block address) from the system log
and writes it using hdparm (use sudo apt-get install hdparm or equivalent
if not already installed).

In order to use this mode, run

sudo fixhdd.py --loop /dev/sda

in the background. In another shell, run the program yielding the error
message repeatedly until the file can be read without an error. Every five
seconds, fixhdd.py will re-scan the syslog and attempt to rewrite all
damaged blocks. When finished, stop fixhdd.py using Ctrl+C.

Sequential block scan mode

After these errors are resolved, I recommend using smartctl -t [short|long]
to run a SMART test on the hard drive (even a short two-minute tests will
often yield a LBA for the first bad block). After the selftest has
finished, use smartctl -a to find the first LBA of first error.

For this example, we will assume the LBA of first error is 1234567. To get
the offset for fixhdd.py (i.e. the first LBA that will be scanned),
substract a safety margin of about 100-1000 from the LBA of first error
so the script will recognize errors occuring before the given LBA. The
script will now try to read all LBAs starting from the offset, rewriting
any bad blocks in the process. You can also start at offset 0 and wait
several hours to days for the whole HDD to be scanned.

sudo fixhdd.py -a -o 1234000 /dev/sda

WARNING: fixhdd.py is EXTREMELY dangerous and might destroy all your data
in just a few seconds. I recommend using it only if you understand the
source code and know how the script and hdparm work. Even then it is your
own responsibility if any of your data gets lots (in theory, there is
a remote possibility of hdparm damaging your hardware, however I believe
this is next to impossible). While I used fixhdd.py several times to fix
broken computers in the past, it might have critical bugs on other systems.
Even hardware damage is possible, considering the power of hdparm.
fixhdd.py currently doesn’t include a simulation mode and silently bypasses
the hdparm --yes-i-know-what-i-am-doing flag.
