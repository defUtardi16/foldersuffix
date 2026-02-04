#!/usr/bin/env python3
"""
Folder Suffix Merger
====================
Author: Utardi16
License: MIT
Repository: https://github.com/defUtardi16/foldersuffix
"""

from __future__ import annotations

import os
import sys
import time
import shutil
import threading
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import (
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    Final,
    Protocol,
    runtime_checkable,
)

# =============================================================================
# Dependency Management
# =============================================================================


def _ensure_dependencies() -> None:
    """Ensure all required dependencies are installed."""
    required = ["customtkinter"]

    for package in required:
        try:
            __import__(package)
        except ImportError:
            print(f"[INFO] Installing missing dependency: {package}")
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", package],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except subprocess.CalledProcessError as e:
                print(f"[ERROR] Failed to install {package}: {e}")
                print(f"[HINT] Run manually: {sys.executable} -m pip install {package}")
                sys.exit(1)


_ensure_dependencies()

import customtkinter as ctk
from tkinter import filedialog, messagebox


# =============================================================================
# Type Aliases
# =============================================================================

LogCallback = Callable[[str], None]
ProgressCallback = Callable[[float], None]
StatusCallback = Callable[[str], None]
MergePlan = List[Tuple[str, str]]


# =============================================================================
# Constants
# =============================================================================


class Colors:
    """Application color palette - Monochrome with macOS traffic lights."""

    # Traffic light colors (macOS style)
    TRAFFIC_CLOSE: Final[str] = "#ff5f57"
    TRAFFIC_CLOSE_HOVER: Final[str] = "#ff7b73"
    TRAFFIC_MINIMIZE: Final[str] = "#febc2e"
    TRAFFIC_MINIMIZE_HOVER: Final[str] = "#ffc84a"
    TRAFFIC_MAXIMIZE: Final[str] = "#28c840"
    TRAFFIC_MAXIMIZE_HOVER: Final[str] = "#3ed656"
    TRAFFIC_INACTIVE: Final[str] = "#3a3a3c"

    # Monochrome UI palette (light, dark)
    WINDOW_BG: Final[tuple] = ("#f4f4f5", "#09090b")
    PANEL_BG: Final[tuple] = ("#ffffff", "#0a0a0c")
    SUBPANEL_BG: Final[tuple] = ("#fafafa", "#0f0f12")
    ACCENT: Final[tuple] = ("#18181b", "#fafafa")
    ACCENT_HOVER: Final[tuple] = ("#27272a", "#e4e4e7")
    ACCENT_SOFT: Final[tuple] = ("#e4e4e7", "#27272a")
    BORDER: Final[tuple] = ("#e4e4e7", "#27272a")
    TEXT_PRIMARY: Final[tuple] = ("#09090b", "#fafafa")
    TEXT_SECONDARY: Final[tuple] = ("#71717a", "#a1a1aa")
    TEXT_MUTED: Final[tuple] = ("#a1a1aa", "#71717a")


class Dimensions:
    """UI dimensions and sizing constants."""

    WINDOW_WIDTH: Final[int] = 880
    WINDOW_HEIGHT: Final[int] = 600
    WINDOW_MIN_WIDTH: Final[int] = 800
    WINDOW_MIN_HEIGHT: Final[int] = 520

    CORNER_RADIUS_LG: Final[int] = 24
    CORNER_RADIUS_MD: Final[int] = 16
    CORNER_RADIUS_SM: Final[int] = 10
    CORNER_RADIUS_XS: Final[int] = 8

    PADDING_LG: Final[int] = 24
    PADDING_MD: Final[int] = 16
    PADDING_SM: Final[int] = 12
    PADDING_XS: Final[int] = 8

    DOT_SIZE: Final[int] = 12
    DOT_GAP: Final[int] = 8


class Animation:
    """Animation timing constants."""

    FADE_DURATION_MS: Final[int] = 400
    FADE_STEPS: Final[int] = 25
    FADE_INTERVAL_MS: Final[int] = 16  # ~60fps

    BUTTON_PULSE_MS: Final[int] = 400
    CELEBRATION_MS: Final[int] = 100
    CELEBRATION_STEPS: Final[int] = 8


class ConflictMode(Enum):
    """File conflict resolution strategies."""

    RENAME = "rename"
    OVERWRITE = "overwrite"
    SKIP = "skip"


class ThemeMode(Enum):
    """Application theme modes."""

    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"


# =============================================================================
# Protocols
# =============================================================================


@runtime_checkable
class ProgressReporter(Protocol):
    """Interface for progress reporting."""

    def set_progress(self, value: float) -> None: ...
    def set_status(self, text: str) -> None: ...
    def log(self, message: str) -> None: ...


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class OperationStats:
    """Statistics tracking for merge operations."""

    folders_planned: int = 0
    folders_merged: int = 0
    folders_renamed: int = 0
    files_moved: int = 0
    items_skipped: int = 0
    name_conflicts: int = 0
    dirs_deleted: int = 0
    backups_created: int = 0

    def to_summary(self) -> str:
        """Generate human-readable summary string."""
        return "\n".join([
            f"Folders planned   : {self.folders_planned}",
            f"Folders merged    : {self.folders_merged}",
            f"Folders renamed   : {self.folders_renamed}",
            f"Files moved       : {self.files_moved}",
            f"Name conflicts    : {self.name_conflicts}",
            f"Items skipped     : {self.items_skipped}",
            f"Dirs deleted      : {self.dirs_deleted}",
            f"Backups created   : {self.backups_created}",
        ])


@dataclass
class MergeConfig:
    """Configuration for merge operations."""

    root_path: str
    suffix: str
    ignore_case: bool = False
    dry_run: bool = True
    create_backup: bool = False
    conflict_mode: ConflictMode = ConflictMode.RENAME

    def __post_init__(self) -> None:
        """Validate configuration."""
        if not self.root_path:
            raise ValueError("Root path cannot be empty")
        if not self.suffix:
            raise ValueError("Suffix cannot be empty")


