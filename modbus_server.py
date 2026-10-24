import pymodbus

print("PyModbus 版本：", pymodbus.__version__)

import threading
import time

from pymodbus.datastore import (
    ModbusSequentialDataBlock,
    ModbusSlaveContext,
    ModbusServerContext,
)
from pymodbus.server import StartTcpServer
from simulator import EquipmentSimulator
#1.初始化设备模拟器
euipment=EquipmentSimulator()

#2.创建modbus寄存器
store=ModbusSlaveContext(
    di=ModbusSequentialDataBlock(0,[0]*10),
    co=ModbusSequentialDataBlock(1,[0]*10),
    hr=ModbusSequentialDataBlock(
        0,
        [6325,1200,3250]+[0]*97,
    ),
    ir=ModbusSequentialDataBlock(0,[0]*10),
    zero_mode=True,
)
context = ModbusServerContext(
    slaves=store,
    single=True,
)

#3.更新设备寄存器
def update_equipment():
    while True:
        #从模拟器获得最新数据
        data=euipment.generate_data()
        #转换为寄存器整数
        registers=[
            round(data['temperature']*100),
            int(data['speed']),
            round(data['torque']*100),
        ]
        #更新寄存器
        store.setValues(
            3,
            0,
            registers,
        )

        print(
            f"[Server]"
            f"温度:{data['temperature']:.2f} 摄氏度 |"
            f"转速:{data['speed']} rpm|"
            f"扭矩:{data['torque']:.2f}N·m",
            flush=True,
        )
        time.sleep(1)

        #4.启动modbus tcp服务端
def main():
    print("Modbus TCP Server Started")
    print("IP:127.0.0.1")
    print("Port:5020")
    #后台启动数据更新任务
    thread=threading.Thread(
        target=update_equipment,
        daemon=True,
    )

    thread.start()
    #启动TCP服务端
    StartTcpServer(
        context=context,
        address=("127.0.0.1", 5020),
    )

if __name__ == "__main__":
    main()