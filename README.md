<div align="center">

# 📁 Folder Suffix Merger

**A modern, elegant tool for merging folders with matching suffixes**

[![Python](https://img.shields.io/badge/Python-3.8+-3776ab?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey?style=for-the-badge)]()

<img src="screenshot.png" alt="Folder Suffix Merger Screenshot" width="700">

</div>

---

## ✨ What is this?

**Folder Suffix Merger** helps you clean up messy folder structures by automatically merging folders that share the same base name but have different suffixes.

### The Problem
You have folders like this:<br>
📁 Projects/<br>
📁 MyApp/<br>
📁 MyApp_backup/<br>
📁 MyApp_old/<br>
📁 Documents/<br>
📁 Documents_copy/<br>


### The Solution
This tool merges them automatically:<br>
📁 Projects/<br>
📁 MyApp/ ← Contains files from MyApp_backup & MyApp_old<br>
📁 Documents/ ← Contains files from Documents_copy<br>


---

## 🚀 Features

| Feature | Description |
|---------|-------------|
| **🔍 Smart Detection** | Automatically finds folders with matching suffixes |
| **🧪 Dry Run Mode** | Preview changes before applying them |
| **💾 Auto Backup** | Create ZIP backup before any modifications |
| **⚡ Conflict Handling** | Choose how to handle file name conflicts |
| **🎨 Modern UI** | Clean, macOS-inspired interface with smooth animations |
| **🌓 Theme Support** | Light, Dark, and System theme options |
| **📋 Detailed Logs** | Full operation logs with export capability |

---

## 📦 Installation

### Option 1: Run Directly (Recommended)

```bash
git clone https://github.com/defUtardi16/foldersuffix.git
cd folder-suffix-merger
python main.py

```
### Option 2 Manual Installation
```
pip install customtkinter
python main.py
```
### Requirements
Python 3.8 or higher<br>
CustomTkinter (auto-installed)<br>
Supported Platforms<br>
✅ Windows 10/11<br>
✅ macOS 10.14+<br>
✅ Linux (with Tk support)<br>


### Development Setup
```
git clone https://github.com/yourusername/folder-suffix-merger.git
cd folder-suffix-merger
pip install -e .

```
### How It Works
1. Scan directory tree (bottom-up)
2. Identify folders ending with target suffix
3. Build merge plan (source → destination pairs)
4. Execute merges:
   - If destination exists: merge contents recursively
   - If destination missing: simple rename
5. Clean up empty source folders

<div align="center">
Made with ❤️ by Melisa Laura Utardi

⭐ Star this repo if you find it useful!

</div>