@dataclass
class FontConfig:
    """
    Font configuration with rounded font families.
    
    Uses platform-specific rounded fonts for a softer, modern look.
    Falls back to system defaults if preferred fonts aren't available.
    """

    family: str = "Nunito"
    mono_family: str = "Consolas"

    def __post_init__(self) -> None:
        """Detect and set platform-appropriate fonts."""
        if sys.platform == "darwin":
            # macOS - SF Pro Rounded is beautiful
            self.family = "SF Pro Rounded"
            self.mono_family = "SF Mono"
        elif sys.platform == "win32":
            # Windows - Poppins or Nunito (need to be installed)
            # Fallback to Segoe UI Variable which has rounded variants
            self.family = "Poppins"
            self.mono_family = "Cascadia Code"
        else:
            # Linux - Ubuntu Rounded or Nunito
            self.family = "Nunito"
            self.mono_family = "Ubuntu Mono"

    def title(self) -> ctk.CTkFont:
        """Large title font."""
        return ctk.CTkFont(family=self.family, size=24, weight="bold")

    def heading(self) -> ctk.CTkFont:
        """Section heading font."""
        return ctk.CTkFont(family=self.family, size=16, weight="bold")

    def subtitle(self) -> ctk.CTkFont:
        """Subtitle/description font."""
        return ctk.CTkFont(family=self.family, size=13)

    def body(self) -> ctk.CTkFont:
        """Body text font."""
        return ctk.CTkFont(family=self.family, size=12)

    def small(self) -> ctk.CTkFont:
        """Small text font."""
        return ctk.CTkFont(family=self.family, size=11)

    def button(self) -> ctk.CTkFont:
        """Button text font."""
        return ctk.CTkFont(family=self.family, size=12, weight="bold")

    def mono(self) -> ctk.CTkFont:
        """Monospace font for logs."""
        return ctk.CTkFont(family=self.mono_family, size=11)


# =============================================================================
# Core Operations
# =============================================================================


