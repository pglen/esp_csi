#!/usr/bin/env python3
# -*-coding:utf-8-*-

# Copyright 2021 Espressif Systems (Shanghai) PTE LTD
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

# WARNING: we don't check for Python build-time dependencies until
# check_environment() function below. If possible, avoid importing
# any external libraries here - put in external script, or import in
# their specific function instead.

import sys
import csv
import json
import argparse
import pandas as pd
import numpy as np

import serial
from os import path
from io import StringIO

from PyQt5.Qt import *
import pyqtgraph as pg
#from pyqtgraph import PlotWidget
import pyqtgraph as pq
from PyQt5 import QtCore
from PyQt5 import QtGui

import matplotlib.pyplot as plt

import threading
import time
import math
import random
import queue

from PIL import Image, ImageDraw
from PIL import ImageQt

stopme = 0

# Reduce displayed waveforms to avoid display freezes
#CSI_VAID_SUBCARRIER_INTERVAL = 3
CSI_VAID_SUBCARRIER_INTERVAL = 1
#CSI_VAID_SUBCARRIER_INTERVAL = 5
MAX_SHADES = 22

# Remove invalid subcarriers
# secondary channel : below, HT, 40 MHz, non STBC, v, HT-LFT: 0~63, -64~-1, 384
csi_vaid_subcarrier_index = []
csi_vaid_subcarrier_color = []
color_step = (255-70) // (MAX_SHADES // CSI_VAID_SUBCARRIER_INTERVAL + 1)

