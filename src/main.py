import os
import sys
import shlex
import base64
import argparse
import getpass
import tkinter as tk
import xml.etree.ElementTree as ET

class VFSEmulator:
    def __init__(self, vfs_path=None, script_path=None):
        self.vfs_name = "VirtualFS"
        self.root_node = None
        self.current_path = []
        self.vfs_path = vfs_path
        self.script_path = script_path
        if vfs_path:
            self.load_vfs(vfs_path)

    def load_vfs(self, path):
        try:
            tree = ET.parse(path)
            self.root_node = tree.getroot()
            self.vfs_name = self.root_node.attrib.get("name", "VirtualFS")
            self.current_path = []
            return True
        except:
            return False

    def get_node_by_path(self, path_list):
        node = self.root_node
        for item in path_list:
            found = None
            for child in node:
                if child.attrib.get("name") == item and child.tag == "dir":
                    found = child
                    break
            if not found:
                return None
            node = found
        return node

    def cmd_ls(self):
        node = self.get_node_by_path(self.current_path)
        if node is None:
            return "Error: current path invalid\n"
        items = [child.attrib.get("name") for child in node]
        return "  ".join(items) + "\n" if items else "(empty)\n"

    def cmd_cd(self, target):
        if not target or target == "/":
            self.current_path = []
            return ""
        parts = target.split("/")
        new_path = list(self.current_path)
        if target.startswith("/"):
            new_path = []
        for part in parts:
            if not part or part == ".":
                continue
            if part == "..":
                if new_path:
                    new_path.pop()
            else:
                new_path.append(part)
        if self.get_node_by_path(new_path) is not None:
            self.current_path = new_path
            return ""
        return f"cd: no such file or directory: {target}\n"

    def cmd_tail(self, target):
        node = self.get_node_by_path(self.current_path)
        for child in node:
            if child.attrib.get("name") == target and child.tag == "file":
                try:
                    text = base64.b64decode(child.text or "").decode("utf-8")
                    lines = text.splitlines()
                    return "\n".join(lines[-10:]) + "\n"
                except:
                    return "Error: cannot decode file contents\n"
        return f"tail: {target}: No such file\n"

    def cmd_rm(self, target):
        node = self.get_node_by_path(self.current_path)
        for child in node:
            if child.attrib.get("name") == target:
                node.remove(child)
                return f"Removed {target}\n"
        return f"rm: {target}: No such file or directory\n"

    def cmd_cp(self, src, dest):
        node = self.get_node_by_path(self.current_path)
        src_node = None
        for child in node:
            if child.attrib.get("name") == src:
                src_node = child
                break
        if not src_node:
            return f"cp: {src}: No such file or directory\n"
        new_node = ET.Element(src_node.tag, attrib={"name": dest})
        new_node.text = src_node.text
        for sub in src_node:
            new_node.append(sub)
        node.append(new_node)
        return f"Copied {src} to {dest}\n"

class EmulatorGUI:
    def __init__(self, root, emulator):
        self.root = root
        self.emu = emulator
        self.update_title()
        self.root.geometry("700x450")
        self.output_text = tk.Text(root, bg="black", fg="white", font=("Courier", 12), state="disabled")
        self.output_text.pack(expand=True, fill="both")
        self.input_entry = tk.Entry(root, bg="black", fg="green", font=("Courier", 12), insertbackground="white")
        self.input_entry.pack(fill="x")
        self.input_entry.bind("<Return>", self.handle_command)
        self.print_to_console("VFS Emulator Initialized.\n")
        self.print_prompt()
        if self.emu.script_path:
            self.run_script(self.emu.script_path)

    def update_title(self):
        self.root.title(self.emu.vfs_name)

    def print_to_console(self, text):
        self.output_text.config(state="normal")
        self.output_text.insert(tk.END, text)
        self.output_text.config(state="disabled")
        self.output_text.see(tk.END)

    def print_prompt(self):
        path_str = "/" + "/".join(self.emu.current_path)
        self.print_to_console(f"{self.emu.vfs_name}:{path_str}$ ")

    def handle_command(self, event):
        command_str = self.input_entry.get()
        self.input_entry.delete(0, tk.END)
        if not command_str.strip():
            self.print_to_console("\n")
            self.print_prompt()
            return
        self.print_to_console(f"{command_str}\n")
        self.execute(command_str)

    def execute(self, command_str):
        expanded = os.path.expandvars(command_str)
        try:
            args = shlex.split(expanded)
        except:
            self.print_to_console("Error: Mismatched quotes\n")
            self.print_prompt()
            return False
        if not args:
            self.print_prompt()
            return True
        cmd = args[0]
        c_args = args[1:]
        if cmd == "exit":
            self.root.quit()
            return True
        elif cmd == "clear":
            self.output_text.config(state="normal")
            self.output_text.delete("1.0", tk.END)
            self.output_text.config(state="disabled")
            self.print_prompt()
            return True
        elif cmd == "who":
            self.print_to_console(f"{getpass.getuser()}\n")
        elif cmd == "ls":
            self.print_to_console(self.emu.cmd_ls())
        elif cmd == "cd":
            target = c_args[0] if c_args else "/"
            self.print_to_console(self.emu.cmd_cd(target))
        elif cmd == "tail":
            target = c_args[0] if c_args else ""
            self.print_to_console(self.emu.cmd_tail(target))
        elif cmd == "rm":
            target = c_args[0] if c_args else ""
            self.print_to_console(self.emu.cmd_rm(target))
        elif cmd == "cp":
            if len(c_args) < 2:
                self.print_to_console("cp: missing destination\n")
            else:
                self.print_to_console(self.emu.cmd_cp(c_args[0], c_args[1]))
        elif cmd == "vfs-load":
            target = c_args[0] if c_args else ""
            if self.emu.load_vfs(target):
                self.update_title()
                self.print_to_console(f"Loaded VFS from {target}\n")
            else:
                self.print_to_console(f"vfs-load: failed to load {target}\n")
        else:
            self.print_to_console(f"vfs: {cmd}: command not found\n")
        self.print_prompt()
        return True

    def run_script(self, path):
        if not os.path.exists(path):
            self.print_to_console(f"Script error: {path} not found\n")
            return
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                self.print_to_console(f"{line}\n")
                self.execute(line)

def parse_config(config_path):
    if not config_path or not os.path.exists(config_path):
        return None, None
    try:
        tree = ET.parse(config_path)
        root = tree.getroot()
        vfs = root.find("vfs_path").text if root.find("vfs_path") is not None else None
        script = root.find("script_path").text if root.find("script_path") is not None else None
        return vfs, script
    except:
        return None, None
        
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vfs")
    parser.add_argument("--script")
    parser.add_argument("--config")
    args = parser.parse_args()
    file_vfs, file_script = parse_config(args.config)
    final_vfs = args.vfs if args.vfs else file_vfs
    final_script = args.script if args.script else file_script
    print(f"[DEBUG] VFS: {final_vfs}, Script: {final_script}")
    emu = VFSEmulator(vfs_path=final_vfs, script_path=final_script)
    root = tk.Tk()
    app = EmulatorGUI(root, emu)
    root.mainloop()

if __name__ == "__main__":
    main()
