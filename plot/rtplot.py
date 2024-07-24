import sys
import time
from threading import Event, Thread

import numpy as np
import pyqtgraph as pg
import zmq
from PyQt5.QtWidgets import QApplication, QMainWindow

# 禁用科学记数法
np.set_printoptions(suppress=True)

class Suber(Thread):

    def __init__(self, address, topic=""):
        super().__init__(name=f"Suber Thread | address:{address}, topic:{topic}", daemon=True)
        self.address = address
        self.topic = topic
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect(self.address)
        self.socket.setsockopt_string(zmq.SUBSCRIBE, self.topic)
        self._stop_event = Event()
        self.message = None
        self.internal = 0
        self.timestamp = 0


    def run(self):
        print(f"Subscriber started, listening to {self.topic} on {self.address}")
        t1 = time.time()
        while not self._stop_event.is_set():
            try:
                message = self.socket.recv_string(flags=zmq.NOBLOCK)
                t2 = time.time()
                self.internal = t2 - t1
                self.timestamp += self.internal
                t1 = t2
                print(f"Received message on topic {self.topic}: {message} | {self.timestamp}")
                self.message = message
            except zmq.Again:
                pass


    def stop(self):
        self._stop_event.set()
        self.socket.close()
        self.context.term()
        print("Subscriber stopped")

suber = Suber("tcp://192.168.1.2:5556")
# suber = Suber("tcp://127.0.0.1:5556")
suber.start()





class PlotSubWindow:
    def __init__(self, title, callback, row, col, yRange, win):
        self.plot = win.addPlot(row, col, title=title)
        self.plot.setTitle(title)
        self.x_data = []
        self.y_data = []
        self.curve = self.plot.plot()

        # 添加显示最大值和最小值的文本项
        self.max_text = pg.TextItem(anchor=(1, 1))
        self.min_text = pg.TextItem(anchor=(1, 0))
        self.plot.addItem(self.max_text)
        self.plot.addItem(self.min_text)

        # 设置y轴的初始范围
        if yRange is not None:
            self.plot.setYRange(*yRange)

        self.callback = callback

    def update(self):

        x, y = self.callback()

        if x is None or y is None:
            return
        # 存储新数据点
        self.x_data.append(x)
        self.y_data.append(y)
        
        # 更新曲线的数据
        self.curve.setData(self.x_data, self.y_data)

        # 更新最大值和最小值的显示
        if self.y_data:
            max_y = max(self.y_data)
            min_y = min(self.y_data)
            self.max_text.setText(f'Max: {max_y:.2f}')
            self.min_text.setText(f'Min: {min_y:.2f}')
            self.max_text.setPos(self.x_data[-1], max_y)
            self.min_text.setPos(self.x_data[-1], min_y)

            # 更新y轴的范围
            self.plot.setYRange(min_y, max_y)




class RealTimePlot(QMainWindow):
    
    def __init__(self,title, msec):
        super().__init__()
        self.win = pg.GraphicsLayoutWidget(show=True)
        self.setWindowTitle(title)
        self.setCentralWidget(self.win)
        self._plots = {}


        # 设置一个计时器来调用更新函数
        self.timer = pg.QtCore.QTimer()
        self.timer.start(msec)  # 每100毫秒更新一次


    def addSubWindow(self, title, callback, row, col,  yRange=None):
        subWindow = self.createSubWindow(title, callback, row, col, yRange)
        self._plots.update({title: subWindow})
        self.timer.timeout.connect(subWindow.update)
        return subWindow
        

    def delSubWindow(self, title):
        if title in self._plots.keys():
            self._plots.pop(title)
    

    def createSubWindow(self, title, callback, row, col, yRange=None):
       subWindow = PlotSubWindow(title, callback,  row, col, yRange, self.win)
       return subWindow


    def getSubWindow(self, title):
        return self._plots.get(title, None)

    
# TODO:增加数据保存


if __name__ == '__main__':
    app = QApplication(sys.argv)
    # ex = RealTimePlot((-15, 15), callback=lambda: (float(suber.timestamp), float(suber.message.split(",")[0])))
    # ex.show()
    # exit = app.exec_()
    # # values = np.column_stack(ex.x_data, ex.y_data)
    # # np.savetxt("values.txt",values)
    # sys.exit(exit)

    rtPlot = RealTimePlot("数据", 100)
    rtPlot.addSubWindow("t1", lambda: (float(suber.timestamp), float(suber.message.split(",")[0])), 1,1)
    rtPlot.addSubWindow("t2", lambda: (float(suber.timestamp), float(suber.message.split(",")[1])), 2,1)
    # rtPlot.addSubWindow("t3", lambda:(round(time.time(), 6),3), 2,1)
    # rtPlot.addSubWindow("t4", lambda:(round(time.time(), 6),4), 2,2)
    rtPlot.show()
    sys.exit(app.exec_())
