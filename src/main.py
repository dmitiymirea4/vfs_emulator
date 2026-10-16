import os
import sys
import argparse
import xml.etree.ElementTree as ET
import base64
import re
import tkinter as tk
from tkinter import scrolledtext

class VFSEmulator:
    def __init__(self, vfs_path, script_path):
        self.vfs_path = vfs_path
        self.script_path = script_path
        self.vfs_name = "VirtualFS"
        self.root = None
        self.current_node = None
        self.username = os.getlogin() if hasattr(os, 'getlogin') else "user"
        
        self.load_vfs(vfs_path)

    def load_vfs(self, path):
        """Этап 3 & Этап 5: Загрузка VFS из XML в оперативную память"""
        try:
            tree = ET.parse(path)
            self.root = tree.getroot()
            self.vfs_name = self.root.get("name", "VirtualFS")
            # Корневой тег <vfs>, внутри него ищем первый <dir name="root"> или берем сам корень
            root_dir = self.root.find("dir")
            self.current_node = root_dir if root_dir is not None else self.root
        except Exception as e:
            print(f"Ошибка загрузки VFS: {e}")
            sys.exit(1)

    def resolve_env_vars(self, text):
        """Этап 1, Требование 3: Раскрытие переменных окружения ($HOME и др.)"""
        def replacer(match):
            var_name = match.group(1)
            return os.environ.get(var_name, f"${var_name}")
        return re.sub(r'\$(\w+)', replacer, text)

    def get_node_by_path(self, path_str):
        """Вспомогательный метод навигации по виртуальному дереву"""
        if not path_str:
            return self.current_node
        
        parts = path_str.strip("/").split("/")
        start_node = self.current_node
        
        if path_str.startswith("/"):
            start_node = self.root.find("dir") or self.root
            parts = [p for p in parts if p and p != "root"]

        node = start_node
        for part in parts:
            if not part or part == ".":
                continue
            if part == "..":
                continue
            
            found = False
            for child in node.findall("dir"):
                if child.get("name") == part:
                    node = child
                    found = True
                    break
            if not found:
                return None
        return node

    def execute_command(self, command_line):
        """Парсер команд REPL: всегда передает в методы чистый список строк"""
        command_line = self.resolve_env_vars(command_line).strip()
        if not command_line:
            return ""
        
        parts = command_line.split()
        cmd = parts[0]
        args = parts[1:]

        commands = {
            "exit": self.cmd_exit,
            "clear": self.cmd_clear,
            "who": self.cmd_who,
            "ls": self.cmd_ls,
            "cd": self.cmd_cd,
            "tail": self.cmd_tail,
            "cp": self.cmd_cp,
            "rm": self.cmd_rm,
            "vfs-load": self.cmd_vfs_load
        }

        if cmd in commands:
            return commands[cmd](args)
        else:
            return f"vfs: {cmd}: команда не найдена\n"

    def cmd_exit(self, args):
        sys.exit(0)

    def cmd_clear(self, args):
        return "CLEAR_SIGNAL"

    def cmd_who(self, args):
        return f"{self.username}\n"

    def cmd_ls(self, args):
        target = self.current_node if not args else self.get_node_by_path(args[0])
        if target is None:
            return "ls: каталог не найден\n"
        
        result = []
        for child in target.findall("dir"):
            result.append(child.get("name") + "/")
        for child in target.findall("file"):
            result.append(child.get("name"))
        return "  ".join(result) + "\n" if result else ""

    def cmd_cd(self, args):
        if not args:
            return ""
        target = self.get_node_by_path(args[0])
        if target is None or target.tag != "dir":
            return f"cd: нет такого каталога: {args[0]}\n"
        self.current_node = target
        return ""

    def cmd_tail(self, args):
        if not args:
            return "tail: пропущен файл\n"
        filename = args[0]
        
        file_node = None
        for child in self.current_node.findall("file"):
            if child.get("name") == filename:
                file_node = child
                break
                
        if file_node is None:
            return f"tail: {filename}: файл не найден\n"
        
        try:
            content = base64.b64decode(file_node.text or "").decode('utf-8')
            lines = content.splitlines()
            return "\n".join(lines[-10:]) + "\n"
        except Exception:
            return "tail: ошибка чтения файла\n"

    def cmd_cp(self, args):
        if len(args) < 2:
            return "cp: пропущены аргументы\n"
        src, dest = args[0], args[1]
        
        src_node = None
        for child in self.current_node.findall("file"):
            if child.get("name") == src:
                src_node = child
                break
        if src_node is None:
            return f"cp: {src}: файл не найден\n"
        
        new_node = ET.Element("file", name=dest)
        new_node.text = src_node.text
        self.current_node.append(new_node)
        return ""

    def cmd_rm(self, args):
        if not args:
            return "rm: пропущен аргумент\n"
        target_name = args[0]
        for child in list(self.current_node):
            if child.get("name") == target_name:
                self.current_node.remove(child)
                return ""
        return f"rm: {target_name}: файл или каталог не найден\n"

    def cmd_vfs_load(self, args):
        if not args:
            return "vfs-load: пропущен путь\n"
        self.load_vfs(args[0])
        return f"Успешно загружена новая VFS: {self.vfs_name}\n"
