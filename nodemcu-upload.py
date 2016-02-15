#!/usr/bin/python

import sys
import os
import serial
import socket

port = '/dev/ttyUSB0'
baudrate = 9600
CHUNK_SIZE = 16

HEADER_CODE = [
        '_w=function(data, f1, f2)',
            'local i',
            'local sum1=0',
            'local sum2=0',
            'for i = 1, #data do',
                'local c = string.byte(data, i)',
                'sum1 = (sum1 + c) % 255',
                'sum2 = (sum2 + sum1) % 255',
            'end',
            'if f1 ~= sum1 or f2 ~= sum2 then',
                'print("ERROR: checksum doesnt match")',
            'else',
                'file.write(data)',
            'end',
        'end',
        'file.open("_upload.lua", "w")',
]

TRAILER_CODE = [
        'file.close()',
        '_w=nil',
]

def usage():
    print 'Usage: %s <filename>' % sys.argv[0]
    print
    print '<filename> is the lua source file to be compiled and uploaded, if it is init.lua it will not be compiled'
    print

def chunk_it(data, size):
    while len(data) > 0:
        prefix = data[0:size]
        data = data[size:]
        yield prefix

def fletcher(data):
    sum1 = 0
    sum2 = 0

    for ch in data:
        val = ord(ch)
        sum1 += val
        sum1 %= 255
        sum2 += sum1
        sum2 %= 255

    return (sum1, sum2)

def encode_data(data):
    s = ''
    for ch in data:
        s += '\%d' % ord(ch)
    return s

def lua_encode(data):
    sum1, sum2 = fletcher(data)
    encoded_data = encode_data(data)
    return '_w("%s", %d, %d)' % (encoded_data, sum1, sum2)

def serial_send(ser, commands):
    for command in commands:
        print command
        ser.write(command)
        ser.write('\n')

        s = ''
        while 1:
            s += ser.read()
            if s.endswith('> '):
                break
        print s

def replace_file(ser, fromname, toname):
    serial_send(ser, ['file.remove("%s")' % toname, 'file.rename("%s", "%s")' % (fromname, toname)])

class NetSerial(object):
    def __init__(self, sock):
        self._sock = sock
    def write(self, data):
        return self._sock.sendall(data)
    def read(self, sz=64):
        return self._sock.recv(sz)

def upload_data(ser, filename, data):
    chunks = []
    for chunk in chunk_it(data, CHUNK_SIZE):
        chunks.append(lua_encode(chunk))

    serial_send(ser, HEADER_CODE)
    print
    serial_send(ser, chunks)
    print
    serial_send(ser, TRAILER_CODE)
    print
    if filename == 'init.lua':
        serial_send(ser, ['file.remove("init.lua")', 'file.rename("_upload.lua","init.lua")'])
    elif filename.endswith('.lua'):
        lcname = filename[:-4] + '.lc'
        serial_send(ser, ['node.compile("_upload.lua")', 'file.remove("_upload.lua")'])
        replace_file(ser, '_upload.lua', lcname)
    else:
        replace_file(ser, '_upload.lua', filename)
    
def main():
    if len(sys.argv) != 2:
        return usage()

    f = file(sys.argv[1], 'r')
    data = f.read()
    f.close()

    #ser = serial.Serial(port, baudrate)
    ser = NetSerial(socket.create_connection( ('127.0.0.1', 9090) ))

    upload_data(ser, os.path.basename(sys.argv[1]), data)

if __name__ == '__main__':
    main()
