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
from pyqtgraph import PlotWidget
from PyQt5 import QtCore
import pyqtgraph as pq

import threading
import time

stopme = 0

# Reduce displayed waveforms to avoid display freezes
#CSI_VAID_SUBCARRIER_INTERVAL = 3
CSI_VAID_SUBCARRIER_INTERVAL = 2
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

#csi_vaid_subcarrier_index += [i for i in range(3*MAX_SHADES +6, 4*MAX_SHADES +6, CSI_VAID_SUBCARRIER_INTERVAL)]     # 26  red
#csi_vaid_subcarrier_color += [(128, 128, i * color_step +70) for i in range(0,  MAX_SHADES // CSI_VAID_SUBCARRIER_INTERVAL + 1) ]

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

CSI_DATA_INDEX = 100  # buffer size
CSI_DATA_COLUMNS = len(csi_vaid_subcarrier_index)
DATA_COLUMNS_NAMES = ["type", "id", "mac", "rssi", "rate", "sig_mode", "mcs", "bandwidth", "smoothing", "not_sounding", "aggregation", "stbc", "fec_coding",
                      "sgi", "noise_floor", "ampdu_cnt", "channel", "secondary_channel", "local_timestamp", "ant", "sig_len", "rx_state", "len", "first_word", "data"]
#csi_data_array = np.zeros(
#    [CSI_DATA_INDEX, CSI_DATA_COLUMNS], dtype=np.complex64)
csi_data_array = np.zeros(
    [CSI_DATA_INDEX, CSI_DATA_COLUMNS], dtype=np.float64)

csi_data_array2 = np.zeros(
    [CSI_DATA_INDEX, CSI_DATA_COLUMNS], dtype=np.float64)

class FormWidget(QWidget):

    def __init__(self, parent):
        super(FormWidget, self).__init__(parent)
        self.layout = QVBoxLayout(self)

        self.button1 = QPushButton("Button 1")
        self.layout.addWidget(self.button1)

        self.button2 = QPushButton("Button 2")
        self.layout.addWidget(self.button2)

        self.setLayout(self.layout)

class csi_data_graphical_window(QMainWindow):
    def __init__(self):
        super().__init__()

        self.resize(1280, 720)
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

        self.setWindowTitle(serial_port + ' + ' + serial_port2)

        self.plotWidget_ted = PlotWidget(self)
        #self.plotWidget_ted.setGeometry(QtCore.QRect(0, 0, 1280, 720))
        self.plotWidget_ted.setYRange(-100, 100)
        self.plotWidget_ted.addLegend((10,1))

        self.plotWidget_ted2 = PlotWidget(self)
        #self.plotWidget_ted2.setGeometry(QtCore.QRect(0, 0, 1280, 720))
        self.plotWidget_ted2.setYRange(-100, 100)
        self.plotWidget_ted2.addLegend((10,1))

        self.main = QWidget(self)
        self.main_layout = QVBoxLayout(self.main)
        self.main_layout.addWidget(self.plotWidget_ted)
        #self.main_layout.addWidget(self.plotWidget_ted2)
        #self.setLayout(self.main_layout)
        self.setCentralWidget(self.main)

        #self.csi_phase_array = csi_data_array
        self.curve_list = []

        #print(f"csi_vaid_subcarrier_color, len: {len(csi_vaid_subcarrier_color)}, {csi_vaid_subcarrier_color}")

        for i in range(CSI_DATA_COLUMNS):
            curve = self.plotWidget_ted.plot(
                csi_data_array[:, i],
                        name=str(i) + ' ' + str(i*CSI_VAID_SUBCARRIER_INTERVAL),
                    pen=csi_vaid_subcarrier_color[i])
            self.curve_list.append(curve)

        self.csi_phase_array2 = csi_data_array2
        self.curve_list2 = []

        #for i in range(CSI_DATA_COLUMNS):
        #    curve = self.plotWidget_ted2.plot(
        #        self.csi_phase_array2[:, i],
        #                name=str(i) + ' ' + str(i*CSI_VAID_SUBCARRIER_INTERVAL),
        #            pen=csi_vaid_subcarrier_color[i])
        #    self.curve_list2.append(curve)

        self.timer = pq.QtCore.QTimer()
        self.timer.timeout.connect(self.update_data)
        self.timer.start(100)

        #self.timer2 = pq.QtCore.QTimer()
        #self.timer2.timeout.connect(self.update_data2)
        #self.timer2.start(100)

    def update_data(self):
        #print(csi_data_array.shape)

        #self.csi_phase_array = np.abs(csi_data_array)
        #self.csi_phase_array = csi_data_array
        #self.csi_phase_array[-1] = np.array([np.real(csi_data_array[-1]),
        #         np.imag(csi_data_array[-1])])
        #self.csi_phase_array[1] = np.copy(csi_data_array[1])
        #print(self.csi_phase_array)

        for i in range(CSI_DATA_COLUMNS):
            self.curve_list[i].setData(csi_data_array[:, i])

        if stopme:
            #print("stopme")
            subthread = []

            sys.exit()
            #return True

