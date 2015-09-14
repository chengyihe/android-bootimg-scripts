#!/usr/bin/python

import os
import sys
import argparse
import struct
from hashlib import sha1

def update_sha_with_buf(sha, buf):
    sha.update(buf)
    sha.update(struct.pack('I', len(buf)))

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

    def update_image(self, kernel_buf, ramdisk_buf, second_buf, dt_buf):
        self.kernel_size = len(kernel_buf)
        self.ramdisk_size = len(ramdisk_buf)
        self.second_size = len(second_buf)
        self.unused[0] = len(dt_buf)
        sha = sha1()
        update_sha_with_buf(sha, kernel_buf)
        update_sha_with_buf(sha, ramdisk_buf)
        update_sha_with_buf(sha, second_buf)
        if self.unused[0] > 0:
            update_sha_with_buf(sha, dt_buf)
        self.img_id = struct.pack('32s', sha.digest())

def read_args(argv):
    parser = argparse.ArgumentParser(description='bootimg updater')
    parser.add_argument('--bootimg', help='path to the bootimg',  type=argparse.FileType('rb'), required=True)
    parser.add_argument('--kernel',  help='path to the kernel',   type=argparse.FileType('rb'), default=None)
    parser.add_argument('--ramdisk', help='path to the ramdisk',  type=argparse.FileType('rb'), default=None)
    parser.add_argument('--second',  help='path to the second',   type=argparse.FileType('rb'), default=None)
    parser.add_argument('--dt',      help='path to the dt',       type=argparse.FileType('rb'), default=None)
    parser.add_argument('--output',  help='path to the output',   type=argparse.FileType('wb'), required=True)
    return parser.parse_args(argv)

def pad_file(f, padding):
    pad = (padding - (f.tell() & (padding - 1))) & (padding - 1)
    f.write(struct.pack(str(pad) + 'x'))

def write_padded_buf_data(f, buf, padding):
    if len(buf) == 0:
        return
    f.write(buf)
    pad_file(f, padding)


def read_buf_data(f_new, f_old, start, size):
    if f_new:
        return f_new.read()
    else:
        f_old.seek(start)
        buf = f_old.read(size)
        f_old.seek(0)
        return buf

def write_header(args, header):
    args.output.write(header.pack())
    pad_file(args.output, header.page_size)

def write_data(args, header):
    num_kernel_pages = (header.kernel_size + header.page_size - 1) / header.page_size
    num_ramdisk_pages = (header.ramdisk_size + header.page_size - 1) / header.page_size
    num_second_pages = (header.second_size + header.page_size - 1) / header.page_size

    start_kernel_addr = header.page_size
    start_ramdisk_addr = start_kernel_addr + header.page_size * num_kernel_pages
    start_second_addr = start_ramdisk_addr + header.page_size * num_ramdisk_pages
    start_dt_addr = start_second_addr + header.page_size * num_second_pages

    kernel_buf = read_buf_data(args.kernel, args.bootimg, start_kernel_addr, header.kernel_size)
    ramdisk_buf = read_buf_data(args.ramdisk, args.bootimg, start_ramdisk_addr, header.ramdisk_size)
    second_buf = read_buf_data(args.second, args.bootimg, start_second_addr, header.second_size)
    dt_buf = read_buf_data(args.dt, args.bootimg, start_dt_addr, header.unused[0])

    header.update_image(kernel_buf, ramdisk_buf, second_buf, dt_buf)

    write_header(args, header)
    write_padded_buf_data(args.output, kernel_buf, header.page_size)
    write_padded_buf_data(args.output, ramdisk_buf, header.page_size)
    write_padded_buf_data(args.output, second_buf, header.page_size)
    write_padded_buf_data(args.output, dt_buf, header.page_size)

def main(argv):
    args = read_args(argv)
    header = boot_img_hdr(args)
    write_data(args, header)

if __name__ == '__main__':
    main(sys.argv[1:])
