#!/usr/bin/env python3
# -*-coding:utf-8-*-

import queue
from PyQt5.Qt import *

local_queue = queue.Queue()

# Call this from QT timer wih the text  window to paint to

def worker(logwin):

    if local_queue.empty():
        return

    while True:
        try:
            item = local_queue.get(False)
        except queue.Empty:
            #return
            break

        if not item:
            return

        logwin.update()
        logwin.moveCursor(QTextCursor.End)
        logwin.insertPlainText(item)
        logwin.ensureCursorVisible()

    # Check for overflow
    txt = logwin.toPlainText()
    if len(txt) > 3000:
        logwin.clear()
        logwin.insertPlainText(txt[1500:])

    local_queue.task_done()


# imitate some features of the default print

def print(*strx, **keyw):

    sss = ""
    for aa in strx:
       sss += str(aa) + ' '

    if 'end' in keyw:
        sss += keyw['end']
    else:
        sss += '\n'

    # submit for aync processing
    local_queue.put(sss)
