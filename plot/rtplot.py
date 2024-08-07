from re import X
import sys
from threading import Event, Thread
import time
from typing import Callable
from PyQt5.QtWidgets import QApplication, QMainWindow

import pyqtgraph as pg
import numpy as np
import zmq

# 禁用科学记数法
np.set_printoptions(suppress=True)

class Suber(Thread):
    """
        基于zmq PUB的SUB线程实现
    """
    def __init__(self, address: str, topic: str=""):
        """
            订阅zmq 的 PUB 发送的数据

        Args:
            address (str): 订阅地址. 例如:  tcp://192.168.40.241:5556
            topic (str, optional): 如果PUB指定那么SUB也需要指定. Defaults to "".
        """
        super().__init__(name=f"Suber Thread | address:{address}, topic:{topic}", daemon=True)
        self.address = address
        self.topic = topic
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect(self.address)
        self.socket.setsockopt_string(zmq.SUBSCRIBE, self.topic)
        self._stop_event = Event()
        self.message = "0,0,0"
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
        """
            停止SUB的后台线程
        """
        self._stop_event.set()
        self.socket.close()
        self.context.term()
        print("Subscriber stopped")



class PlotSubWindow:
    """
        实时绘制子窗口类
    """
    def __init__(self, title: str, callback: Callable, row: int, col: int, yRange: tuple, win:pg.GraphicsLayoutWidget):
        """
        _summary_

        Args:
            title (str): 窗口title
            callback (Callable): 获取数据回调函数,该回调函数在每个时间周期内调用,并且该回调应该返回该子窗口上x和y对应的数据
            row (int): 在主窗口上的行位置
            col (int): 在主窗口上的列位置
            yRange (tuple, optional): 初始Y轴的区间. Defaults to None.
            win (pg.GraphicsLayoutWidget): 子窗口要添加到的主窗口
        """
        self.plot = win.addPlot(row, col, title=title)
        self.plot.setTitle(title, size="20pt")
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
        """
            数据更新
        """
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
    """
        实时接收数据plot
    """
    def __init__(self,title:str, msec:int):
        """
        Args:
            title (str): 窗口的名册很难过
            msec (int): 数据刷新频率,单位:ms
        """
        super().__init__()
        self.win = pg.GraphicsLayoutWidget(show=True)
        self.setWindowTitle(title)
        self.setCentralWidget(self.win)
        self._plots = {}


        # 设置一个计时器来调用更新函数
        self.timer = pg.QtCore.QTimer()
        self.timer.start(msec)  # 每100毫秒更新一次


    def addSubWindow(self, title: str, callback:Callable, row: int, col: int,  yRange: tuple=None) -> PlotSubWindow:
        """
            添加一个子窗口

        Args:
            title (str): 窗口title
            callback (Callable): 获取数据回调函数,该回调函数在每个时间周期内调用,并且该回调应该返回该子窗口上x和y对应的数据
            row (int): 在主窗口上的行位置
            col (int): 在主窗口上的列位置
            yRange (tuple, optional): 初始Y轴的区间. Defaults to None.

        Returns:
            PlotSubWindow: 创建的子窗口
        """
        subWindow = self.createSubWindow(title, callback, row, col, yRange)
        self._plots.update({title: subWindow})
        self.timer.timeout.connect(subWindow.update)
        return subWindow
        

    def delSubWindow(self, title: str) -> None:
        """
            删除子窗口

        Args:
            title (str): 要删除的子窗口名称
        """
        if title in self._plots.keys():
            self._plots.pop(title)
    

    def createSubWindow(self, title: str, callback: Callable, row: int, col: int, yRange: tuple=None) -> PlotSubWindow:
        """
        创建一个子窗口

        Args:
            title (str): 窗口name
            callback (Callable): 回调
            row (int): 行号
            col (int): 列号
            yRange (tuple, optional): 设置y轴的初始区间. Defaults to None.

        Returns:
            PlotSubWindow: 子窗口
        """
        subWindow = PlotSubWindow(title, callback,  row, col, yRange, self.win)
        return subWindow


    def getSubWindow(self, title: str):
        """
        _summary_

        Args:
            title (str): _description_

        Returns:
            _type_: _description_
        """
        return self._plots.get(title, None)

    
# TODO:增加数据保存


if __name__ == '__main__':
    # suber = Suber("tcp://192.168.1.2:5556")
    suber = Suber("tcp://192.168.40.241:5556")
    # suber = Suber("tcp://127.0.0.1:5556")
    suber.start()
    app = QApplication(sys.argv)


    rtPlot = RealTimePlot("数据", 100)
    rtPlot.addSubWindow("X", lambda: (float(suber.timestamp), float(suber.message.split(",")[0])), 1,1)
    rtPlot.addSubWindow("Y", lambda: (float(suber.timestamp), float(suber.message.split(",")[1])), 2,1)
    rtPlot.addSubWindow("Z", lambda: (float(suber.timestamp), float(suber.message.split(",")[2])), 3,1)
    # rtPlot.addSubWindow("t3", lambda:(round(time.time(), 6),3), 2,1)
    # rtPlot.addSubWindow("t4", lambda:(round(time.time(), 6),4), 2,2)
    rtPlot.show()
    sys.exit(app.exec_())
