import random
import time

class EquipmentSimulator:
    """工业设备运行数据模拟器"""
    def __init__(self):
        #初始化模拟设备的运行参数
        self.temperature=63.25
        self.speed=1200
        self.torque=32.50
    def generate_data(self):
        """生成一组新的设备运行数据"""
        #温度小幅度波动
        self.temperature +=random.uniform(-0.2,0.2)
        self.temperature =max(
            58,
            min(68,self.temperature)
        )
        #转速小幅度波动
        self.speed +=random.randint(-3,3)
        self.speed=max(
            1180,
            min(1220,self.speed)
        )

        #扭矩小幅度波动
        self.torque +=random.uniform(-0.4,0.4)
        self.torque=max(
            28,
            min(36,self.torque)
        )
        #返回本次生成的数据
        return{
            "temperature":round(self.temperature,2),
            "speed":self.speed,
            "torque":round(self.torque,2),
        }

def main():
  """独立测试数据模拟器"""
  equipment=EquipmentSimulator()

  try:
      while True:
          data=equipment.generate_data()
          print(
              f"温度:{data['temperature']:.2f}摄氏度|"
              f"转速:{data['speed']} rpm|"
              f"扭矩:{data['torque']:.2f}N·m"
          )
          time.sleep(1)
  except KeyboardInterrupt:
      print("\n模拟器停止")

if __name__ == "__main__":
    main()