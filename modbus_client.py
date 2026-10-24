
import csv
import time

from datetime import datetime
from pathlib import Path

from pymodbus.client import ModbusTcpClient


# =====================================
# 1. 配置数据存储路径
# =====================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CSV_FILE = DATA_DIR / "equipment_data.csv"


# =====================================
# 2. 保存采集数据
# =====================================

def save_data(data):

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_exists = CSV_FILE.exists()

    with CSV_FILE.open(
        mode="a",
        newline="",
        encoding="utf-8-sig",
    ) as file:

        fieldnames = [
            "timestamp",
            "temperature",
            "speed",
            "torque",
        ]

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        if not file_exists or CSV_FILE.stat().st_size == 0:
            writer.writeheader()

        writer.writerow(data)


# =====================================
# 3. 连接 Modbus TCP 服务端
# =====================================

def main():

    client = ModbusTcpClient(
        host="127.0.0.1",
        port=5020,
        timeout=3,
    )

    try:

        if not client.connect():
            print("连接失败，请检查服务端。")
            return

        print("Modbus TCP 连接成功！")
        print("开始采集，按 Ctrl+C 停止。\n")

        while True:

            # 读取三个保持寄存器
            try:
                response = client.read_holding_registers(
                    address=0,
                    count=3,
                    slave=1,
                )

            except Exception as e:
                print("读取请求异常：", repr(e))
                time.sleep(1)
                continue

            # 检查 Modbus 响应
            if response.isError():
                print("读取失败！")
                print("响应类型：", type(response).__name__)
                print("响应内容：", repr(response))

                if hasattr(response, "exception_code"):
                    print(
                        "异常代码：",
                        response.exception_code,
                    )

                time.sleep(1)
                continue

            # 检查寄存器数量
            registers = response.registers

            if len(registers) < 3:
                print("寄存器数量不足：", registers)
                time.sleep(1)
                continue

            # 转换为工程量
            temperature = registers[0] / 100
            speed = registers[1]
            torque = registers[2] / 100

            # 整理采集记录
            data = {
                "timestamp": datetime.now().isoformat(
                    timespec="seconds"
                ),
                "temperature": temperature,
                "speed": speed,
                "torque": torque,
            }

            # 保存 CSV
            save_data(data)

            # 输出采集结果
            print(
                f"时间：{data['timestamp']} | "
                f"温度：{temperature:.2f} ℃ | "
                f"转速：{speed} rpm | "
                f"扭矩：{torque:.2f} N·m"
            )

            time.sleep(1)

    except KeyboardInterrupt:
        print("\n数据采集已经停止。")

    finally:
        client.close()


if __name__ == "__main__":
    main()
