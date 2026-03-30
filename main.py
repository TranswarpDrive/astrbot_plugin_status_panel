from __future__ import annotations

import asyncio
import base64
import mimetypes
import os
import platform
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import psutil
from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register

try:
    import pynvml  # type: ignore
except ImportError:  # pragma: no cover
    pynvml = None


PLUGIN_NAME = "astrbot_plugin_status_panel"
BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = BASE_DIR / "templates" / "status_panel.html"
HELP_TOKENS = {"help", "-h", "--help", "?"}
IMAGE_TOKENS = {"image", "img", "pic", "png", "render"}
TEXT_TOKENS = {"text", "txt", "plain"}


@register(
    PLUGIN_NAME,
    "Codex",
    "QQ status panel for AstrBot on OneBot v11 / NapCat.",
    "1.0.0",
)
class StatusPanelPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig | None = None):
        super().__init__(context)
        self.config = config or {}
        self.template = TEMPLATE_PATH.read_text(encoding="utf-8")
        self.astrbot_process = psutil.Process(os.getpid())

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.event_message_type(filter.EventMessageType.ALL)
    async def handle_status_command(self, event: AstrMessageEvent):
        """Handle \\status for OneBot v11 based QQ bots."""

        command_mode = self._parse_status_command((event.message_str or "").strip())
        if command_mode is None:
            return

        if command_mode in HELP_TOKENS:
            yield event.plain_result(self._build_help_text())
            return

        snapshot = await self._collect_snapshot()
        reply_mode = self._resolve_reply_mode(command_mode)

        if reply_mode == "image":
            try:
                image_url = await self._render_snapshot_image(event, snapshot)
                yield event.image_result(image_url)
                return
            except Exception as exc:  # pragma: no cover
                logger.warning(
                    "status_panel image render failed, fallback to text: %s",
                    exc,
                )

        yield event.plain_result(self._render_snapshot_text(snapshot))

    def _parse_status_command(self, message: str) -> str | None:
        match = re.match(r"^[\\/](status)(?:\s+(.+))?$", message, re.IGNORECASE)
        if not match:
            return None

        arg_text = (match.group(2) or "").strip()
        if not arg_text:
            return ""
        return arg_text.split()[0].strip().lower()

    def _resolve_reply_mode(self, requested_mode: str) -> str:
        if requested_mode in IMAGE_TOKENS:
            return "image"
        if requested_mode in TEXT_TOKENS:
            return "text"

        configured = str(self.config.get("reply_mode", "image")).strip().lower()
        if configured in {"image", "text"}:
            return configured
        return "image"

    async def _collect_snapshot(self) -> dict[str, Any]:
        cpu_percent, read_speed, write_speed, top_processes = await self._sample_runtime()
        memory = psutil.virtual_memory()

        disk_root = self._detect_disk_root()
        disk_usage = psutil.disk_usage(str(disk_root))
        gpus = self._collect_gpus()

        cpu_freq = psutil.cpu_freq()
        cpu_name = self._resolve_cpu_name()
        boot_time = psutil.boot_time()
        process_start = self.astrbot_process.create_time()

        return {
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "hostname": platform.node() or "Unknown host",
            "system": self._build_system_label(),
            "python_version": platform.python_version(),
            "cpu": {
                "name": cpu_name,
                "percent": round(cpu_percent, 1),
                "cores_physical": psutil.cpu_count(logical=False) or 0,
                "cores_logical": psutil.cpu_count(logical=True) or 0,
                "frequency": round((cpu_freq.current if cpu_freq else 0.0) / 1000, 2),
            },
            "memory": {
                "used": memory.used,
                "total": memory.total,
                "percent": round(memory.percent, 1),
            },
            "disk": {
                "path": str(disk_root),
                "used": disk_usage.used,
                "total": disk_usage.total,
                "percent": round((disk_usage.used / disk_usage.total) * 100, 1)
                if disk_usage.total
                else 0.0,
                "read_speed": read_speed,
                "write_speed": write_speed,
            },
            "gpus": gpus,
            "device_uptime_seconds": max(time.time() - boot_time, 0),
            "astrbot_uptime_seconds": max(time.time() - process_start, 0),
            "top_processes": top_processes,
        }

    async def _sample_runtime(self) -> tuple[float, float, float, list[dict[str, Any]]]:
        sample_window = 0.35
        process_limit = max(int(self.config.get("process_count", 6) or 6), 1)

        candidates = []
        psutil.cpu_percent(interval=None)
        disk_before = psutil.disk_io_counters()

        for proc in psutil.process_iter(attrs=["pid", "name", "memory_percent"]):
            try:
                proc.cpu_percent(interval=None)
                candidates.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        await asyncio.sleep(sample_window)

        cpu_percent = psutil.cpu_percent(interval=None)
        disk_after = psutil.disk_io_counters()
        if disk_before and disk_after:
            read_speed = max(disk_after.read_bytes - disk_before.read_bytes, 0) / sample_window
            write_speed = max(disk_after.write_bytes - disk_before.write_bytes, 0) / sample_window
        else:
            read_speed = 0.0
            write_speed = 0.0

        top_processes: list[dict[str, Any]] = []
        for proc in candidates:
            try:
                cpu = proc.cpu_percent(interval=None)
                info = proc.info
                top_processes.append(
                    {
                        "pid": proc.pid,
                        "name": info.get("name") or f"pid-{proc.pid}",
                        "cpu_percent": round(cpu, 1),
                        "memory_percent": round(float(info.get("memory_percent") or 0.0), 1),
                    }
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        top_processes.sort(
            key=lambda item: (item["cpu_percent"], item["memory_percent"], item["name"]),
            reverse=True,
        )
        return cpu_percent, read_speed, write_speed, top_processes[:process_limit]

    def _collect_gpus(self) -> list[dict[str, Any]]:
        if pynvml is not None:
            try:
                pynvml.nvmlInit()
                gpu_count = pynvml.nvmlDeviceGetCount()
                gpus = []
                for index in range(gpu_count):
                    handle = pynvml.nvmlDeviceGetHandleByIndex(index)
                    name = pynvml.nvmlDeviceGetName(handle)
                    if isinstance(name, bytes):
                        name = name.decode("utf-8", errors="ignore")
                    util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    gpus.append(
                        {
                            "name": str(name),
                            "percent": round(float(util.gpu), 1),
                            "memory_used": int(mem.used),
                            "memory_total": int(mem.total),
                        }
                    )
                pynvml.nvmlShutdown()
                if gpus:
                    return gpus
            except Exception as exc:  # pragma: no cover
                logger.debug("status_panel NVML unavailable: %s", exc)
                try:
                    pynvml.nvmlShutdown()
                except Exception:
                    pass

        return [
            {
                "name": name,
                "percent": None,
                "memory_used": None,
                "memory_total": None,
            }
            for name in self._fallback_gpu_names()
        ]

    def _fallback_gpu_names(self) -> list[str]:
        if os.name == "nt":
            lines = self._run_command(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name",
                ]
            )
            return self._unique_lines(lines)

        if Path("/usr/bin/lspci").exists() or Path("/bin/lspci").exists():
            lines = self._run_command(["lspci"])
            return self._unique_lines(
                line.split(": ", 1)[-1]
                for line in lines
                if re.search(r"(VGA|3D|Display)", line, re.IGNORECASE)
            )

        return []

    def _resolve_cpu_name(self) -> str:
        cpu_name = platform.processor().strip()
        if cpu_name:
            return cpu_name

        if os.name == "nt":
            lines = self._run_command(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "Get-CimInstance Win32_Processor | Select-Object -ExpandProperty Name",
                ]
            )
            if lines:
                return lines[0]

        cpuinfo = Path("/proc/cpuinfo")
        if cpuinfo.exists():
            for line in cpuinfo.read_text(encoding="utf-8", errors="ignore").splitlines():
                if line.lower().startswith("model name"):
                    return line.split(":", 1)[-1].strip()

        return "Unknown CPU"

    def _build_system_label(self) -> str:
        system = platform.system() or "Unknown OS"
        release = platform.release() or ""
        version = platform.version() or ""
        bits, _ = platform.architecture()
        label = " ".join(part for part in [system, release, bits] if part).strip()
        if version and version not in label:
            label = f"{label} ({version})"
        return label

    def _detect_disk_root(self) -> Path:
        cwd = Path.cwd()
        anchor = cwd.anchor or os.sep
        return Path(anchor)

    async def _render_snapshot_image(self, event: AstrMessageEvent, snapshot: dict[str, Any]) -> str:
        avatar_src = self._resolve_avatar_source(event)
        nickname = self._resolve_bot_nickname()
        primary_gpu = snapshot["gpus"][0] if snapshot["gpus"] else None

        data = {
            "title": "AstrBot Status Panel",
            "bot_name": nickname,
            "bot_id": str(getattr(event.message_obj, "self_id", "") or ""),
            "avatar_src": avatar_src,
            "updated_at": snapshot["updated_at"],
            "hostname": snapshot["hostname"],
            "system": snapshot["system"],
            "python_version": snapshot["python_version"],
            "device_uptime": self._format_duration(snapshot["device_uptime_seconds"]),
            "astrbot_uptime": self._format_duration(snapshot["astrbot_uptime_seconds"]),
            "cards": [
                {
                    "label": "CPU",
                    "headline": f'{snapshot["cpu"]["percent"]:.1f}%',
                    "title": snapshot["cpu"]["name"],
                    "subline": f'{snapshot["cpu"]["cores_physical"]}P / {snapshot["cpu"]["cores_logical"]}T',
                    "extra": (
                        f'{snapshot["cpu"]["frequency"]:.2f} GHz'
                        if snapshot["cpu"]["frequency"] > 0
                        else "Frequency unavailable"
                    ),
                    "percent": snapshot["cpu"]["percent"],
                    "accent": "#ff8a5b",
                },
                {
                    "label": "GPU",
                    "headline": (
                        f'{primary_gpu["percent"]:.1f}%'
                        if primary_gpu and primary_gpu["percent"] is not None
                        else "N/A"
                    ),
                    "title": primary_gpu["name"] if primary_gpu else "No GPU detected",
                    "subline": (
                        f'{self._format_bytes(primary_gpu["memory_used"])} / {self._format_bytes(primary_gpu["memory_total"])}'
                        if primary_gpu
                        and primary_gpu["memory_used"] is not None
                        and primary_gpu["memory_total"] is not None
                        else "Telemetry unavailable"
                    ),
                    "extra": f'{len(snapshot["gpus"])} device(s)',
                    "percent": primary_gpu["percent"] if primary_gpu and primary_gpu["percent"] is not None else 0,
                    "accent": "#7fe36e",
                },
                {
                    "label": "RAM",
                    "headline": f'{snapshot["memory"]["percent"]:.1f}%',
                    "title": f'{self._format_bytes(snapshot["memory"]["used"])} / {self._format_bytes(snapshot["memory"]["total"])}',
                    "subline": "System memory",
                    "extra": "Virtual memory usage",
                    "percent": snapshot["memory"]["percent"],
                    "accent": "#6fb6ff",
                },
                {
                    "label": "Disk",
                    "headline": f'{snapshot["disk"]["percent"]:.1f}%',
                    "title": f'{self._format_bytes(snapshot["disk"]["used"])} / {self._format_bytes(snapshot["disk"]["total"])}',
                    "subline": snapshot["disk"]["path"],
                    "extra": f'R {self._format_rate(snapshot["disk"]["read_speed"])} | W {self._format_rate(snapshot["disk"]["write_speed"])}',
                    "percent": snapshot["disk"]["percent"],
                    "accent": "#f3d66b",
                },
            ],
            "runtime_items": [
                {"label": "Host", "value": snapshot["hostname"]},
                {"label": "System", "value": snapshot["system"]},
                {"label": "Python", "value": snapshot["python_version"]},
                {"label": "Updated", "value": snapshot["updated_at"]},
                {"label": "Device Uptime", "value": self._format_duration(snapshot["device_uptime_seconds"])},
                {"label": "AstrBot Uptime", "value": self._format_duration(snapshot["astrbot_uptime_seconds"])},
            ],
            "gpu_items": [
                {
                    "name": gpu["name"],
                    "utilization": (
                        f'{gpu["percent"]:.1f}%'
                        if gpu["percent"] is not None
                        else "Unavailable"
                    ),
                    "memory": (
                        f'{self._format_bytes(gpu["memory_used"])} / {self._format_bytes(gpu["memory_total"])}'
                        if gpu["memory_used"] is not None and gpu["memory_total"] is not None
                        else "Unavailable"
                    ),
                }
                for gpu in snapshot["gpus"]
            ],
            "process_items": [
                {
                    "index": index + 1,
                    "name": process["name"],
                    "pid": process["pid"],
                    "cpu": f'{process["cpu_percent"]:.1f}%',
                    "memory": f'{process["memory_percent"]:.1f}%',
                }
                for index, process in enumerate(snapshot["top_processes"])
            ],
        }

        return await self.html_render(
            self.template,
            data,
            options={
                "type": "png",
                "timeout": 30000,
                "animations": "disabled",
                "scale": "device",
                "full_page": True,
            },
        )

    def _render_snapshot_text(self, snapshot: dict[str, Any]) -> str:
        lines = [
            "AstrBot Status Panel",
            f'Updated: {snapshot["updated_at"]}',
            f'Host: {snapshot["hostname"]}',
            f'System: {snapshot["system"]}',
            f'Python: {snapshot["python_version"]}',
            "",
            (
                "CPU: "
                f'{snapshot["cpu"]["name"]} | '
                f'{snapshot["cpu"]["percent"]:.1f}% | '
                f'{snapshot["cpu"]["cores_physical"]}P/{snapshot["cpu"]["cores_logical"]}T'
            ),
            (
                "RAM: "
                f'{self._format_bytes(snapshot["memory"]["used"])} / '
                f'{self._format_bytes(snapshot["memory"]["total"])} '
                f'({snapshot["memory"]["percent"]:.1f}%)'
            ),
            (
                "Disk: "
                f'{snapshot["disk"]["path"]} | '
                f'{self._format_bytes(snapshot["disk"]["used"])} / '
                f'{self._format_bytes(snapshot["disk"]["total"])} '
                f'({snapshot["disk"]["percent"]:.1f}%) | '
                f'R {self._format_rate(snapshot["disk"]["read_speed"])} | '
                f'W {self._format_rate(snapshot["disk"]["write_speed"])}'
            ),
        ]

        if snapshot["gpus"]:
            lines.append("GPU:")
            for gpu in snapshot["gpus"]:
                gpu_line = f'- {gpu["name"]}'
                if gpu["percent"] is not None:
                    gpu_line += f' | {gpu["percent"]:.1f}%'
                if gpu["memory_used"] is not None and gpu["memory_total"] is not None:
                    gpu_line += (
                        f' | {self._format_bytes(gpu["memory_used"])} / '
                        f'{self._format_bytes(gpu["memory_total"])}'
                    )
                lines.append(gpu_line)
        else:
            lines.append("GPU: No GPU detected")

        lines.extend(
            [
                "",
                f'Device uptime: {self._format_duration(snapshot["device_uptime_seconds"])}',
                f'AstrBot uptime: {self._format_duration(snapshot["astrbot_uptime_seconds"])}',
                "",
                "Top processes:",
            ]
        )

        if snapshot["top_processes"]:
            for index, process in enumerate(snapshot["top_processes"], start=1):
                lines.append(
                    f'{index}. {process["name"]} (PID {process["pid"]}) | '
                    f'CPU {process["cpu_percent"]:.1f}% | MEM {process["memory_percent"]:.1f}%'
                )
        else:
            lines.append("No process data available")

        return "\n".join(lines)

    def _build_help_text(self) -> str:
        return (
            "Usage:\n"
            "\\status            Use the default reply mode from plugin config.\n"
            "\\status image      Force image mode for this request.\n"
            "\\status text       Force plain-text mode for this request.\n"
            "\\status help       Show this help message.\n\n"
            "The plugin also accepts /status as an alias."
        )

    def _resolve_bot_nickname(self) -> str:
        nickname = str(self.config.get("bot_nickname", "") or "").strip()
        return nickname or "astrbot"

    def _resolve_avatar_source(self, event: AstrMessageEvent) -> str:
        avatar_file = self._normalize_uploaded_file(self.config.get("avatar_file"))
        if avatar_file:
            avatar_data_uri = self._file_to_data_uri(avatar_file)
            if avatar_data_uri:
                return avatar_data_uri

        avatar_url = str(self.config.get("avatar_url", "") or "").strip()
        if avatar_url:
            return avatar_url

        bot_qq = str(getattr(event.message_obj, "self_id", "") or "").strip()
        if bot_qq.isdigit():
            return f"https://q1.qlogo.cn/g?b=qq&nk={bot_qq}&s=640"
        return "https://q1.qlogo.cn/g?b=qq&nk=10000&s=640"

    def _normalize_uploaded_file(self, value: Any) -> str:
        if not value:
            return ""

        if isinstance(value, list):
            for item in value:
                normalized = self._normalize_uploaded_file(item)
                if normalized:
                    return normalized
            return ""

        if isinstance(value, str):
            return value.strip()

        if isinstance(value, dict):
            for key in ("path", "file_path", "local_path", "url", "value", "name"):
                raw_value = value.get(key)
                if isinstance(raw_value, str) and raw_value.strip():
                    return raw_value.strip()

        return ""

    def _file_to_data_uri(self, file_ref: str) -> str:
        file_path = Path(file_ref)
        if not file_path.is_absolute():
            file_path = (Path.cwd() / file_path).resolve()
        if not file_path.exists() or not file_path.is_file():
            return ""

        mime_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        encoded = base64.b64encode(file_path.read_bytes()).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"

    def _run_command(self, command: list[str]) -> list[str]:
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=2,
                check=False,
            )
        except Exception:
            return []

        if completed.returncode != 0 and not completed.stdout:
            return []
        return [line.strip() for line in completed.stdout.splitlines() if line.strip()]

    def _unique_lines(self, values: Any) -> list[str]:
        seen = set()
        unique = []
        for value in values:
            line = str(value).strip()
            if not line or line in seen:
                continue
            seen.add(line)
            unique.append(line)
        return unique

    def _format_bytes(self, size: int | float | None) -> str:
        if size is None:
            return "N/A"

        value = float(size)
        units = ["B", "KB", "MB", "GB", "TB", "PB"]
        for unit in units:
            if value < 1024 or unit == units[-1]:
                return f"{value:.1f} {unit}"
            value /= 1024
        return f"{value:.1f} PB"

    def _format_rate(self, size_per_second: float | None) -> str:
        if size_per_second is None:
            return "N/A"
        return f"{self._format_bytes(size_per_second)}/s"

    def _format_duration(self, seconds: float) -> str:
        total_seconds = max(int(seconds), 0)
        days, remainder = divmod(total_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, secs = divmod(remainder, 60)

        parts = []
        if days:
            parts.append(f"{days}d")
        if hours or parts:
            parts.append(f"{hours}h")
        if minutes or parts:
            parts.append(f"{minutes}m")
        parts.append(f"{secs}s")
        return " ".join(parts)

    async def terminate(self):
        return
