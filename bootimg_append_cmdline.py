#!/usr/bin/python

import os
import sys
import argparse
import struct
from hashlib import sha1

class boot_img_hdr:
    def __init__(self, args):
        self.s0 = struct.Struct('<8s 10I 16s 512s 32s 1024s')
        self.unpack(args)

    def unpack(self, args):
        self.unused = [0] * 2
        args.bootimg.seek(0)
        self.magic, self.kernel_size, self.kernel_addr, self.ramdisk_size, self.ramdisk_addr, self.second_size, self.second_addr, self.tag_addr, self.page_size, self.unused[0], self.unused[1], self.name, prefix_cmdline, self.img_id, extra_cmdline = self.s0.unpack(args.bootimg.read(self.s0.size))
        self.cmdline = prefix_cmdline + extra_cmdline
        args.bootimg.seek(0)

    def pack(self):
        return self.s0.pack(self.magic, self.kernel_size, self.kernel_addr, self.ramdisk_size, self.ramdisk_addr, self.second_size, self.second_addr, self.tag_addr, self.page_size, self.unused[0], self.unused[1], self.name, self.cmdline[:512], self.img_id, self.cmdline[512:])

    def append_cmd(self, cmd):
        if not cmd:
            return
        size = len(self.cmdline)
        real_cmdline = self.cmdline.split(chr(0x0))[0]
        if len(real_cmdline) + len(cmd) > size:
            return
        self.cmdline = real_cmdline + ' ' + cmd
        self.cmdline += struct.pack(str(size - len(self.cmdline)) + 'x')

def read_args(argv):
    parser = argparse.ArgumentParser(description='bootimg updater')
    parser.add_argument('--bootimg', help='path to the bootimg',  type=argparse.FileType('rb'), required=True)
    parser.add_argument('--cmd',     help='cmd to append cmdline',type=str,                     required=True)
    parser.add_argument('--output',  help='path to the output',   type=argparse.FileType('wb'), required=True)
    return parser.parse_args(argv)

def pad_file(f, padding):
    pad = (padding - (f.tell() & (padding - 1))) & (padding - 1)
    f.write(struct.pack(str(pad) + 'x'))

def write_header(args, header):
    args.output.write(header.pack())
    pad_file(args.output, header.page_size)

def write_image(args, header):
    args.bootimg.seek(header.page_size)
    args.output.write(args.bootimg.read())

def write_data(args, header):
    header.append_cmd(args.cmd)
    write_header(args, header)
    write_image(args, header)

def main(argv):
    args = read_args(argv)
    header = boot_img_hdr(args)
    write_data(args, header)

if __name__ == '__main__':
    main(sys.argv[1:])