class OperationContext:
    """
    Context for file system operations.
    
    Manages logging, progress reporting, statistics tracking,
    and provides safe file operation methods with dry-run support.
    
    Attributes:
        stats: Operation statistics tracker
    """

    def __init__(
        self,
        config: MergeConfig,
        log_fn: LogCallback,
        progress_fn: ProgressCallback,
        status_fn: StatusCallback,
    ) -> None:
        self._config = config
        self._log_fn = log_fn
        self._progress_fn = progress_fn
        self._status_fn = status_fn
        self.stats = OperationStats()

    @property
    def dry_run(self) -> bool:
        """Whether operations should be simulated only."""
        return self._config.dry_run

    @property
    def conflict_mode(self) -> ConflictMode:
        """Current conflict resolution strategy."""
        return self._config.conflict_mode

    def log(self, message: str) -> None:
        """Log a message to the UI."""
        self._log_fn(message)

    def progress(self, value: float) -> None:
        """Update progress bar (0.0 to 1.0)."""
        self._progress_fn(max(0.0, min(1.0, value)))

    def status(self, text: str) -> None:
        """Update status label text."""
        self._status_fn(text)

    def generate_unique_path(self, directory: str, name: str) -> str:
        """
        Generate a unique file path by appending a counter.
        
        Args:
            directory: Target directory
            name: Original file/folder name
            
        Returns:
            Unique path that doesn't exist yet
        """
        base, ext = os.path.splitext(name)
        candidate = os.path.join(directory, name)
        counter = 1

        while os.path.exists(candidate):
            candidate = os.path.join(directory, f"{base} ({counter}){ext}")
            counter += 1

        return candidate

    def resolve_conflict(self, dst_dir: str, dst_path: str) -> Optional[str]:
        """
        Resolve a naming conflict based on current conflict mode.
        
        Args:
            dst_dir: Destination directory
            dst_path: Proposed destination path
            
        Returns:
            Resolved path to use, or None if should skip
        """
        if not os.path.exists(dst_path):
            return dst_path

        name = os.path.basename(dst_path)

        if self.conflict_mode == ConflictMode.SKIP:
            self.log(f"   ⊘ Skipped (exists): {name}")
            self.stats.items_skipped += 1
            self.stats.name_conflicts += 1
            return None

        if self.conflict_mode == ConflictMode.OVERWRITE:
            self.log(f"   ⟳ Overwriting: {name}")
            self.stats.name_conflicts += 1
            if not self.dry_run:
                try:
                    os.remove(dst_path)
                except OSError:
                    pass
            return dst_path

        if self.conflict_mode == ConflictMode.RENAME:
            new_path = self.generate_unique_path(dst_dir, name)
            new_name = os.path.basename(new_path)
            self.log(f"   ⟳ Renaming: {name} → {new_name}")
            self.stats.name_conflicts += 1
            return new_path

        return None

    def makedirs(self, path: str) -> None:
        """Create directory and parents if needed."""
        if os.path.exists(path):
            return

        if self.dry_run:
            self.log(f"   [DRY] Would create: {os.path.basename(path)}")
        else:
            os.makedirs(path, exist_ok=True)

    def move(self, src: str, dst: str, *, is_dir: bool = False) -> None:
        """
        Move a file or directory.
        
        Args:
            src: Source path
            dst: Destination path
            is_dir: Whether source is a directory
        """
        name = os.path.basename(src)

        if self.dry_run:
            kind = "folder" if is_dir else "file"
            self.log(f"   [DRY] Would move {kind}: {name}")
        else:
            parent = os.path.dirname(dst)
            if parent and not os.path.exists(parent):
                os.makedirs(parent, exist_ok=True)
            shutil.move(src, dst)

        if not is_dir:
            self.stats.files_moved += 1

    def rename_dir(self, src: str, dst: str) -> None:
        """Rename a directory."""
        src_name = os.path.basename(src)
        dst_name = os.path.basename(dst)

        if self.dry_run:
            self.log(f"   [DRY] Would rename: {src_name} → {dst_name}")
        else:
            parent = os.path.dirname(dst)
            if parent and not os.path.exists(parent):
                os.makedirs(parent, exist_ok=True)
            os.rename(src, dst)

        self.stats.folders_renamed += 1

    def rmdir(self, path: str) -> bool:
        """
        Remove an empty directory.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.dry_run:
                self.log(f"   [DRY] Would remove: {os.path.basename(path)}")
            else:
                os.rmdir(path)
            self.stats.dirs_deleted += 1
            return True
        except OSError:
            return False


class MergePlanner:
    """Builds merge plans by scanning directory trees."""

    @staticmethod
    def build_plan(
        root: str,
        suffix: str,
        ignore_case: bool = False,
    ) -> MergePlan:
        """
        Scan directory tree and build a merge plan.
        
        Walks the directory tree bottom-up to find folders ending
        with the specified suffix, pairing them with their target
        (suffix-removed) paths.
        
        Args:
            root: Root directory to scan
            suffix: Suffix to match and remove
            ignore_case: Whether to ignore case in matching
            
        Returns:
            List of (source, destination) path tuples
        """
        if not suffix:
            return []

        plan: MergePlan = []
        suffix_len = len(suffix)
        match_suffix = suffix.lower() if ignore_case else suffix

        for dirpath, dirnames, _ in os.walk(root, topdown=False):
            for name in dirnames:
                check_name = name.lower() if ignore_case else name

                if check_name.endswith(match_suffix):
                    base = name[:-suffix_len]
                    if base:
                        src = os.path.join(dirpath, name)
                        dst = os.path.join(dirpath, base)
                        plan.append((src, dst))

        return plan


class MergeExecutor:
    """Executes merge operations from a plan."""

    def __init__(self, ctx: OperationContext) -> None:
        self._ctx = ctx

    def execute(self, plan: MergePlan) -> None:
        """
        Execute the merge plan.
        
        Args:
            plan: List of (source, destination) tuples
        """
        total = len(plan) or 1

        for index, (src, dst) in enumerate(plan, start=1):
            if not os.path.exists(src):
                self._ctx.log(f"⊘ Not found: {os.path.basename(src)}")
                self._ctx.progress(index / total)
                continue

            self._ctx.status(f"Processing {index} of {len(plan)}...")
            src_name = os.path.basename(src)
            dst_name = os.path.basename(dst)

            if os.path.exists(dst):
                self._ctx.log(f"◈ Merge: {src_name} → {dst_name}")
                self._ctx.stats.folders_merged += 1
                self._merge_trees(src, dst)
            else:
                self._ctx.log(f"◇ Rename: {src_name} → {dst_name}")
                self._ctx.rename_dir(src, dst)

            self._ctx.progress(index / total)

    def _merge_trees(self, src: str, dst: str) -> None:
        """Recursively merge source into destination."""
        if not os.path.exists(dst):
            self._ctx.makedirs(dst)

        for name in os.listdir(src):
            src_item = os.path.join(src, name)
            dst_item = os.path.join(dst, name)

            if os.path.isdir(src_item):
                self._handle_directory(src_item, dst_item, name, dst)
            else:
                self._handle_file(src_item, dst_item, name, dst)

        # Clean up empty source
        try:
            if not os.listdir(src):
                self._ctx.rmdir(src)
        except (OSError, FileNotFoundError):
            pass

    def _handle_directory(
        self,
        src_item: str,
        dst_item: str,
        name: str,
        dst_parent: str,
    ) -> None:
        """Handle directory during merge."""
        if os.path.isdir(dst_item):
            self._ctx.stats.folders_merged += 1
            self._merge_trees(src_item, dst_item)
        elif os.path.exists(dst_item):
            self._handle_type_conflict(src_item, name, dst_parent, is_dir=True)
        else:
            self._ctx.stats.folders_merged += 1
            self._ctx.move(src_item, dst_item, is_dir=True)

    def _handle_file(
        self,
        src_item: str,
        dst_item: str,
        name: str,
        dst_parent: str,
    ) -> None:
        """Handle file during merge."""
        if os.path.isdir(dst_item):
            self._handle_type_conflict(src_item, name, dst_parent, is_dir=False)
        elif os.path.exists(dst_item):
            resolved = self._ctx.resolve_conflict(dst_parent, dst_item)
            if resolved:
                self._ctx.move(src_item, resolved)
        else:
            self._ctx.move(src_item, dst_item)

    def _handle_type_conflict(
        self,
        src_item: str,
        name: str,
        dst_parent: str,
        is_dir: bool,
    ) -> None:
        """Handle conflict between file and directory."""
        src_type = "folder" if is_dir else "file"
        dst_type = "file" if is_dir else "folder"

        if self._ctx.conflict_mode == ConflictMode.SKIP:
            self._ctx.log(f"   ⊘ Skip ({src_type} vs {dst_type}): {name}")
            self._ctx.stats.items_skipped += 1
            self._ctx.stats.name_conflicts += 1
        else:
            new_path = self._ctx.generate_unique_path(dst_parent, name)
            new_name = os.path.basename(new_path)
            self._ctx.log(f"   ⟳ Rename conflict: {name} → {new_name}")
            self._ctx.stats.name_conflicts += 1
            self._ctx.move(src_item, new_path, is_dir=is_dir)


class BackupManager:
    """Handles backup archive creation."""

    @staticmethod
    def create_archive(root: str, ctx: OperationContext) -> Optional[str]:
        """
        Create a ZIP backup of the target directory.
        
        Args:
            root: Directory to backup
            ctx: Operation context
            
        Returns:
            Path to created archive, or None on failure
        """
        if not os.path.isdir(root):
            return None

        root_path = Path(root).resolve()
        parent = root_path.parent
        name = root_path.name or "backup"

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        archive_name = f"{name}_backup_{timestamp}"
        archive_base = parent / archive_name

        ctx.log(f"◎ Creating backup: {archive_name}.zip")
        ctx.status("Creating backup archive...")

        if ctx.dry_run:
            ctx.log("   [DRY] Backup would be created")
            return str(archive_base) + ".zip"

        try:
            archive = shutil.make_archive(str(archive_base), "zip", root_dir=str(root_path))
            ctx.log(f"   ✓ Backup saved: {os.path.basename(archive)}")
            ctx.stats.backups_created += 1
            return archive
        except Exception as e:
            ctx.log(f"   ✗ Backup failed: {e}")
            return None


# =============================================================================
# UI Components
# =============================================================================


class TrafficLightButton(ctk.CTkLabel):
    """
    macOS-style traffic light button.
    
    Displays colored dot that responds to hover with
    symbol overlay and size animation.
    """

    def __init__(
        self,
        master: ctk.CTkFrame,
        color: str,
        hover_color: str,
        symbol: str,
        command: Callable[[], None],
        fonts: FontConfig,
        **kwargs,
    ) -> None:
        super().__init__(
            master,
            text="",
            width=Dimensions.DOT_SIZE,
            height=Dimensions.DOT_SIZE,
            corner_radius=Dimensions.DOT_SIZE // 2,
            fg_color=color,
            **kwargs,
        )

        self._base_color = color
        self._hover_color = hover_color
        self._symbol = symbol
        self._command = command
        self._fonts = fonts
        self._active = True

        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def set_active(self, active: bool) -> None:
        """Toggle active/inactive visual state."""
        self._active = active
        self.configure(fg_color=self._base_color if active else Colors.TRAFFIC_INACTIVE)

    def _on_click(self, event=None) -> str:
        self._command()
        return "break"

    def _on_enter(self, event=None) -> None:
        self.configure(
            fg_color=self._hover_color,
            text=self._symbol,
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color="#4a4a4a",
            width=Dimensions.DOT_SIZE + 2,
            height=Dimensions.DOT_SIZE + 2,
        )

    def _on_leave(self, event=None) -> None:
        color = self._base_color if self._active else Colors.TRAFFIC_INACTIVE
        self.configure(
            fg_color=color,
            text="",
            width=Dimensions.DOT_SIZE,
            height=Dimensions.DOT_SIZE,
        )


class TrafficLightGroup(ctk.CTkFrame):
    """Group of three macOS-style traffic light buttons."""

    def __init__(
        self,
        master: ctk.CTkFrame,
        fonts: FontConfig,
        on_close: Callable[[], None],
        on_minimize: Callable[[], None],
        on_maximize: Callable[[], None],
    ) -> None:
        super().__init__(master, fg_color="transparent")

        self.close_btn = TrafficLightButton(
            self, Colors.TRAFFIC_CLOSE, Colors.TRAFFIC_CLOSE_HOVER,
            "×", on_close, fonts,
        )
        self.close_btn.pack(side="left", padx=(0, Dimensions.DOT_GAP))

        self.minimize_btn = TrafficLightButton(
            self, Colors.TRAFFIC_MINIMIZE, Colors.TRAFFIC_MINIMIZE_HOVER,
            "−", on_minimize, fonts,
        )
        self.minimize_btn.pack(side="left", padx=(0, Dimensions.DOT_GAP))

        self.maximize_btn = TrafficLightButton(
            self, Colors.TRAFFIC_MAXIMIZE, Colors.TRAFFIC_MAXIMIZE_HOVER,
            "+", on_maximize, fonts,
        )
        self.maximize_btn.pack(side="left")

    def set_active(self, active: bool) -> None:
        """Set active state for all buttons."""
        self.close_btn.set_active(active)
        self.minimize_btn.set_active(active)
        self.maximize_btn.set_active(active)


# =============================================================================
# Main Application
# =============================================================================


class FolderMergerApp(ctk.CTk):
    """
    Main application window.
    
    Provides a modern, macOS-inspired interface for merging
    folders with matching suffixes.
    """

    def __init__(self) -> None:
        super().__init__()

        # Configuration
        self._fonts = FontConfig()
        self._use_custom_titlebar = sys.platform.startswith("win")
        self._transparent_color = "#010101"

        # State
        self._is_maximized = False
        self._restore_geometry: Optional[str] = None
        self._drag_offset = (0, 0)
        self._window_active = True
        self._animation_job: Optional[str] = None
        self._button_animating = False
        self._worker_thread: Optional[threading.Thread] = None

        # UI references
        self._main_frame: Optional[ctk.CTkFrame] = None
        self._traffic_lights: Optional[TrafficLightGroup] = None
        self._progress_bar: Optional[ctk.CTkProgressBar] = None
        self._status_label: Optional[ctk.CTkLabel] = None
        self._run_button: Optional[ctk.CTkButton] = None
        self._log_textbox: Optional[ctk.CTkTextbox] = None

        # Variables
        self._path_var = ctk.StringVar()
        self._suffix_var = ctk.StringVar(value="")
        self._dry_run_var = ctk.BooleanVar(value=True)
        self._backup_var = ctk.BooleanVar(value=False)
        self._ignore_case_var = ctk.BooleanVar(value=False)
        self._conflict_var = ctk.StringVar(value=ConflictMode.RENAME.value)
        self._theme_var = ctk.StringVar(value="Light")

        self._setup_window()
        self._build_ui()
        self._bind_events()
        self._fade_in()

    # -------------------------------------------------------------------------
    # Setup
    # -------------------------------------------------------------------------

    def _setup_window(self) -> None:
        """Configure main window properties."""
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("dark-blue")

        self.title("Folder Suffix Merger")
        self.geometry(f"{Dimensions.WINDOW_WIDTH}x{Dimensions.WINDOW_HEIGHT}")
        self.minsize(Dimensions.WINDOW_MIN_WIDTH, Dimensions.WINDOW_MIN_HEIGHT)

        if self._use_custom_titlebar:
            try:
                self.overrideredirect(True)
                self.configure(bg=self._transparent_color, fg_color=self._transparent_color)
                self.wm_attributes("-transparentcolor", self._transparent_color)
            except Exception:
                self._use_custom_titlebar = False

        if not self._use_custom_titlebar:
            self.configure(fg_color=Colors.WINDOW_BG)

        try:
            self.attributes("-alpha", 0.0)
        except Exception:
            pass

        # Center window
        self.update_idletasks()
        x = (self.winfo_screenwidth() - Dimensions.WINDOW_WIDTH) // 2
        y = (self.winfo_screenheight() - Dimensions.WINDOW_HEIGHT) // 3
        self.geometry(f"+{x}+{y}")

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # -------------------------------------------------------------------------
    # UI Building
    # -------------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Build the complete user interface."""
        self._main_frame = ctk.CTkFrame(
            self,
            corner_radius=Dimensions.CORNER_RADIUS_LG,
            fg_color=Colors.PANEL_BG,
        )
        self._main_frame.pack(
            fill="both", expand=True,
            padx=Dimensions.PADDING_LG,
            pady=Dimensions.PADDING_LG,
        )

        self._build_header()
        self._build_divider()
        self._build_body()

    def _build_header(self) -> None:
        """Build header with traffic lights and title."""
        header = ctk.CTkFrame(self._main_frame, fg_color="transparent")
        header.pack(fill="x", padx=Dimensions.PADDING_MD, pady=(8, 8))

        self._traffic_lights = TrafficLightGroup(
            header, self._fonts,
            on_close=self._on_close,
            on_minimize=self._on_minimize,
            on_maximize=self._on_maximize,
        )
        self._traffic_lights.pack(side="left", padx=(0, Dimensions.PADDING_SM))

        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left", expand=True)

        title = ctk.CTkLabel(
            title_box,
            text="Folder Suffix Merger",
            font=self._fonts.title(),
            text_color=Colors.TEXT_PRIMARY,
        )
        title.pack(anchor="center")

        subtitle = ctk.CTkLabel(
            header,
            text="Merge folders with matching suffixes safely",
            font=self._fonts.subtitle(),
            text_color=Colors.TEXT_MUTED,
        )
        subtitle.pack(anchor="w", pady=(4, 0))

        # Drag bindings
        if self._use_custom_titlebar:
            for w in (header, title_box, title, subtitle):
                w.bind("<Button-1>", self._start_drag)
                w.bind("<B1-Motion>", self._on_drag)
                w.bind("<Double-Button-1>", lambda e: self._on_maximize())

    def _build_divider(self) -> None:
        """Build horizontal divider line."""
        ctk.CTkFrame(
            self._main_frame,
            fg_color=Colors.BORDER,
            height=1,
        ).pack(fill="x", padx=Dimensions.PADDING_LG, pady=(0, 8))

    def _build_body(self) -> None:
        """Build main content area."""
        body = ctk.CTkFrame(
            self._main_frame,
            corner_radius=Dimensions.CORNER_RADIUS_MD,
            fg_color=Colors.SUBPANEL_BG,
        )
        body.pack(
            fill="both", expand=True,
            padx=Dimensions.PADDING_MD,
            pady=(4, Dimensions.PADDING_MD),
        )

        self._build_path_section(body)
        self._build_suffix_section(body)
        self._build_options_section(body)
        self._build_conflict_section(body)
        self._build_controls_section(body)
        self._build_progress_section(body)
        self._build_log_section(body)

    def _build_path_section(self, parent: ctk.CTkFrame) -> None:
        """Build folder path input."""
        container = ctk.CTkFrame(parent, fg_color="transparent")
        container.pack(fill="x", padx=Dimensions.PADDING_MD, pady=(Dimensions.PADDING_MD, 8))

        ctk.CTkLabel(
            container, text="Root Folder",
            font=self._fonts.body(),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w")

        row = ctk.CTkFrame(container, fg_color="transparent")
        row.pack(fill="x", pady=(4, 0))

        ctk.CTkEntry(
            row,
            textvariable=self._path_var,
            font=self._fonts.body(),
            corner_radius=Dimensions.CORNER_RADIUS_SM,
            placeholder_text="Select folder to organize...",
        ).pack(side="left", fill="x", expand=True)

        ctk.CTkButton(
            row, text="Browse",
            font=self._fonts.button(),
            width=100,
            corner_radius=Dimensions.CORNER_RADIUS_SM,
            fg_color=Colors.ACCENT,
            hover_color=Colors.ACCENT_HOVER,
            command=self._on_browse,
        ).pack(side="left", padx=(10, 0))

    def _build_suffix_section(self, parent: ctk.CTkFrame) -> None:
        """Build suffix input."""
        container = ctk.CTkFrame(parent, fg_color="transparent")
        container.pack(fill="x", padx=Dimensions.PADDING_MD, pady=(0, 8))

        ctk.CTkLabel(
            container, text="Suffix to Remove",
            font=self._fonts.body(),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w")

        ctk.CTkEntry(
            container,
            textvariable=self._suffix_var,
            font=self._fonts.body(),
            corner_radius=Dimensions.CORNER_RADIUS_SM,
            placeholder_text="e.g., _backup, _old, _copy",
        ).pack(fill="x", pady=(4, 0))

    def _build_options_section(self, parent: ctk.CTkFrame) -> None:
        """Build option checkboxes."""
        container = ctk.CTkFrame(parent, fg_color="transparent")
        container.pack(fill="x", padx=Dimensions.PADDING_MD, pady=(0, 8))

        ctk.CTkCheckBox(
            container, text="Dry run (simulate only)",
            variable=self._dry_run_var,
            font=self._fonts.small(),
            corner_radius=Dimensions.CORNER_RADIUS_XS,
        ).pack(side="left")

        ctk.CTkCheckBox(
            container, text="Create backup (.zip)",
            variable=self._backup_var,
            font=self._fonts.small(),
            corner_radius=Dimensions.CORNER_RADIUS_XS,
        ).pack(side="left", padx=(16, 0))

        ctk.CTkCheckBox(
            container, text="Ignore case",
            variable=self._ignore_case_var,
            font=self._fonts.small(),
            corner_radius=Dimensions.CORNER_RADIUS_XS,
        ).pack(side="right")

    def _build_conflict_section(self, parent: ctk.CTkFrame) -> None:
        """Build conflict mode selector."""
        container = ctk.CTkFrame(parent, fg_color="transparent")
        container.pack(fill="x", padx=Dimensions.PADDING_MD, pady=(0, 12))

        ctk.CTkLabel(
            container, text="On file conflict",
            font=self._fonts.body(),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w")

        ctk.CTkSegmentedButton(
            container,
            values=["rename", "overwrite", "skip"],
            variable=self._conflict_var,
            font=self._fonts.small(),
            corner_radius=Dimensions.CORNER_RADIUS_SM,
            fg_color=Colors.ACCENT_SOFT,
            selected_color=Colors.ACCENT,
            selected_hover_color=Colors.ACCENT_HOVER,
        ).pack(anchor="w", pady=(4, 0))

    def _build_controls_section(self, parent: ctk.CTkFrame) -> None:
        """Build control buttons and theme selector."""
        container = ctk.CTkFrame(parent, fg_color="transparent")
        container.pack(fill="x", padx=Dimensions.PADDING_MD, pady=(0, 10))

        ctk.CTkLabel(
            container, text="Theme",
            font=self._fonts.body(),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(side="left")

        ctk.CTkSegmentedButton(
            container,
            values=["System", "Light", "Dark"],
            variable=self._theme_var,
            font=self._fonts.small(),
            corner_radius=Dimensions.CORNER_RADIUS_SM,
            command=self._on_theme_change,
        ).pack(side="left", padx=(8, 0))

        ctk.CTkLabel(
            container,
            text="Ctrl+R Run • Ctrl+L Save",
            font=self._fonts.small(),
            text_color=Colors.TEXT_MUTED,
        ).pack(side="left", padx=(16, 0))

        # Spacer
        ctk.CTkLabel(container, text="").pack(side="left", expand=True)

        ctk.CTkButton(
            container, text="Save Log",
            font=self._fonts.button(),
            width=100,
            corner_radius=Dimensions.CORNER_RADIUS_SM,
            fg_color=Colors.ACCENT_SOFT,
            hover_color=Colors.BORDER,
            text_color=Colors.TEXT_SECONDARY,
            command=self._on_save_log,
        ).pack(side="right", padx=(0, 8))

        self._run_button = ctk.CTkButton(
            container, text="Start Merge",
            font=self._fonts.button(),
            width=140,
            corner_radius=Dimensions.CORNER_RADIUS_SM,
            fg_color=Colors.ACCENT,
            hover_color=Colors.ACCENT_HOVER,
            command=self._on_run,
        )
        self._run_button.pack(side="right")

    def _build_progress_section(self, parent: ctk.CTkFrame) -> None:
        """Build progress bar and status."""
        container = ctk.CTkFrame(parent, fg_color="transparent")
        container.pack(fill="x", padx=Dimensions.PADDING_MD, pady=(0, 8))

        self._progress_bar = ctk.CTkProgressBar(
            container,
            corner_radius=Dimensions.CORNER_RADIUS_XS,
            progress_color=Colors.ACCENT,
        )
        self._progress_bar.pack(fill="x")
        self._progress_bar.set(0)

        self._status_label = ctk.CTkLabel(
            container, text="Ready",
            font=self._fonts.small(),
            text_color=Colors.TEXT_MUTED,
        )
        self._status_label.pack(anchor="w", pady=(4, 0))

    def _build_log_section(self, parent: ctk.CTkFrame) -> None:
        """Build log output area."""
        container = ctk.CTkFrame(
            parent,
            fg_color=Colors.PANEL_BG,
            corner_radius=Dimensions.CORNER_RADIUS_MD,
        )
        container.pack(
            fill="both", expand=True,
            padx=Dimensions.PADDING_MD,
            pady=(0, Dimensions.PADDING_MD),
        )

        ctk.CTkLabel(
            container, text="Log",
            font=self._fonts.body(),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w", padx=10, pady=(8, 0))

        self._log_textbox = ctk.CTkTextbox(
            container,
            font=self._fonts.mono(),
            corner_radius=Dimensions.CORNER_RADIUS_SM,
            state="disabled",
        )
        self._log_textbox.pack(fill="both", expand=True, padx=10, pady=(4, 10))

    # -------------------------------------------------------------------------
    # Event Binding
    # -------------------------------------------------------------------------

    def _bind_events(self) -> None:
        """Bind keyboard shortcuts and focus events."""
        self.bind("<FocusIn>", self._on_focus_in)
        self.bind("<FocusOut>", self._on_focus_out)

        mod = "Command" if sys.platform == "darwin" else "Control"
        self.bind_all(f"<{mod}-r>", lambda e: self._on_run())
        self.bind_all(f"<{mod}-R>", lambda e: self._on_run())
        self.bind_all(f"<{mod}-l>", lambda e: self._on_save_log())
        self.bind_all(f"<{mod}-L>", lambda e: self._on_save_log())

    # -------------------------------------------------------------------------
    # Animation
    # -------------------------------------------------------------------------

    def _fade_in(self) -> None:
        """Perform smooth fade-in animation."""
        steps = Animation.FADE_STEPS
        step = 0

        def animate():
            nonlocal step
            if step > steps:
                try:
                    self.attributes("-alpha", 1.0)
                except Exception:
                    pass
                return

            progress = step / steps
            alpha = 1 - pow(1 - progress, 3)  # ease-out cubic

            try:
                self.attributes("-alpha", alpha)
            except Exception:
                pass

            step += 1
            self.after(Animation.FADE_INTERVAL_MS, animate)

        animate()

    def _fade_out_and_close(self) -> None:
        """Fade out then destroy window."""
        steps = 15
        step = 0

        def animate():
            nonlocal step
            if step > steps:
                self.destroy()
                return

            progress = step / steps
            alpha = 1.0 - (progress ** 2)  # ease-in

            try:
                self.attributes("-alpha", max(0, alpha))
            except Exception:
                pass

            step += 1
            self.after(Animation.FADE_INTERVAL_MS, animate)

        animate()

    def _set_running(self, running: bool) -> None:
        """Toggle run button state."""
        if running:
            self._run_button.configure(state="disabled")
            self._button_animating = True
            self._animate_button()
        else:
            self._button_animating = False
            if self._animation_job:
                try:
                    self.after_cancel(self._animation_job)
                except Exception:
                    pass
            self._run_button.configure(
                text="Start Merge",
                state="normal",
                fg_color=Colors.ACCENT,
            )

    def _animate_button(self) -> None:
        """Animate button text while processing."""
        dots = ["", ".", "..", "..."]
        idx = 0

        def step():
            nonlocal idx
            if not self._button_animating:
                return
            self._run_button.configure(text=f"Processing{dots[idx % 4]}")
            idx += 1
            self._animation_job = self.after(Animation.BUTTON_PULSE_MS, step)

        step()

    def _celebrate(self) -> None:
        """Flash progress bar on completion."""
        steps = Animation.CELEBRATION_STEPS
        i = 0

        def pulse():
            nonlocal i
            if i >= steps:
                self._progress_bar.configure(progress_color=Colors.ACCENT)
                return
            color = Colors.ACCENT if i % 2 == 0 else Colors.ACCENT_SOFT
            self._progress_bar.configure(progress_color=color)
            i += 1
            self.after(Animation.CELEBRATION_MS, pulse)

        pulse()

    # -------------------------------------------------------------------------
    # Window Management
    # -------------------------------------------------------------------------

    def _start_drag(self, event) -> None:
        """Start window drag."""
        if self._is_maximized:
            return
        self._drag_offset = (
            event.x_root - self.winfo_x(),
            event.y_root - self.winfo_y(),
        )

    def _on_drag(self, event) -> None:
        """Handle window drag motion."""
        if self._is_maximized:
            return
        x = event.x_root - self._drag_offset[0]
        y = event.y_root - self._drag_offset[1]
        self.geometry(f"+{x}+{y}")

    def _on_focus_in(self, event=None) -> None:
        """Handle focus gain."""
        self._window_active = True
        if self._traffic_lights:
            self._traffic_lights.set_active(True)

    def _on_focus_out(self, event=None) -> None:
        """Handle focus loss."""
        self._window_active = False
        if self._traffic_lights:
            self._traffic_lights.set_active(False)

    # -------------------------------------------------------------------------
    # Event Handlers
    # -------------------------------------------------------------------------

    def _on_close(self) -> None:
        """Handle close button."""
        self._fade_out_and_close()

    def _on_minimize(self) -> None:
        """Handle minimize button."""
        try:
            self.iconify()
        except Exception:
            pass

    def _on_maximize(self) -> None:
        """Handle maximize button."""
        if not self._use_custom_titlebar:
            return

        if not self._is_maximized:
            self._restore_geometry = self.geometry()
            sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()

            try:
                self.wm_attributes("-transparentcolor", "")
                self.configure(bg=Colors.WINDOW_BG, fg_color=Colors.WINDOW_BG)
            except Exception:
                pass

            self._main_frame.configure(corner_radius=0)
            self._main_frame.pack_configure(padx=0, pady=0)
            self.geometry(f"{sw}x{sh}+0+0")
            self._is_maximized = True
        else:
            if self._restore_geometry:
                self.geometry(self._restore_geometry)

            try:
                self.configure(bg=self._transparent_color, fg_color=self._transparent_color)
                self.wm_attributes("-transparentcolor", self._transparent_color)
            except Exception:
                pass

            self._main_frame.configure(corner_radius=Dimensions.CORNER_RADIUS_LG)
            self._main_frame.pack_configure(
                padx=Dimensions.PADDING_LG,
                pady=Dimensions.PADDING_LG,
            )
            self._is_maximized = False

    def _on_browse(self) -> None:
        """Handle browse button."""
        folder = filedialog.askdirectory(title="Select Root Folder")
        if folder:
            self._path_var.set(folder)

    def _on_theme_change(self, value: str) -> None:
        """Handle theme change."""
        modes = {"System": "system", "Light": "light", "Dark": "dark"}
        ctk.set_appearance_mode(modes.get(value, "light"))

    def _on_save_log(self) -> None:
        """Handle save log button."""
        content = self._log_textbox.get("1.0", "end").strip()

        if not content:
            messagebox.showinfo("Save Log", "Log is empty.")
            return

        path = filedialog.asksaveasfilename(
            title="Save Log",
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
        )

        if path:
            try:
                Path(path).write_text(content, encoding="utf-8")
                messagebox.showinfo("Save Log", f"Saved to:\n{path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save:\n{e}")

    def _on_run(self) -> None:
        """Handle run button."""
        root = self._path_var.get().strip()
        suffix = self._suffix_var.get().strip()

        if not root:
            messagebox.showerror("Error", "Please select a folder.")
            return
        if not os.path.isdir(root):
            messagebox.showerror("Error", "Folder does not exist.")
            return
        if not suffix:
            messagebox.showerror("Error", "Please enter a suffix.")
            return

        try:
            config = MergeConfig(
                root_path=root,
                suffix=suffix,
                ignore_case=self._ignore_case_var.get(),
                dry_run=self._dry_run_var.get(),
                create_backup=self._backup_var.get(),
                conflict_mode=ConflictMode(self._conflict_var.get()),
            )
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return

        summary = "\n".join([
            f"Folder: {config.root_path}",
            f"Suffix: '{config.suffix}'",
            f"Ignore case: {'Yes' if config.ignore_case else 'No'}",
            f"Conflict: {config.conflict_mode.value}",
            f"Dry run: {'Yes' if config.dry_run else 'No'}",
            f"Backup: {'Yes' if config.create_backup else 'No'}",
        ])

        if not messagebox.askyesno("Confirm", f"Proceed with:\n\n{summary}"):
            return

        # Clear and start
        self._log_textbox.configure(state="normal")
        self._log_textbox.delete("1.0", "end")
        self._log_textbox.configure(state="disabled")

        self._progress_bar.set(0)
        self._status_label.configure(text="Preparing...")
        self._set_running(True)

        self._worker_thread = threading.Thread(
            target=self._execute_merge,
            args=(config,),
            daemon=True,
        )
        self._worker_thread.start()

    # -------------------------------------------------------------------------
    # Merge Execution
    # -------------------------------------------------------------------------

    def _execute_merge(self, config: MergeConfig) -> None:
        """Execute merge in background thread."""
        ctx = OperationContext(
            config=config,
            log_fn=self._log,
            progress_fn=self._set_progress,
            status_fn=self._set_status,
        )

        error: Optional[Exception] = None

        try:
            ctx.log("═" * 50)
            ctx.log("FOLDER SUFFIX MERGER")
            ctx.log("═" * 50)
            ctx.log(f"Root     : {config.root_path}")
            ctx.log(f"Suffix   : '{config.suffix}'")
            ctx.log(f"Case     : {'ignore' if config.ignore_case else 'sensitive'}")
            ctx.log(f"Mode     : {'DRY RUN' if config.dry_run else 'LIVE'}")
            ctx.log(f"Backup   : {'yes' if config.create_backup else 'no'}")
            ctx.log(f"Conflict : {config.conflict_mode.value}")
            ctx.log("─" * 50)

            self.after(0, lambda: self._set_progress_mode(True))

            ctx.status("Scanning...")
            plan = MergePlanner.build_plan(
                config.root_path,
                config.suffix,
                config.ignore_case,
            )

            self.after(0, lambda: self._set_progress_mode(False))

            ctx.stats.folders_planned = len(plan)

            if not plan:
                ctx.log("No matching folders found.")
                ctx.status("Done: nothing to merge")
                ctx.progress(1.0)
                return

            ctx.log(f"Found {len(plan)} folder(s)")
            ctx.log("─" * 50)

            if config.create_backup:
                BackupManager.create_archive(config.root_path, ctx)

            ctx.status("Merging...")
            MergeExecutor(ctx).execute(plan)

            ctx.status("Complete")
            ctx.progress(1.0)

            ctx.log("─" * 50)
            ctx.log("SUMMARY")
            ctx.log("─" * 50)
            ctx.log(ctx.stats.to_summary())
            ctx.log("═" * 50)

            self.after(0, self._celebrate)
            self.after(0, lambda: self._show_summary(ctx.stats, config))

        except Exception as e:
            error = e
            self.after(0, lambda: self._set_progress_mode(False))
            ctx.log(f"ERROR: {e}")
            ctx.status(f"Error: {e}")

        finally:
            self.after(0, lambda: self._set_running(False))
            if error:
                self.after(0, lambda: messagebox.showerror("Error", str(error)))

    def _show_summary(self, stats: OperationStats, config: MergeConfig) -> None:
        """Show completion summary dialog."""
        text = "\n".join([
            stats.to_summary(),
            "",
            f"Mode: {'DRY RUN' if config.dry_run else 'LIVE'}",
        ])
        messagebox.showinfo("Complete", text)

    # -------------------------------------------------------------------------
    # Thread-Safe UI Updates
    # -------------------------------------------------------------------------

    def _log(self, message: str) -> None:
        """Append to log (thread-safe)."""
        def write():
            self._log_textbox.configure(state="normal")
            self._log_textbox.insert("end", message + "\n")
            self._log_textbox.see("end")
            self._log_textbox.configure(state="disabled")

        self.after(0, write)

    def _set_progress(self, value: float) -> None:
        """Set progress (thread-safe)."""
        self.after(0, lambda: self._progress_bar.set(value))

    def _set_status(self, text: str) -> None:
        """Set status (thread-safe)."""
        self.after(0, lambda: self._status_label.configure(text=text))

    def _set_progress_mode(self, indeterminate: bool) -> None:
        """Toggle progress bar mode."""
        if indeterminate:
            self._progress_bar.configure(mode="indeterminate")
            self._progress_bar.start()
        else:
            try:
                self._progress_bar.stop()
            except Exception:
                pass
            self._progress_bar.configure(mode="determinate")


# =============================================================================
# Entry Point
# =============================================================================


def main() -> None:
    """Application entry point."""
    app = FolderMergerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