class EmulatorGUI:
    """Этап 1: Графический интерфейс REPL с полем ввода снизу"""
    def __init__(self, emulator):
        self.emu = emulator
        self.root = tk.Tk()
        self.root.title(self.emu.vfs_name)
        self.root.geometry("700x450")
        
        # Область истории терминала (вывод результатов)
        self.terminal = scrolledtext.ScrolledText(
            self.root, bg="black", fg="white", font=("Courier", 12), state=tk.DISABLED
        )
        self.terminal.pack(fill=tk.BOTH, expand=True)
        
        # Контейнер для нижней строки ввода
        input_frame = tk.Frame(self.root, bg="black")
        input_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        # Метка приглашения пользователя (Prompt)
        self.prompt_label = tk.Label(
            input_frame, text=f"{self.emu.username}@vfs:~$ ", bg="black", fg="cyan", font=("Courier", 12)
        )
        self.prompt_label.pack(side=tk.LEFT)
        
        # Интерактивная строка ввода СНИЗУ
        self.entry = tk.Entry(
            input_frame, bg="black", fg="white", insertbackground="white", 
            font=("Courier", 12), bd=0, highlightthickness=0
        )
        self.entry.pack(fill=tk.X, side=tk.LEFT, expand=True)
        self.entry.bind("<Return>", self.handle_input)
        self.entry.focus_set()
        
        # Автоматический запуск стартового скрипта из Этапа 2
        if self.emu.script_path:
            self.root.after(100, self.run_startup_script)

    def write_to_terminal(self, text):
        """Вспомогательный метод безопасного вывода текста в историю"""
        self.terminal.config(state=tk.NORMAL)
        self.terminal.insert(tk.END, text)
        self.terminal.config(state=tk.DISABLED)
        self.terminal.see(tk.END)

    def handle_input(self, event):
        """Обработка ввода пользователя по нажатию Enter"""
        cmd_line = self.entry.get().strip()
        self.entry.delete(0, tk.END)
        
        if not cmd_line:
            return "break"
            
        # Логируем введенную команду в историю
        self.write_to_terminal(f"{self.emu.username}@vfs:~$ {cmd_line}\n")
        
        if cmd_line == "exit":
            self.root.quit()
            return "break"
            
        output = self.emu.execute_command(cmd_line)
        
        if output == "CLEAR_SIGNAL":
            self.terminal.config(state=tk.NORMAL)
            self.terminal.delete("1.0", tk.END)
            self.terminal.config(state=tk.DISABLED)
        else:
            self.write_to_terminal(output)
            
        return "break"

    def run_startup_script(self):
        """Этап 2, Требование 5: Логика построчного выполнения стартового скрипта"""
        if not os.path.exists(self.emu.script_path):
            return
        with open(self.emu.script_path, "r", encoding="utf-8") as f:
            for line in f:
                cmd = line.strip()
                if not cmd or cmd.startswith("#"):
                    continue
                self.write_to_terminal(f"{self.emu.username}@vfs:~$ {cmd}\n")
                output = self.emu.execute_command(cmd)
                
                # Если команда завершилась с ошибкой, немедленно прерываемся по ТЗ
                if "команда не найдена" in output or "ошибка" in output or "не найден" in output:
                    self.write_to_terminal(output)
                    self.write_to_terminal("Скрипт остановлен из-за ошибки.\n")
                    break
                
                if output != "CLEAR_SIGNAL":
                    self.write_to_terminal(output)


def parse_args():
    """Этап 2: Парсинг аргументов с приоритетом перед XML-конфигом"""
    parser = argparse.ArgumentParser(description="VFS Emulator")
    parser.add_argument("--vfs", help="Путь к файлу VFS XML")
    parser.add_argument("--script", help="Путь к стартовому скрипту")
    parser.add_argument("--config", help="Путь к конфигурационному файлу XML")
    args = parser.parse_args()

    vfs_path, script_path = None, None
    config_file = args.config or "config.xml"
    
    if os.path.exists(config_file):
        try:
            tree = ET.parse(config_file)
            root = tree.getroot()
            vfs_node = root.find("vfs_path")
            script_node = root.find("startup_script")
            if vfs_node is not None: vfs_path = vfs_node.text
            if script_node is not None: script_path = script_node.text
        except Exception:
            pass

    # Приоритет параметров из CLI (командная строка перебивает конфиг)
    if args.vfs: vfs_path = args.vfs
    if args.script: script_path = args.script

    if not vfs_path:
        print("Ошибка: Не задан путь к файлу VFS XML.")
        sys.exit(1)

    return vfs_path, script_path


if __name__ == "__main__":
    vfs, script = parse_args()
    emulator = VFSEmulator(vfs, script)
    gui = EmulatorGUI(emulator)
    gui.root.mainloop()
