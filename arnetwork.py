# Copyright (c) 2011 Bastian Venthur
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


import select
import socket
import threading
import multiprocessing

import libardrone
import arvideo

import datetime

class ARDroneNetworkThread(threading.Thread):

    def __init__(self, drone):
        threading.Thread.__init__(self)
        self.drone = drone
        self.stopping = False

    def run(self):
        video_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        video_socket.setblocking(0)
        video_socket.bind(('', libardrone.ARDRONE_VIDEO_PORT))
        video_socket.sendto("\x01\x00\x00\x00", ('192.168.1.1', libardrone.ARDRONE_VIDEO_PORT))

        nav_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        nav_socket.setblocking(0)
        nav_socket.bind(('', libardrone.ARDRONE_NAVDATA_PORT))
        nav_socket.sendto("\x01\x00\x00\x00", ('192.168.1.1', libardrone.ARDRONE_NAVDATA_PORT))
 
        while not self.stopping:
            # TODO: check if we should use a timeout here like below
            inputready, outputready, exceptready = select.select([nav_socket, video_socket], [], [])
            for i in inputready:
                if i == video_socket:
                    while 1:
                        try:
                            data, address = video_socket.recvfrom(65535)
                        except:
                            break
                    self.drone.new_video_packet(data)
                elif i == nav_socket:
                    while 1:
                        try:
                            data, address = nav_socket.recvfrom(65535)
                        except:
                            break
                    self.drone.new_navdata_packet(data)
        video_socket.close()
        nav_socket.close()

    def stop(self):
        self.stopping = True


class ARDroneNetworkProcess(multiprocessing.Process):

    def __init__(self, nav_pipe, video_pipe):
        multiprocessing.Process.__init__(self)
        self.nav_pipe = nav_pipe
        self.video_pipe = video_pipe
        self.stopping = False

    def run(self):
        video_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        video_socket.setblocking(0)
        video_socket.bind(('', libardrone.ARDRONE_VIDEO_PORT))
        video_socket.sendto("\x01\x00\x00\x00", ('192.168.1.1', libardrone.ARDRONE_VIDEO_PORT))

        nav_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        nav_socket.setblocking(0)
        nav_socket.bind(('', libardrone.ARDRONE_NAVDATA_PORT))
        nav_socket.sendto("\x01\x00\x00\x00", ('192.168.1.1', libardrone.ARDRONE_NAVDATA_PORT))

        f = 0
        while not self.stopping:
            inputready, outputready, exceptready = select.select([nav_socket, video_socket], [], [])
            for i in inputready:
                if i == video_socket:
                    ts = datetime.datetime.now()
                    while 1:
                        print 's',
                        try:
                            data, address = video_socket.recvfrom(65535)
                        except:
                            break
                    br = arvideo.BitReader(data)
                    w, h, image, t = arvideo.read_picture(br)
                    try:
                        self.video_pipe.send(image)
                    except e:
                        print "error while sending in video pipe."
                        print e
                    print
                    print 'd>',f,  datetime.datetime.now() - ts
                    f += 1
                elif i == nav_socket:
                    while 1:
                        try:
                            data, address = nav_socket.recvfrom(65535)
                        except:
                            break
                    navdata = libardrone.decode_navdata(data)
                    self.nav_pipe.send(navdata)
        video_socket.close()
        nav_socket.close()

    def stop(self):
        self.stopping = True


class IPCThread(threading.Thread):

    def __init__(self, drone):
        threading.Thread.__init__(self)
        self.drone = drone
        self.stopping = False

    def run(self):
        f = 0
        while not self.stopping:
            inputready, outputready, exceptready = select.select([self.drone.video_pipe, self.drone.nav_pipe], [], [], 1)
            for i in inputready:
                if i == self.drone.video_pipe:
                    while self.drone.video_pipe.poll():
                        image = self.drone.video_pipe.recv()
                    self.drone.image = image
                    print 't<',f, datetime.datetime.now()
                    f += 1
                elif i == self.drone.nav_pipe:
                    while self.drone.nav_pipe.poll():
                        _ = self.drone.nav_pipe.recv()

    def stop(self):
        self.stopping = True
