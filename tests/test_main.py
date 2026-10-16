"""Модульные тесты для проверки логики работы эмулятора VFS."""

import unittest
import xml.etree.ElementTree as ET
import os
from src.main import VFSEmulator


class TestVFSEmulatorLogic(unittest.TestCase):
    """Тесты основных и дополнительных команд VFS."""

    def setUp(self):
        """Создание фиктивной конфигурации и структуры VFS для тестов."""
        self.vfs_xml = "test_vfs.xml"
        self.vfs_xml2 = "test_vfs2.xml"
        self.config_xml = "test_config.xml"

        # Основной образ VFS для базовых тестов
        with open(self.vfs_xml, "w", encoding="utf-8") as f:
            f.write(
                '<vfs name="TestVFS"><dir name="root">'
                '<dir name="home"></dir>'
                '<file name="a.txt">MQoyCjMKNAo1</file>'
                "</dir></vfs>"
            )

        # Второй образ VFS для теста команды vfs-load
        with open(self.vfs_xml2, "w", encoding="utf-8") as f:
            f.write(
                '<vfs name="NewLoadedVFS"><dir name="root">'
                '<dir name="bin"></dir>'
                "</dir></vfs>"
            )

        with open(self.config_xml, "w", encoding="utf-8") as f:
            f.write(
                f"<config><vfs_path>{self.vfs_xml}</vfs_path></config>"
            )

        # Инициализируем эмулятор
        self.app = VFSEmulator(self.vfs_xml, None)

    def tearDown(self):
        """Удаление временных файлов после выполнения тестов."""
        for path in [self.vfs_xml, self.vfs_xml2, self.config_xml]:
            if os.path.exists(path):
                os.remove(path)

    def test_ls_command(self):
        """Проверка корректности вывода содержимого директории."""
        res = self.app.execute_command("ls")
        self.assertIn("home/", res)
        self.assertIn("a.txt", res)

    def test_cd_command(self):
        """Проверка навигации по виртуальным папкам."""
        self.app.execute_command("cd home")
        self.assertEqual(self.app.current_node.get("name"), "home")

    def test_who_command(self):
        """Проверка вывода имени текущего пользователя."""
        res = self.app.execute_command("who")
        self.assertIn(self.app.username, res)

    def test_tail_command(self):
        """Проверка чтения последних строк виртуального файла."""
        res = self.app.execute_command("tail a.txt")
        self.assertIn("5", res)

    def test_cp_command(self):
        """Проверка копирования виртуального файла в памяти."""
        self.app.execute_command("cp a.txt b.txt")
        res = self.app.execute_command("ls")
        self.assertIn("b.txt", res)

    def test_rm_command(self):
        """Проверка удаления файла из структуры VFS."""
        self.app.execute_command("rm a.txt")
        res = self.app.execute_command("ls")
        self.assertNotIn("a.txt", res)

    def test_env_vars_expansion(self):
        """Проверка раскрытия системных переменных окружения."""
        os.environ["TEST_DIR"] = "home"
        res = self.app.resolve_env_vars("$TEST_DIR")
        self.assertEqual(res, "home")

    def test_vfs_load_command(self):
        """Проверка динамической загрузки нового XML образа VFS."""
        res = self.app.execute_command(f"vfs-load {self.vfs_xml2}")
        self.assertIn("NewLoadedVFS", res)
        res_ls = self.app.execute_command("ls")
        self.assertIn("bin/", res_ls)


if __name__ == "__main__":
    unittest.main()
