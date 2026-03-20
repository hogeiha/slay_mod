import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import os
import sys
import shutil

def resource_path(relative_path):
    """获取打包后资源的绝对路径（兼容PyInstaller单文件模式）"""
    try:
        # PyInstaller 创建的临时文件夹
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_git_path():
    """优先使用内置便携版Git，无则用系统Git"""
    # 便携版Git路径（打包时会把Git便携版放到git_portable目录）
    portable_git = resource_path("git_portable/bin/git.exe")
    if os.path.exists(portable_git):
        return portable_git
    # 系统Git
    if shutil.which("git"):
        return "git"
    return None

def check_git_available():
    """检查Git是否可用（内置/系统）"""
    git_path = get_git_path()
    if not git_path:
        return False
    try:
        # 【修改点1】检查Git时也禁止黑窗口
        subprocess.run(
            [git_path, "--version"],
            capture_output=True,
            text=True,
            check=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def sync_git_repo(url, target_dir, log_text):
    """执行Git强行同步（无账户，仅公共仓库）"""
    if not url.strip():
        messagebox.showerror("错误", "仓库URL不能为空！")
        return
    if not target_dir:
        messagebox.showerror("错误", "请选择同步目录！")
        return
    if not url.startswith("https://"):
        messagebox.warning("提示", "建议使用HTTPS格式的公共仓库地址（无需账户）！")

    git_path = get_git_path()
    log_text.delete(1.0, tk.END)
    log_text.insert(tk.END, f"开始同步仓库：{url}\n目标目录：{target_dir}\n使用Git：{git_path}\n\n")
    log_text.update()

    try:
        os.makedirs(target_dir, exist_ok=True)
        git_dir = os.path.join(target_dir, ".git")

        if os.path.exists(git_dir):
            # 已有仓库：强行同步（无账户）
            log_text.insert(tk.END, "检测到已有仓库，执行强行同步...\n")
            # 1. Fetch最新代码（匿名）
            run_command([git_path, "-C", target_dir, "fetch", "origin"], log_text)
            # 2. 强行重置到远程分支（兼容main/master）
            try:
                run_command([git_path, "-C", target_dir, "reset", "--hard", "origin/main"], log_text)
            except subprocess.CalledProcessError:
                log_text.insert(tk.END, "主分支非main，尝试master分支...\n")
                run_command([git_path, "-C", target_dir, "reset", "--hard", "origin/master"], log_text)
            # 3. 清理所有额外文件/文件夹
            run_command([git_path, "-C", target_dir, "clean", "-fdx"], log_text)
        else:
            # 克隆公共仓库（匿名）
            log_text.insert(tk.END, "未检测到仓库，执行匿名克隆...\n")
            run_command([git_path, "clone", "--depth=1", url, target_dir], log_text)

        log_text.insert(tk.END, "\n✅ 同步完成！目录内容与远程仓库完全一致（无额外文件）")
        messagebox.showinfo("成功", "仓库同步完成！")

    except Exception as e:
        log_text.insert(tk.END, f"\n❌ 同步失败：{str(e)}")
        messagebox.showerror("失败", f"同步出错：{str(e)}")

def run_command(cmd, log_text):
    """执行命令并实时输出日志"""
    log_text.insert(tk.END, f"执行命令：{' '.join(cmd)}\n")
    log_text.update()
    
    # 【修改点2】核心：添加creationflags禁止创建黑窗口（仅Windows生效）
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NO_WINDOW  # Windows专属，禁止控制台窗口
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="ignore",
        creationflags=creationflags  # 关键参数：消除黑窗口
    )
    
    while True:
        output = process.stdout.readline()
        if output == "" and process.poll() is not None:
            break
        if output:
            log_text.insert(tk.END, output)
            log_text.see(tk.END)
            log_text.update()
    return_code = process.poll()
    if return_code != 0:
        raise subprocess.CalledProcessError(return_code, cmd)

def select_directory(entry):
    """选择同步目录"""
    dir_path = filedialog.askdirectory(title="选择同步目录")
    if dir_path:
        entry.delete(0, tk.END)
        entry.insert(0, dir_path)

def create_gui():
    """创建轻量GUI"""
    root = tk.Tk()
    root.title("GitMOD强行同步工具")
    root.geometry("750x550")
    root.resizable(False, False)

    # 检查Git可用性 --- 此处是修改点：将critical改为showerror
    if not check_git_available():
        messagebox.showerror("严重错误", 
            "未检测到Git环境！\n"
            "1. 若您是客户：请安装Git并添加到系统环境变量；\n"
            "2. 若您是开发者：可打包便携版Git到工具中（见打包教程）。")
        root.destroy()
        sys.exit(1)

    # 1. 仓库URL输入区
    frame_url = ttk.Frame(root, padding="10")
    frame_url.pack(fill=tk.X)
    ttk.Label(frame_url, text="公共仓库HTTPS地址：").pack(side=tk.LEFT, padx=5)
    entry_url = ttk.Entry(frame_url, width=85)
    entry_url.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

    # 2. 同步目录选择区
    frame_dir = ttk.Frame(root, padding="10")
    frame_dir.pack(fill=tk.X)
    ttk.Label(frame_dir, text="同步目标目录：").pack(side=tk.LEFT, padx=5)
    entry_dir = ttk.Entry(frame_dir, width=70)
    entry_dir.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
    ttk.Button(frame_dir, text="选择", command=lambda: select_directory(entry_dir)).pack(side=tk.LEFT, padx=5)

    # 3. 同步按钮
    frame_btn = ttk.Frame(root, padding="10")
    frame_btn.pack()
    ttk.Button(
        frame_btn,
        text="开始强行同步（清空额外文件）",
        command=lambda: sync_git_repo(entry_url.get(), entry_dir.get(), log_text),
        style="Accent.TButton"
    ).pack(pady=5)

    # 4. 日志显示区
    frame_log = ttk.Frame(root, padding="10")
    frame_log.pack(fill=tk.BOTH, expand=True)
    ttk.Label(frame_log, text="执行日志：").pack(anchor=tk.W)
    log_text = tk.Text(frame_log, wrap=tk.WORD, height=22)
    scrollbar = ttk.Scrollbar(frame_log, orient=tk.VERTICAL, command=log_text.yview)
    log_text.configure(yscrollcommand=scrollbar.set)
    log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # 样式优化
    style = ttk.Style()
    style.configure("Accent.TButton", font=("Arial", 10, "bold"))
    root.mainloop()

if __name__ == "__main__":
    create_gui()