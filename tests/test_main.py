"""Модульные тесты для проверки логики работы эмулятора VFS."""

import unittest
import xml.etree.ElementTree as ET
from src.main import VFSEmulator


class TestVFSEmulatorLogic(unittest.TestCase):
    """Тесты основных и дополнительных команд VFS."""

    def setUp(self):
        """Создание фиктивной конфигурации и структуры VFS для тестов."""
        self.vfs_xml = "test_vfs.xml"
        self.config_xml = "test_config.xml"

        with open(self.vfs_xml, "w", encoding="utf-8") as f:
            f.write(
                '<vfs><dir name="root">'
                '<dir name="home"></dir>'
                '<file name="a.txt">1\n2\n3\n4\n5</file>'
                "</dir></vfs>"
            )

        with open(self.config_xml, "w", encoding="utf-8") as f:
            f.write(
                f"<config><vfs_path>{self.vfs_xml}</vfs_path></config>"
            )

        self.app = VFSEmulator(self.config_xml)

    def test_ls_command(self):
        """Проверка корректности вывода содержимого директории."""
        items = [
            c.get("name") + ("/" if c.tag == "dir" else "")
            for c in self.app.current_node
        ]
        self.assertIn("home/", items)
        self.assertIn("a.txt", items)

    def test_cd_command(self):
        """Проверка навигации по виртуальным папкам."""
        self.app.cmd_cd(["home"])
        self.assertEqual(self.app.current_node.get("name"), "home")


if __name__ == "__main__":
    unittest.main()
