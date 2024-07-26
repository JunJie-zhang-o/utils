#!/usr/bin/env python3
# coding=utf-8
'''
Author       : Jay jay.zhangjunjie@outlook.com
Date         : 2024-07-18 11:24:52
LastEditTime : 2024-07-26 20:19:54
LastEditors  : Jay jay.zhangjunjie@outlook.com
Description  : 显示触觉传感器对应法向力和切向力,其中法向力为高和底面半径,在根据切向力大小求出合力方向
'''
from queue import Queue
import time
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib import cm
import fire
import zmq
import math

from threading import Thread



class ForcePlot:
    """
        订阅数据并3D plot

        How to use

            python p6.py show                               # 使用默认参数ip=127.0.0.1 port=5555启动

            python p6.py show --ip="127.0.0.1"              # 指定ip
            python p6.py show --ip="127.0.0.1" --port==5555 # 指定ip和端口
    """

    def __init__(self, ip: str="127.0.0.1", port: int=5555) -> None:
        self.fig = plt.figure()
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.ax.set_xlim(-5,5)
        self.ax.set_ylim(-5, 5)
        self.ax.set_zlim(-5, 5)
        self.suber = zmq.Context().socket(zmq.SUB)
        self.suber.connect(f"tcp://{ip}:{port}")
        self.suber.setsockopt_string(zmq.SUBSCRIBE, "")
    

        self._suberTHread = Thread(target=self.suberThreadFunc, name="ForcePlotThread", daemon=True)
        self._suberTHread.start()

        self.norm = plt.Normalize(0, 5)

    
    def suberThreadFunc(self):
        while True:
            recv = self.suber.recv_string()
            print(f"Q:{self._q.qsize()}")
            if recv is None:
                continue
            # self._q.
            self.recv = recv


    def _calculate(self, normalF, tangentialF):
        normalRatio = 1
        tangentailRatio = 1
        return [normalF * normalRatio, tangentialF * tangentailRatio]
       

    def _updata(self, frame):
        self.t1 = time.time()
        if not self._q.empty():

            recv = self.recv        # x, y, z
            print(f"Recv:{recv}")
            if recv is None:
                NF, TF, H = 0,0,0
            else:
                [NF, TF, H] = [float(i) for i in recv.split(',')]
                H = 3 * H
                if H < 0:
                    H = 0
            
            H = H * 5
            x, y, z, x_top, y_top, z_top = self._generateCone(NF, TF, H)

            # 获取当前的轴范围
            xlim = self.ax.get_xlim()
            ylim = self.ax.get_ylim()
            zlim = self.ax.get_zlim()
            self.ax.clear()

            vector = np.sqrt(x_top**2+y_top**2+z_top**2)
            print(f"Vector:{vector}")
            # norm = plt.Normalize(z.min(), z.max())
            
            colors = cm.viridis(self.norm(np.full_like(z, vector)))


            self.ax.plot_surface(x, y, z, facecolors=colors, alpha=0.4)
            # 顶点
            self.ax.plot([x_top], [y_top], [z_top], 'ro')
            # 绘制箭头
            self.ax.quiver(0, 0, 0, x_top, y_top, z_top, color='r', arrow_length_ratio=0.1)

            
            # 重新设置轴范围
            self.ax.set_xlim(xlim)
            self.ax.set_ylim(ylim)
            self.ax.set_zlim(zlim)
            self.t2 = time.time()
            print(f"T:{self.t2 - self.t1}")
            self.t1 = self.t2
        


    def _generateCone(self, NF, TF, H):
        # 生成圆的底面
        t = np.linspace(0, 2 * np.pi, 100)
        # r = np.linspace(0, NF, 50)
        # r = np.linspace(0, np.sqrt(NF*NF+TF*TF), 50)
        r = np.linspace(0, H/2, 50)
        # r = np.linspace(0, 0.5, 50)
        T, R = np.meshgrid(t, r)
        X = R * np.cos(T)
        Y = R * np.sin(T)
        Z = np.zeros_like(X)
        
        # 生成圆锥顶点
        x_top, y_top = self._calculate(NF, TF)
        # x_top = TF * np.sin(Theta)
        z_top = H
        # z_top = TF * np.cos(Theta)
        
        # 插入顶点数据
        X = np.vstack([X, np.full_like(t, x_top)])
        Y = np.vstack([Y, np.full_like(t, y_top)])
        Z = np.vstack([Z, np.full_like(t, z_top)])
        # print(x_top, y_top, z_top)
        return X, Y, Z, x_top, y_top, z_top



    def show(self, interval=1):
        # 创建动画
        self.ani = FuncAnimation(self.fig, self._updata, frames=np.arange(0, 360, 1), interval=interval, blit=False)


        # 获取当前图形并连接鼠标事件
        def on_scroll(event):
            scale_factor = 1.1
            if event.button == 'up':
                scale_factor = 1 / scale_factor
            self.ax.set_xlim([scale_factor * x for x in self.ax.get_xlim()])
            self.ax.set_ylim([scale_factor * y for y in self.ax.get_ylim()])
            self.ax.set_zlim([scale_factor * z for z in self.ax.get_zlim()])
            plt.draw()

        self.fig.canvas.mpl_connect('scroll_event', on_scroll)


        # 添加颜色条
        self.mappable = cm.ScalarMappable(norm=self.norm, cmap=cm.viridis)

        self.cbar = self.fig.colorbar(self.mappable, ax=self.ax, shrink=0.5, aspect=5)

        # 启用交互模式
        plt.ion()

        # 启用工具栏
        plt.show()
        plt.show(block=True)




if __name__ == "__main__":
    # fire.Fire(ForcePlot)
    p = ForcePlot(ip="192.168.1.2",port=5556)
    # p = ForcePlot(port=5556)
    p.show()