def csi_data_read_parse(port: str, csv_writer, outdata):

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
        print("open failed")
        return

    while True:
        strings = str(ser.readline())
        if not strings:
            break

        strings = strings.lstrip('b\'').rstrip('\\r\\n\'')
        index = strings.find('CSI_DATA')

        if index == -1:
            continue

        csv_reader = csv.reader(StringIO(strings))
        csi_data = next(csv_reader)

        if len(csi_data) != len(DATA_COLUMNS_NAMES):
            print("element number is not equal")
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

        # Rotate data to the left
        #csi_data_array[:-1] = csi_data_array[1:]
        outdata[:-1] = outdata[1:]

        if len(csi_raw_data) == 128:
            csi_vaid_subcarrier_len = CSI_DATA_LLFT_COLUMNS
        else:
            csi_vaid_subcarrier_len = CSI_DATA_COLUMNS

        for i in range(csi_vaid_subcarrier_len):
            #csi_data_array[-1][i] = complex(csi_raw_data[csi_vaid_subcarrier_index[i] * 2],
            #                                csi_raw_data[csi_vaid_subcarrier_index[i] * 2 - 1])

            # simpler data representation
            outdata[-1][i] = csi_raw_data[csi_vaid_subcarrier_index[i] * 2]
            #csi_data_array[-1][i] = csi_raw_data[csi_vaid_subcarrier_index[i] * 2 - 1]

            #try:
            #    csi_data_array[-1][i] = \
            #        csi_raw_data[csi_vaid_subcarrier_index[i] * 2] / \
            #            csi_raw_data[csi_vaid_subcarrier_index[i] * 2  - 1]
            #except:
            #    pass
            #    csi_data_array[-1][i] = 0

            #csi_data_array[-1][i] = complex(0,
            #                                csi_raw_data[csi_vaid_subcarrier_index[i] * 2 - 1])
            #csi_data_array[-1][i] = complex(csi_raw_data[csi_vaid_subcarrier_index[i] * 2],
            #                                0)

    ser.close()
    return


class SubThread (QThread):
    def __init__(self, serial_port, save_file_name):
        super().__init__()
        self.serial_port = serial_port

        save_file_fd = open(save_file_name, 'w')
        self.csv_writer = csv.writer(save_file_fd)
        self.csv_writer.writerow(DATA_COLUMNS_NAMES)

    def run(self):
        csi_data_read_parse(self.serial_port, self.csv_writer, csi_data_array)

    def __del__(self):
        self.wait()

class SubThread2 (QThread):
    def __init__(self, serial_port, save_file_name):
        super().__init__()
        self.serial_port = serial_port

        save_file_fd = open(save_file_name, 'w')
        self.csv_writer = csv.writer(save_file_fd)
        self.csv_writer.writerow(DATA_COLUMNS_NAMES)

    def run(self):
        csi_data_read_parse(self.serial_port, self.csv_writer, csi_data_array2)

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
    parser.add_argument('-t', '--port2', dest='port2', action='store', required=True,
                        help="Second Serial port number of csv_recv device")
    parser.add_argument('-s', '--store', dest='store_file', action='store', default='./csi_data.csv',
                        help="Save the data printed by the serial port to a file")

    args = parser.parse_args()
    serial_port = args.port
    serial_port2 = args.port2

    file_name = args.store_file
    file_name2 = args.store_file + '2'

    app = QApplication(sys.argv)

    subthread = SubThread(serial_port, file_name)
    subthread.start()

    subthread2 = SubThread2(serial_port2, file_name2)
    subthread2.start()

    window = csi_data_graphical_window()
    window.show()

    sys.exit(app.exec())
