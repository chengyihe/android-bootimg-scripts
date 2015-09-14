#!/usr/bin/python

import os
import sys
import argparse
import struct

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

def read_args(argv):
    parser = argparse.ArgumentParser(description='bootimg parser')
    parser.add_argument('--bootimg', help='path to the bootimg', type=argparse.FileType('rb'), required=True)
    parser.add_argument('--kernel',  help='path to the kernel',  type=argparse.FileType('wb'), default='kernel')
    parser.add_argument('--ramdisk', help='path to the ramdisk', type=argparse.FileType('wb'), default='ramdisk')
    parser.add_argument('--second',  help='path to the second',  type=argparse.FileType('wb'), default='second')
    parser.add_argument('--dt',      help='path to the dt',      type=argparse.FileType('wb'), default='dt')
    return parser.parse_args(argv)

def write_file_data(f_out, f_in, start, size):
    f_in.seek(start)
    f_out.write(f_in.read(size))
    f_in.seek(0)

def write_data(args, header):
    num_kernel_pages = (header.kernel_size + header.page_size - 1) / header.page_size
    num_ramdisk_pages = (header.ramdisk_size + header.page_size - 1) / header.page_size
    num_second_pages = (header.second_size + header.page_size - 1) / header.page_size

    start_kernel_addr = header.page_size
    start_ramdisk_addr = start_kernel_addr + header.page_size * num_kernel_pages
    start_second_addr = start_ramdisk_addr + header.page_size * num_ramdisk_pages
    start_dt_addr = start_second_addr + header.page_size * num_second_pages

    write_file_data(args.kernel, args.bootimg, start_kernel_addr, header.kernel_size)
    write_file_data(args.ramdisk, args.bootimg, start_ramdisk_addr, header.ramdisk_size)
    write_file_data(args.second, args.bootimg, start_second_addr, header.second_size)
    write_file_data(args.dt, args.bootimg, start_dt_addr, header.unused[0])

    if header.second_size == 0:
        args.second.close()
        os.remove(args.second.name)

    if header.unused[0] == 0:
        args.dt.close()
        os.remove(args.dt.name)

def main(argv):
    args = read_args(argv)
    header = boot_img_hdr(args)
    write_data(args, header)

if __name__ == '__main__':
    main(sys.argv[1:])