# LLTF:
csi_vaid_subcarrier_index += [i for i in range(6, MAX_SHADES +6, CSI_VAID_SUBCARRIER_INTERVAL)]     # 26  red
csi_vaid_subcarrier_color += [(i * color_step +70, 0, 0) for i in range(0,  MAX_SHADES // CSI_VAID_SUBCARRIER_INTERVAL + 1) ]

csi_vaid_subcarrier_index += [i for i in range(MAX_SHADES +6, MAX_SHADES +MAX_SHADES +6, CSI_VAID_SUBCARRIER_INTERVAL)]     # 26  red
csi_vaid_subcarrier_color += [(0, i * color_step +70, 0) for i in range(0,  MAX_SHADES // CSI_VAID_SUBCARRIER_INTERVAL + 1) ]

csi_vaid_subcarrier_index += [i for i in range(2*MAX_SHADES +6, 3*MAX_SHADES +6, CSI_VAID_SUBCARRIER_INTERVAL)]     # 26  red
csi_vaid_subcarrier_color += [(0, 0, i * color_step +70) for i in range(0,  MAX_SHADES // CSI_VAID_SUBCARRIER_INTERVAL + 1) ]

csi_vaid_subcarrier_index += [i for i in range(3*MAX_SHADES +6, 4*MAX_SHADES +6, CSI_VAID_SUBCARRIER_INTERVAL)]     # 26  red
csi_vaid_subcarrier_color += [(128, 128, i * color_step +70) for i in range(0,  MAX_SHADES // CSI_VAID_SUBCARRIER_INTERVAL + 1) ]

#csi_vaid_subcarrier_index += [i for i in range(33, 59, CSI_VAID_SUBCARRIER_INTERVAL)]    # 26  green
#csi_vaid_subcarrier_color += [(0, i * color_step, 0) for i in range(1,  26 // CSI_VAID_SUBCARRIER_INTERVAL + 2)]

CSI_DATA_LLFT_COLUMNS = len(csi_vaid_subcarrier_index)

# HT-LFT: 56 + 56
#csi_vaid_subcarrier_index += [i for i in range(66, 94, CSI_VAID_SUBCARRIER_INTERVAL)]    # 28  blue
#csi_vaid_subcarrier_color += [(0, 0, i * color_step) for i in range(1,  28 // CSI_VAID_SUBCARRIER_INTERVAL + 2)]
#csi_vaid_subcarrier_index += [i for i in range(95, 123, CSI_VAID_SUBCARRIER_INTERVAL)]   # 28  White
#csi_vaid_subcarrier_color += [(i * color_step, i * color_step, i * color_step) for i in range(1,  28 // CSI_VAID_SUBCARRIER_INTERVAL + 2)]
##
# csi_vaid_subcarrier_index += [i for i in range(124, 162)]  # 28  White
# csi_vaid_subcarrier_index += [i for i in range(163, 191)]  # 28  White

CSI_DATA_INDEX = 200  # buffer size
CSI_TRAIN_SIZE = 5
#CSI_DATA_COLUMNS = len(csi_vaid_subcarrier_index)
CSI_DATA_COLUMNS = 300
DATA_COLUMNS_NAMES = ["type", "id", "mac", "rssi", "rate", "sig_mode", "mcs", "bandwidth", "smoothing", "not_sounding", "aggregation", "stbc", "fec_coding",
                      "sgi", "noise_floor", "ampdu_cnt", "channel", "secondary_channel", "local_timestamp", "ant", "sig_len", "rx_state", "len", "first_word", "data"]

CSI_DATA_ARR_SIZE = 384
#csi_data_array = np.zeros(
#    [CSI_DATA_INDEX, CSI_DATA_COLUMNS], dtype=np.complex64)

csi_data_array = np.zeros(
    [CSI_DATA_INDEX, CSI_DATA_COLUMNS], dtype=np.float64)

csi_data_array2 = np.zeros(
    [CSI_DATA_INDEX, CSI_DATA_COLUMNS], dtype=np.float64)

csi_data_array3 = np.zeros(
    [CSI_DATA_INDEX, CSI_DATA_COLUMNS], dtype=np.float64)

csi_data_array4 = np.zeros(
    [CSI_DATA_INDEX, CSI_DATA_COLUMNS], dtype=np.float64)

outdata3 = np.zeros(
    [CSI_DATA_INDEX, CSI_DATA_COLUMNS], dtype=np.float64)

outdata4 = np.zeros(
    [CSI_DATA_INDEX, CSI_DATA_COLUMNS], dtype=np.float64)

currsig = np.zeros(
    [ CSI_TRAIN_SIZE, CSI_DATA_ARR_SIZE], dtype=np.float64)

currsig2 = np.zeros(
    [ CSI_TRAIN_SIZE, CSI_DATA_ARR_SIZE], dtype=np.float64)

traindict  = {}
traindict2 = {}

qqq = queue.Queue()

def SQR(vv):
    return vv*vv

xlabel = None
logwin = None
xsum = 0
zsum = 0
prog = 0
stopser = 0
train = 0
recog = 0
imgidx = 0
ilabel = []
ximage = []
datacnt = 0
offsx = 0

cnt = 0
ztime = 0
incnt = 0

iiz = []
for i in range(len(csi_data_array[:, 0]) ):
    iiz.append(i)

def strpad(strx, lenx):
    lll = len(strx)
    if lenx <= lll:
        return strx
    return strx + ' ' * (lenx-lll)

def worker():

    if qqq.empty():
        return

    while True:
        try:
            item = qqq.get(False)
        except queue.Empty:
            #return
            break

        if not item:
            return

        logwin.update()
        logwin.moveCursor(QTextCursor.End)
        logwin.insertPlainText(item)
        logwin.ensureCursorVisible()
        txt = logwin.toPlainText()

    if len(txt) > 3000:
        logwin.clear()
        logwin.insertPlainText(txt[1000:])

    qqq.task_done()


# imitate some features of print

def logx(*strx, **keyw):

    sss = ""
    for aa in strx:
       sss += str(aa) + ' '

    if 'end' in keyw:
        sss += keyw['end']
    else:
        sss += '\n'

    # submit for aync processing
    qqq.put(sss)

def SQRRT(vv, tt):
    return math.sqrt(vv*vv + tt*tt)

def parr(namex, arrx):
    print (namex, end= ' ')
    for aa in arrx[6:9]:
        print(aa[6:9])

def deangle(vv, tt):

    uu = 0
    if tt != 0:
        dd = abs(vv) / abs(tt)
        uu = math.atan(dd)

    #      +-     |   ++
    #  -----------|---------------
    #      --     |   +-

    '''if vv > 0. and tt > 0.:
        uu += 0
    elif vv > 0. and tt < 0.:
        uu += 1
    elif vv < 0. and tt < 0.:
        uu += 2
    elif vv > 0. and tt < 0.:
        uu += 3
    else:
        pass
    '''
    uuu = math.degrees(uu) / 10
    #print(uu, uuu)
    return uuu

def   onclick():
      global stopser
      stopser = 0

def   onclick2():
      global stopser
      stopser = 1

def   onclick3a():
      import re
      #rrr = re.compile("[0-9]")
      sss = re.split('([0-9])', tlabel.text())
      if len(sss) == 1:
        eee = sss[0] + '1'
      else:
        eee = sss[0] + str( int(sss[1])+1)
      #print(eee)
      tlabel.setText(eee)


def   onclick3():
      global train, recog
      logx("Train started with '", tlabel.text(), "'")
      traindict [tlabel.text()] =  np.zeros(
                [CSI_TRAIN_SIZE, CSI_DATA_ARR_SIZE], dtype=np.float64)
      traindict2[tlabel.text()] =  np.zeros(
                [CSI_TRAIN_SIZE, CSI_DATA_ARR_SIZE], dtype=np.float64)


      #print (traindict)
      #print (traindict2)
      train = 1
      recog = 0
      form.button3.setDisabled(True)
      form.button3a.setDisabled(True)

def   onclick4():
      global train, recog, form
      train = 0
      recog = not recog

      if recog:
        form.button4.setText("St&op")
      else:
        form.button4.setText("R&ecog")


def   onclick5():
      sys.exit()
# ------------------------------------------------------------------------

class FormWidget(QWidget):

    def __init__(self, parent):
        super(FormWidget, self).__init__(parent)
        self.layout = QHBoxLayout(self)

        self.button1 = QPushButton("&Start")
        self.layout.addWidget(self.button1)
        self.button1.clicked.connect(onclick)

        self.button2 = QPushButton("S&top")
        self.layout.addWidget(self.button2)
        self.button2.clicked.connect(onclick2)

        self.button3 = QPushButton("T&rain")
        self.layout.addWidget(self.button3)
        self.button3.clicked.connect(onclick3)

        self.button3a = QPushButton("cnt+")
        self.layout.addWidget(self.button3a)
        self.button3a.clicked.connect(onclick3a)

        global tlabel
        tlabel = QLineEdit("base1")
        tlabel.setMaxLength(55)
        tlabel.setFixedSize(200, 30) #tlabel.height())
        #tlabel.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
        #tlabel.resize(265, tlabel.height());
        self.layout.addWidget(tlabel)

        self.button4 = QPushButton("R&ecog")
        self.layout.addWidget(self.button4)
        self.button4.clicked.connect(onclick4)

        global zlabel
        zlabel = QLabel("zidle")
        self.layout.addWidget(zlabel)

        global xlabel
        xlabel = QLabel("xidle")
        self.layout.addWidget(xlabel)

        self.button5 = QPushButton("E&xit")
        self.layout.addWidget(self.button5)
        self.button5.clicked.connect(onclick5)

        self.setLayout(self.layout)
        global form
        form = self

    def onclick(self):
        print("onclick")

class csi_data_graphical_window(QMainWindow):
    def __init__(self):
        super().__init__()

        self.resize(1280, 720)
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

        self.setWindowTitle(serial_port + ' + ' + serial_port2)

        # control map
        # ppppppp   iii
        # ppppppp
        # lllllllllllll

        self.plotWidget_ted = pg.PlotWidget(self)
        #self.plotWidget_ted.setGeometry(QtCore.QRect(0, 0, 1280, 720))
        self.plotWidget_ted.setYRange(-120, 120)
        #self.plotWidget_ted.addLegend((10,1))
        self.plotWidget_ted.setTitle('CSI Scatter Plot')

        self.plotWidget_ted2 = pg.PlotWidget(self)
        #self.plotWidget_ted2.setGeometry(QtCore.QRect(0, 0, 1280, 720))
        self.plotWidget_ted2.setYRange(-2000, 2000)
        #self.plotWidget_ted2.addLegend((10,1))

        global ilabel, ylabel, yimage
        ilabel = QLabel(self)
        xpixmap = QPixmap.fromImage(QImage(200, 400, QImage.Format_RGB32))
        xpixmap.fill(Qt.black)

        yimage = Image.new("RGBA", (400,400), color=(000,000,000) )
        #ximage.show()
        ylabel = QLabel(self)
        pix = QPixmap.fromImage(ImageQt.ImageQt(yimage))
        ylabel.setPixmap(pix)

        self.main = QWidget(self)
        self.sub_layout = QHBoxLayout(self.main)

        self.main3 = QWidget(self)
        self.sub_layout2 = QVBoxLayout(self.main3)
        self.main3.setLayout(self.sub_layout2)
        self.sub_layout2.addWidget(self.plotWidget_ted, stretch=2)
        self.sub_layout2.addWidget(self.plotWidget_ted2)
        self.main3.setLayout(self.sub_layout2)

        self.sub_layout.addWidget(self.main3)
        self.sub_layout.addWidget(ilabel)
        self.sub_layout.addWidget(ylabel)
        self.main2 = QWidget(self)
        self.main2.setLayout(self.sub_layout)

        self.main_layout = QVBoxLayout(self.main)
        self.main_layout.addWidget(self.main2, stretch=2)

        global logwin
        logwin = QTextEdit()
        logwin.setReadOnly(1)
        doc = logwin.document();
        font = doc.defaultFont();
        font.setFamily("Courier New");
        doc.setDefaultFont(font);

        global yimage2, ylabel2
        yimage2 = Image.new("RGBA", (400,200), color=(000,000,000) )
        ylabel2 = QLabel(self)
        pix2 = QPixmap.fromImage(ImageQt.ImageQt(yimage2))
        ylabel2.setPixmap(pix2)

        self.main4 = QWidget(self)
        self.sub_layout3 = QHBoxLayout(self.main4)

        self.sub_layout3.addWidget(logwin)
        self.sub_layout3.addWidget(ylabel2)

        self.main_layout.addWidget(self.main4, stretch=1)

        self.form = FormWidget(self)
        self.main_layout.addWidget(self.form)

        self.setCentralWidget(self.main)

        self.curve_list = []

        #print(f"csi_vaid_subcarrier_color, len: {len(csi_vaid_subcarrier_color)}, {csi_vaid_subcarrier_color}")

        ii = []
        for i in range(len(csi_data_array[:, 0]) ):
            ii.append(i)

        #print(ii)
        if 1: #for i in range(CSI_DATA_COLUMNS):
            #curve = self.plotWidget_ted.
            curve = pg.ScatterPlotItem(ii,
                csi_data_array[:, 0],
                        name=str(i) + ' ' + str(i*CSI_VAID_SUBCARRIER_INTERVAL),
                    size=2, brush=pg.mkBrush(0,0,200))
            self.plotWidget_ted.addItem(curve)
            self.curve_list.append(curve)

            curve2 = pg.ScatterPlotItem(ii,
                csi_data_array3[:, 0],
                    size=2, brush=pg.mkBrush(200,0,0))

            self.plotWidget_ted.addItem(curve2)
            self.curve_list.append(curve2)

            curve3 = pg.ScatterPlotItem(ii,
                outdata3[:, 0],
                    size=1, brush=pg.mkBrush(0,200,200))

            self.plotWidget_ted.addItem(curve3)
            self.curve_list.append(curve3)

            curve4 = pg.ScatterPlotItem(ii,
                outdata4[:, 0],
                    size=1, brush=pg.mkBrush(200,200,200))

            self.plotWidget_ted2.addItem(curve4)
            self.curve_list.append(curve4)


        self.timer = pq.QtCore.QTimer()
        self.timer.timeout.connect(self.update_data)
        self.timer.start(200)

    def update_data(self):

        global cnt, xsum, zsum

        worker()

        global stopser
        if stopser:
            return

        cnt += 1

        #print(csi_data_array.shape)
        #print(csi_data_array)

        self.curve_list[0].setData(iiz, csi_data_array[:, 0])
        self.curve_list[1].setData(iiz, csi_data_array2[:, 0])
        self.curve_list[2].setData(iiz, outdata3[:, 0])
        self.curve_list[3].setData(iiz, outdata4[:, 0])

        xlabel.setText("%.2f" % xsum)

        global ztime
        ztime += 1
        if abs(zsum) > 1000:
            zlabel.setText("Motion %.2f" % zsum)
            ztime = 0
        if ztime > 10:
           zlabel.setText("Idle")

        #logx("%.2f  " % zsum)

        global imgidx

        mxx = 0
        for bb in range(200):
            xx = abs(csi_data_array[bb][0]) # + 128
            if xx > mxx:
                mxx = xx
        if mxx:
            scale =  255 / mxx
        else:
            scale = 5
        #print(mxx, scale)
        scale = 4
        bw =  Image.new("RGBA", (400, 1), color=(000,000,000) )
        ptr = list(bw.getdata())
        #print(ptr)
        for bb in range(200):
            xx = csi_data_array[bb][0]
            # normalize
            iii = int((xx+mxx/2) * scale) & 255
            ptr[bb] = (0, iii, 0)
            #ptr[2*bb+1] = (0, iii, 0)
        bw.putdata(ptr)
        yimage.paste(bw, box=( 0,  imgidx,)  )
        bw =  Image.new("RGBA", (400, 1), color=(000,000,000) )
        ptr = list(bw.getdata())
        #print(ptr)
        for bb in range(200):
            xx = csi_data_array2[bb][0]
            # normalize
            iii = int((xx+mxx/2) * scale) & 255
            ptr[bb] = (0, iii, 0)
            #ptr[2*bb+1] = (0, iii, 0)
        bw.putdata(ptr)

        yimage.paste(bw, box=( 200,  imgidx,)  )
        pix = QPixmap.fromImage(ImageQt.ImageQt(yimage))
        ylabel.setPixmap(pix)

        imgidx += 1
        if imgidx >= 400:
            draw = ImageDraw.Draw(yimage)
            draw.rectangle((0, 0, 400, 400), fill=(0, 0, 0, 255))
            imgidx = 0

        if stopme:
            #print("stopme")
            subthread = []

            sys.exit()
            #return True

def csi_data_read_parse(port: str, csv_writer, outdata, outdata2):

    ser = None
    try:
        ser = serial.Serial(port=port, baudrate=921600,
                        bytesize=8, parity='N', stopbits=1)
    except:
        print("open", sys.exc_info())
        global stopme
        stopme = 1
        return
        #sys.exit()

    if ser.isOpen():
        #=print("open success", port)
        pass
    else:
        print("open failed", port)
        return

    while True:
        strings = str(ser.readline())
        if not strings:
            break

        strings = strings.lstrip('b\'').rstrip('\\r\\n\'')
        index = strings.find('CSI_DATA')

        if index == -1:
            continue

        global stopser
        if stopser:
            continue

        csv_reader = csv.reader(StringIO(strings))
        csi_data = next(csv_reader)

        if len(csi_data) != len(DATA_COLUMNS_NAMES):
            print("element header number is not equal")
            continue

        try:
            csi_raw_data = json.loads(csi_data[-1])
        except json.JSONDecodeError:
            print(f"data is incomplete")
            continue

        if len(csi_raw_data) != 128 and len(csi_raw_data) != 256 and len(csi_raw_data) != 384:
            print(f"element number is not equal: {len(csi_raw_data)}")
            continue

        csv_writer.writerow(csi_data)

        fill(csi_raw_data, outdata, outdata2)

    ser.close()
    return

# turnvector ratio to angle


fcnt = 0

def fill(csi_raw_datax, outdata, outdata2):

    #print(len(csi_raw_datax))

    if len(csi_raw_datax) == 128:
        csi_vaid_subcarrier_len = CSI_DATA_LLFT_COLUMNS
    else:
        #csi_vaid_subcarrier_len = CSI_DATA_COLUMNS
        csi_vaid_subcarrier_len = len(csi_raw_datax)

    # Rotate data to the left
    #csi_data_array[:-1] = csi_data_array[1:]
    #outdata[:-1] = outdata[1:]

    global xsum

    try:
        for i in range(csi_vaid_subcarrier_len // 2):
            #csi_data_array[-1][i] = complex(csi_raw_data[csi_vaid_subcarrier_index[i] * 2],
            #                                csi_raw_data[csi_vaid_subcarrier_index[i] * 2 - 1])

            outdata[i][0] = csi_raw_datax[i * 2]
            outdata2[i][0] = csi_raw_datax[i * 2 -1]

            #try:
            #csi_data_array[-1][i] = complex(0,
            #                                csi_raw_data[csi_vaid_subcarrier_index[i] * 2 - 1])
            #csi_data_array[-1][i] = complex(csi_raw_data[csi_vaid_subcarrier_index[i] * 2],
            #                                0)
        global zsum
        zsum = 0
        for i in range(csi_vaid_subcarrier_len // 2):
            try:
                pass
                #ppp = deangle(csi_data_array[i][0], csi_data_array2[i][0])
                #nnn = deangle(csi_data_array3[i][0], csi_data_array4[i][0])

                zsum += csi_data_array[i][0]

            except:
                pass
                print("div", sys.exc_info())

        xsum += (zsum - xsum) / 30
        global prog
        if prog >= 199:
           outdata4[:-1] = outdata4[1:]
        else:
            prog += 1

        outdata4[prog][0] = zsum

        global train, datacnt, offsx
        if train:
            #print("Train", datacnt)
            for aa in range(len(csi_raw_datax)// 2):
                traindict[tlabel.text()][datacnt][aa] = csi_raw_datax[aa*2]
                traindict2[tlabel.text()][datacnt][aa] = csi_raw_datax[aa*2-1]

            datacnt += 1
            if datacnt >= CSI_TRAIN_SIZE:
                train = 0
                form.button3.setDisabled(False)
                form.button3a.setDisabled(False)
                drawtrain(offsx, traindict[tlabel.text()], traindict2[tlabel.text()])
                logx("Training added at %d" % offsx)
                offsx += datacnt +2
                datacnt = 0

        if recog:
            recogx(csi_raw_datax)
    except:
        print("fill", sys.exc_info())

dcnt = 0

# s=signal d=dictionary
# sssssssssss  0
# sssssssssss  1  head
# sssssssssss  2
# sssssssssss  3

# ddddddddddd
# ddddddddddd  --  head
# ddddddddddd
# ddddddddddd

def recogx(csi_raw_datax):

    global incnt
    for aa in range(len(csi_raw_datax)// 2):
        currsig[incnt % CSI_TRAIN_SIZE][aa] = csi_raw_datax[aa*2]

    #print("raw", currsig)
    hit = 'none'; mxx2 = 0xffffffff
    for aa in  traindict.keys():
        mxx = 0xffffffff
        # scan dict item
        for bb in range(len(traindict[aa])):
            idx = (incnt + bb) % CSI_TRAIN_SIZE
            #print(idx, end=' ')
            ddd = []
            for cc in range(len(currsig[idx])):
                # Compare
                ddd.append(SQR(currsig[idx][cc] - traindict[aa][bb][cc]))
                #print ('%.2f#%.2f=%.2f  ' \
                #        % (currsig[cc],  bb[cc], ddd), end='   ')
            sum = 0
            for dd in range(len(ddd)):
                sum += ddd[dd]
            sum /= len(ddd)
            #print('%.2f' % sum, end = '  ')
            if mxx > sum:
                mxx = sum
        #print()

        #print(aa, '%.2f' % mxx, end = '  ')
        #if mxx2 > mxx:
        #    mxx2 = mxx
        #    hit = aa
        if mxx2 > sum:
            mxx2 = sum
            hit = aa
    #print(hit, '%.2f' % mxx2)

    logx(strpad(hit, 8), strpad('%.2f' % mxx2, 8), end='  ')
    global dcnt
    dcnt += 1
    if dcnt % 4 == 0:
        logx()

    incnt += 1

def drawtrain(offs, tdata, tdata2):
    ret = len(tdata); scale = 4
    for bb in range(len(tdata)):
        mxx = 0
        for cc in range(len(tdata[bb])):
            xx = abs(tdata[bb][cc]) # + 128
            if xx > mxx:
                mxx = xx
        if mxx:
            scale =  255 / mxx
        else:
            scale = 5
        #print(mxx, scale)
        scale = 4

        bw2 =  Image.new("RGBA", (400, 1), color=(000,000,000) )
        ptr = list(bw2.getdata())
        for cc in range(len(tdata[bb])):
            xx = tdata[bb][cc]
            # normalize
            iii = int((xx+mxx/2) * scale) & 255
            #iii = int((xx) * scale) & 255
            ptr[cc] = (0, iii, 0)
        bw2.putdata(ptr)
        yimage2.paste(bw2, box=( 0,  offs + bb,)  )

        bw2 =  Image.new("RGBA", (400, 1), color=(000,000,000) )
        ptr = list(bw2.getdata())
        for cc in range(len(tdata2[bb])):
            xx = tdata2[bb][cc]
            # normalize
            iii = int((xx+mxx/2) * scale) & 255
            #iii = int((xx) * scale) & 255
            ptr[cc] = (0, iii, 0)
        bw2.putdata(ptr)
        yimage2.paste(bw2, box=( 200,  offs+bb,)  )

    pix = QPixmap.fromImage(ImageQt.ImageQt(yimage2))
    ylabel2.setPixmap(pix)
    return ret


class SubThread (QThread):
    def __init__(self, serial_port, save_file_name):
        super().__init__()
        self.serial_port = serial_port

        save_file_fd = open(save_file_name, 'w')
        self.csv_writer = csv.writer(save_file_fd)
        self.csv_writer.writerow(DATA_COLUMNS_NAMES)

    def run(self):
        csi_data_read_parse(self.serial_port, self.csv_writer,
                        csi_data_array, csi_data_array2)

    def __del__(self):
        self.wait()

if __name__ == '__main__':
    if sys.version_info < (3, 6):
        print(" Python version should >= 3.6")
        exit()

    parser = argparse.ArgumentParser(
        description="Read CSI data from serial port and display it graphically")
    parser.add_argument('-p', '--port', dest='port', action='store', required=True,
                        help="Serial port number of csv_recv device")
    #parser.add_argument('-t', '--port2', dest='port2', action='store', required=True,
    #                    help="Second Serial port number of csv_recv device")
    parser.add_argument('-s', '--store', dest='store_file', action='store', default='./csi_data.csv',
                        help="Save the data printed by the serial port to a file")

    args = parser.parse_args()
    serial_port = args.port

    if hasattr(args, "port2"):
        serial_port2 = args.port2
    else:
        serial_port2 = ""

    file_name = args.store_file
    file_name2 = args.store_file + '2'

    app = QApplication(sys.argv)
    window = csi_data_graphical_window()
    window.show()

    subthread = SubThread(serial_port, file_name)
    subthread.start()

    if serial_port2:
        subthread2 = SubThread2(serial_port2, file_name2)
        subthread2.start()

    sys.exit(app.exec())
