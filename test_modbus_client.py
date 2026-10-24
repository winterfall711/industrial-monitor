
import unittest
from unittest.mock import Mock

from modbus_client import read_equipment_data


class TestReadEquipmentData(unittest.TestCase):

    def test_successful_read(self):
        """正常读取三个寄存器。"""
        response = Mock()
        response.isError.return_value = False
        response.registers = [6325, 1200, 3250]

        client = Mock()
        client.read_holding_registers.return_value = response

        result = read_equipment_data(client)

        self.assertEqual(result["temperature"], 63.25)
        self.assertEqual(result["speed"], 1200)
        self.assertEqual(result["torque"], 32.5)

        client.read_holding_registers.assert_called_once_with(
            address=0,
            count=3,
            slave=1,
        )

    def test_no_response(self):
        """服务器没有返回响应。"""
        client = Mock()
        client.read_holding_registers.return_value = None

        with self.assertRaisesRegex(RuntimeError, "没有返回响应"):
            read_equipment_data(client)

    def test_error_response(self):
        """服务器返回 Modbus 异常响应。"""
        response = Mock()
        response.isError.return_value = True

        client = Mock()
        client.read_holding_registers.return_value = response

        with self.assertRaisesRegex(RuntimeError, "异常响应"):
            read_equipment_data(client)

    def test_insufficient_registers(self):
        """返回的寄存器数量不足。"""
        response = Mock()
        response.isError.return_value = False
        response.registers = [6325, 1200]

        client = Mock()
        client.read_holding_registers.return_value = response

        with self.assertRaisesRegex(ValueError, "数据不足"):
            read_equipment_data(client)


if __name__ == "__main__":
    unittest.main(verbosity=2)
