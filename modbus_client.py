
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


def read_equipment_data(client):
    """读取并校验设备的三个 Modbus 寄存器。"""

    response = client.read_holding_registers(
        address=0,
        count=3,
        slave=1,
    )

    if response is None:
        raise RuntimeError("Modbus 没有返回响应。")

    if response.isError():
        raise RuntimeError(
            f"Modbus 返回异常响应：{response!r}"
        )

    registers = getattr(response, "registers", None)

    if registers is None or len(registers) < 3:
        raise ValueError(
            f"寄存器数据不足：{registers!r}"
        )

    return {
        "temperature": registers[0] / 100,
        "speed": registers[1],
        "torque": registers[2] / 100,
    }


def reconnect_client(client):
    """服务端断开后，持续尝试重新连接。"""
    client.close()

    while True:
        time.sleep(2)
        print("正在尝试重新连接 Modbus TCP 服务器...")

        try:
            if client.connect():
                print("Modbus TCP 重连成功，恢复数据采集。")
                return

            print("连接失败，2 秒后继续重试。")

        except Exception as e:
            print(f"重连失败：{e!r}")
            print("连接失败，2 秒后继续重试。")

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

            while True:
                try:
                    # 1. 读取并校验设备数据
                    equipment_data = read_equipment_data(client)

                except Exception as e:
                    print(f"读取失败：{e!r}")
                    print("开始尝试恢复连接，请稍等。")
                    reconnect_client(client)
                    continue

                # 2. 添加时间戳
                data = {
                    "timestamp": datetime.now().isoformat(
                        timespec="seconds"
                    ),
                    "temperature": equipment_data["temperature"],
                    "speed": equipment_data["speed"],
                    "torque": equipment_data["torque"],
                }

                # 3. 保存到 CSV
                save_data(data)

                # 4. 显示采集结果
                print(
                    f"时间：{data['timestamp']} | "
                    f"温度：{data['temperature']:.2f} 摄氏度 | "
                    f"转速：{data['speed']} rpm | "
                    f"扭矩：{data['torque']:.2f} N·m"
                )

                time.sleep(1)

    except KeyboardInterrupt:
        print("\n数据采集已经停止。")

    finally:
        client.close()


if __name__ == "__main__":
    main()
