"""插件拉取 / 启停管理"""

from __future__ import annotations

import os
import re
import signal
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
import yaml

_ROOT = Path(__file__).resolve().parents[2]
_EXT_ROOT = _ROOT / "_ext_targets"
_LOG_ROOT = Path(__file__).resolve().parent / "external_logs"
_LOG_ROOT.mkdir(parents=True, exist_ok=True)

_REMOTE_URLS = {
    "cliproxyapi": "https://github.com/router-for-me/CLIProxyAPI.git",
    "cpa-codex-cleanup": "https://github.com/qcmuu/cpa-codex-cleanup.git",
    "resin": "https://github.com/Resinat/Resin.git",
    "goproxy": "https://github.com/isboyjc/GoProxy.git",
    "grok2api": "https://github.com/chenyme/grok2api.git",
    "kiro-manager": "https://github.com/hj01857655/kiro-account-manager.git",
}

_KIRO_MANAGER_MSI_URL = (
    "https://github.com/hj01857655/kiro-account-manager/releases/download/"
    "v1.8.3/KiroAccountManager_1.8.3_x64_zh-CN.msi"
)
_KIRO_MANAGER_MSI = _EXT_ROOT / "KiroAccountManager_1.8.3_x64_zh-CN.msi"
_KIRO_MANAGER_EXTRACT_DIR = _EXT_ROOT / "kiro-manager-msi-extract"
_KIRO_MANAGER_EXTRACT_EXE = _KIRO_MANAGER_EXTRACT_DIR / "PFiles" / "KiroAccountManager" / "kiro-account-manager.exe"

_SERVICE_META = {
    "cliproxyapi": {
        "label": "CLIProxyAPI",
        "repo_name": "CLIProxyAPI",
        "url": "http://127.0.0.1:8317",
        "health": "http://127.0.0.1:8317/",
        "management_url": "http://127.0.0.1:8317/management.html",
        "port": 8317,
        "startup_timeout": 180,
        "kind": "web",
    },
    "cpa-codex-cleanup": {
        "label": "CPA Codex Cleanup",
        "repo_name": "cpa-codex-cleanup",
        "url": "http://127.0.0.1:39023",
        "health": "http://127.0.0.1:39023/api/defaults",
        "management_url": "http://127.0.0.1:39023",
        "port": 39023,
        "startup_timeout": 90,
        "kind": "web",
    },
    "resin": {
        "label": "Resin",
        "repo_name": "Resin",
        "url": "http://127.0.0.1:39024",
        "health": "http://127.0.0.1:39024/healthz",
        "management_url": "http://127.0.0.1:39024",
        "port": 39024,
        "startup_timeout": 300,
        "kind": "web",
    },
    "goproxy": {
        "label": "GoProxy",
        "repo_name": "GoProxy",
        "url": "http://127.0.0.1:7778",
        "health": "http://127.0.0.1:7778",
        "management_url": "http://127.0.0.1:7778",
        "port": 7778,
        "startup_timeout": 180,
        "kind": "web",
    },
    "grok2api": {
        "label": "grok2api",
        "repo_name": "grok2api",
        "url": "http://127.0.0.1:8011",
        "health": "http://127.0.0.1:8011/health",
        "management_url": "http://127.0.0.1:8011/admin",
        "port": 8011,
        "startup_timeout": 180,
        "kind": "web",
    },
    "kiro-manager": {
        "label": "Kiro Account Manager",
        "repo_name": "kiro-account-manager",
        "url": "",
        "health": "",
        "kind": "desktop",
    },
}

_PROCS: dict[str, subprocess.Popen] = {}
_LOG_FILES: dict[str, Any] = {}
_LAST_ERROR: dict[str, str] = {}
_LOCK = threading.Lock()


def _get_setting(key: str, default: str = "") -> str:
    try:
        from core.config_store import config_store

        value = str(config_store.get(key, "") or "").strip()
        return value or default
    except Exception:
        return default


def _creationflags() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _popen_kwargs() -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "creationflags": _creationflags(),
        "stdin": subprocess.DEVNULL,
    }
    if os.name != "nt":
        kwargs["start_new_session"] = True
    return kwargs


def _repo_path(name: str) -> Path:
    return _EXT_ROOT / _SERVICE_META[name]["repo_name"]


def _log_path(name: str) -> Path:
    return _LOG_ROOT / f"{name}.log"


def _cliproxyapi_management_ui_url() -> str:
    configured_url = _get_setting("cliproxyapi_url", "").rstrip("/")
    if configured_url:
        return f"{configured_url}/management.html"
    return "http://127.0.0.1:8317/management.html"


def _public_service_url_from_known_hosts(port: int, default: str) -> str:
    for raw_url in (
        _get_setting("resin_url", "").strip(),
        _get_setting("cliproxyapi_url", "").strip(),
    ):
        if not raw_url:
            continue

        parsed = urlparse(raw_url)
        if not parsed.scheme or not parsed.hostname:
            continue

        return f"{parsed.scheme}://{parsed.hostname}:{port}"
    return default


def _main_site_public_url() -> str:
    return _public_service_url_from_known_hosts(39001, "http://127.0.0.1:39001")


def _goproxy_management_proxy_url() -> str:
    return f"{_main_site_public_url().rstrip('/')}/api/integrations/goproxy/"


def _close_log(name: str):
    f = _LOG_FILES.pop(name, None)
    if f:
        try:
            f.close()
        except Exception:
            pass


def _open_log(name: str):
    _close_log(name)
    f = open(_log_path(name), "a", encoding="utf-8")
    _LOG_FILES[name] = f
    return f


def _clone_repo_if_missing(name: str):
    repo = _repo_path(name)
    if repo.exists() and (repo / ".git").exists():
        return
    if repo.exists():
        shutil.rmtree(repo, ignore_errors=True)
    repo.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "clone", _REMOTE_URLS[name], str(repo)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=_creationflags(),
    )


def install(name: str) -> dict[str, Any]:
    with _LOCK:
        if name not in _SERVICE_META:
            raise KeyError(name)
        _clone_repo_if_missing(name)
    return _status_one(name)


def _health_ok(name: str) -> bool:
    url = _SERVICE_META[name].get("health")
    if not url:
        return False
    try:
        r = requests.get(url, timeout=2)
        return r.status_code < 500
    except Exception:
        return False


def _find_pid_by_port(port: int) -> int | None:
    if not port:
        return None
    if os.name == "nt":
        try:
            out = subprocess.check_output(
                ["netstat", "-ano", "-p", "tcp"],
                text=True,
                creationflags=_creationflags(),
            )
        except Exception:
            return None
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 5 and parts[0].upper() == "TCP":
                local = parts[1]
                state = parts[3].upper()
                pid = parts[4]
                if local.endswith(f":{port}") and state == "LISTENING":
                    try:
                        return int(pid)
                    except Exception:
                        return None
        return None

    lsof = shutil.which("lsof")
    if lsof:
        try:
            out = subprocess.check_output(
                [lsof, "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"],
                text=True,
                stderr=subprocess.DEVNULL,
                creationflags=_creationflags(),
            )
            for line in out.splitlines():
                if line.strip().isdigit():
                    return int(line.strip())
        except Exception:
            pass

    ss = shutil.which("ss")
    if ss:
        try:
            out = subprocess.check_output(
                [ss, "-ltnp"],
                text=True,
                stderr=subprocess.DEVNULL,
                creationflags=_creationflags(),
            )
            for line in out.splitlines():
                if f":{port}" not in line:
                    continue
                match = re.search(r"pid=(\d+)", line)
                if match:
                    return int(match.group(1))
        except Exception:
            pass
    return None


def _terminate_pid(pid: int | None):
    if not pid:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=_creationflags(),
        )
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    except Exception:
        pass


def _proc_running(name: str) -> bool:
    proc = _PROCS.get(name)
    return bool(proc and proc.poll() is None)


def _kiro_known_exe_paths() -> list[str]:
    candidates: list[str] = []
    try:
        from core.config_store import config_store

        configured = str(config_store.get("kiro_manager_exe", "") or "").strip()
        if configured and Path(configured).exists():
            candidates.append(str(Path(configured).resolve()).lower())
    except Exception:
        pass

    for item in [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "KiroAccountManager" / "KiroAccountManager.exe",
        Path(os.environ.get("ProgramFiles", "")) / "KiroAccountManager" / "KiroAccountManager.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "kiro-account-manager" / "kiro-account-manager.exe",
        Path(os.environ.get("ProgramFiles", "")) / "kiro-account-manager" / "kiro-account-manager.exe",
        _KIRO_MANAGER_EXTRACT_EXE,
    ]:
        if item.exists():
            candidates.append(str(item.resolve()).lower())
    return candidates


def _find_desktop_pid(name: str) -> int | None:
    if name != "kiro-manager":
        return None

    target_paths = set(_kiro_known_exe_paths())

    try:
        processes = subprocess.check_output(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-CimInstance Win32_Process | "
                "Where-Object { $_.Name -in @('KiroAccountManager.exe','kiro-account-manager.exe') } | "
                "Select-Object ProcessId,ExecutablePath | ConvertTo-Json -Compress",
            ],
            text=True,
            creationflags=_creationflags(),
        ).strip()
    except Exception:
        return None

    if not processes:
        return None

    try:
        import json

        data = json.loads(processes)
        items = data if isinstance(data, list) else [data]
        for item in items:
            pid = item.get("ProcessId")
            exe = str(item.get("ExecutablePath") or "").strip()
            if not pid:
                continue
            if not target_paths:
                return int(pid)
            if exe:
                try:
                    if str(Path(exe).resolve()).lower() in target_paths:
                        return int(pid)
                except Exception:
                    if exe.lower() in target_paths:
                        return int(pid)
    except Exception:
        return None

    return None


def _status_one(name: str) -> dict[str, Any]:
    meta = _SERVICE_META[name]
    repo = _repo_path(name)
    proc = _PROCS.get(name)
    desktop_pid = _find_desktop_pid(name) if meta["kind"] == "desktop" else None
    running = _health_ok(name) if meta["kind"] == "web" else bool(desktop_pid or _proc_running(name))
    pid = proc.pid if proc and proc.poll() is None else desktop_pid
    url = meta.get("url", "")
    management_url = meta.get("management_url", "")
    if name == "cliproxyapi":
        configured_url = _get_setting("cliproxyapi_url", "")
        if configured_url:
            url = configured_url.rstrip("/")
            management_url = f"{url}/management.html"
    elif name == "cpa-codex-cleanup":
        public_url = _public_service_url_from_known_hosts(int(meta.get("port") or 39023), url)
        url = public_url
        management_url = public_url
    elif name == "resin":
        configured = _get_setting("resin_url", "").strip()
        if configured:
            url = configured.rstrip("/")
            management_url = url
    elif name == "goproxy":
        proxied_url = _goproxy_management_proxy_url()
        url = proxied_url
        management_url = proxied_url
    if meta["kind"] == "web" and running:
        pid = _find_pid_by_port(int(meta.get("port") or 0)) or pid
    return {
        "name": name,
        "label": meta["label"],
        "repo_path": str(repo),
        "repo_exists": repo.exists(),
        "url": url,
        "management_url": management_url,
        "management_key": (
            _get_setting("cliproxyapi_management_key", "cliproxyapi")
            if name in {"cliproxyapi", "cpa-codex-cleanup"}
            else _get_setting("resin_admin_token", "resin-admin")
            if name == "resin"
            else _get_setting("goproxy_webui_password", "goproxy")
            if name == "goproxy"
            else _get_setting("grok2api_app_key", "grok2api")
            if name == "grok2api"
            else ""
        ),
        "running": running,
        "pid": pid,
        "log_path": str(_log_path(name)),
        "last_error": _LAST_ERROR.get(name, ""),
        "kind": meta["kind"],
    }


def list_status() -> list[dict[str, Any]]:
    return [_status_one(name) for name in _SERVICE_META]


def _find_go() -> str | None:
    candidates = [
        shutil.which("go"),
        "/usr/local/bin/go",
        "/usr/local/go/bin/go",
        "/opt/go/bin/go",
        str(Path.home() / "go" / "pkg" / "mod" / "golang.org" / "toolchain@v0.0.1-go1.24.10.windows-amd64" / "bin" / "go.exe"),
        str(Path.home() / "go" / "pkg" / "mod" / "golang.org" / "toolchain@v0.0.1-go1.24.0.windows-amd64" / "bin" / "go.exe"),
        r"C:\Program Files\Go\bin\go.exe",
    ]
    for item in candidates:
        if item and Path(item).exists():
            return item
    return None


def _conda_exe() -> str | None:
    candidates = [
        shutil.which("conda"),
        r"D:\miniconda\conda3\Scripts\conda.exe",
        r"D:\miniconda\conda3\Library\bin\conda.bat",
    ]
    for item in candidates:
        if item and Path(item).exists():
            return item
    return None


def _resolve_kiro_exe() -> str | None:
    try:
        from core.config_store import config_store

        configured = str(config_store.get("kiro_manager_exe", "") or "").strip()
        if configured and Path(configured).exists():
            return configured
    except Exception:
        pass
    candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "KiroAccountManager" / "KiroAccountManager.exe",
        Path(os.environ.get("ProgramFiles", "")) / "KiroAccountManager" / "KiroAccountManager.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "kiro-account-manager" / "kiro-account-manager.exe",
        Path(os.environ.get("ProgramFiles", "")) / "kiro-account-manager" / "kiro-account-manager.exe",
        _KIRO_MANAGER_EXTRACT_EXE,
    ]
    for item in candidates:
        if item.exists():
            return str(item)
    extracted = _ensure_kiro_extracted_exe()
    if extracted:
        return extracted
    return None


def _download_file(url: str, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)


def _ensure_kiro_extracted_exe() -> str | None:
    if _KIRO_MANAGER_EXTRACT_EXE.exists():
        return str(_KIRO_MANAGER_EXTRACT_EXE)
    if not _KIRO_MANAGER_MSI.exists():
        _download_file(_KIRO_MANAGER_MSI_URL, _KIRO_MANAGER_MSI)
    _KIRO_MANAGER_EXTRACT_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "msiexec.exe",
            "/a",
            str(_KIRO_MANAGER_MSI),
            f"TARGETDIR={_KIRO_MANAGER_EXTRACT_DIR}",
            "/qn",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=_creationflags(),
    )
    if _KIRO_MANAGER_EXTRACT_EXE.exists():
        return str(_KIRO_MANAGER_EXTRACT_EXE)
    return None


def _ensure_grok2api_conda_env(repo: Path) -> str:
    env_name = "grok2api-313"
    conda = _conda_exe()
    if not conda:
        raise RuntimeError("未找到 conda，无法为 grok2api 自动创建 Python 3.13 环境")

    check = subprocess.run(
        [conda, "run", "--no-capture-output", "-n", env_name, "python", "--version"],
        cwd=str(repo),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=_creationflags(),
    )
    if check.returncode != 0:
        subprocess.run(
            [conda, "create", "-y", "-n", env_name, "python=3.13"],
            cwd=str(repo),
            check=True,
            creationflags=_creationflags(),
        )

    marker = repo / ".grok2api-env-ready"
    if not marker.exists():
        subprocess.run(
            [conda, "run", "--no-capture-output", "-n", env_name, "python", "-m", "pip", "install", "--upgrade", "pip"],
            cwd=str(repo),
            check=True,
            creationflags=_creationflags(),
        )
        subprocess.run(
            [conda, "run", "--no-capture-output", "-n", env_name, "python", "-m", "pip", "install", "."],
            cwd=str(repo),
            check=True,
            creationflags=_creationflags(),
        )
        marker.write_text(env_name, encoding="utf-8")
    return env_name


def _ensure_cliproxyapi_runtime_config(repo: Path):
    config_path = repo / "config.local.yaml"
    secret = _get_setting("cliproxyapi_management_key", "cliproxyapi")
    source_path = config_path if config_path.exists() else repo / "config.example.yaml"
    raw = source_path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw) or {}
    remote_management = dict(data.get("remote-management") or {})
    remote_management["secret-key"] = secret
    data["remote-management"] = remote_management
    data["auth-maintenance"] = {
        "enable": True,
        "scan-interval-seconds": 30,
        "delete-interval-seconds": 5,
        "delete-status-codes": [401],
        "delete-quota-exceeded": True,
        "quota-strike-threshold": 6,
    }
    config_path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def _ensure_grok2api_runtime_config(repo: Path):
    data_dir = repo / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    config_file = data_dir / "config.toml"
    app_key = _get_setting("grok2api_app_key", "grok2api")
    default_config = repo / "config.defaults.toml"

    if not config_file.exists():
        if default_config.exists():
            config_file.write_text(default_config.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            config_file.write_text("[app]\n", encoding="utf-8")

    lines = config_file.read_text(encoding="utf-8").splitlines()
    updated_lines: list[str] = []
    in_app = False
    app_section_found = False
    app_key_written = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            if in_app and not app_key_written:
                updated_lines.append(f'app_key = "{app_key}"')
                app_key_written = True
            in_app = stripped == "[app]"
            app_section_found = app_section_found or in_app
            updated_lines.append(line)
            continue

        if in_app and stripped.startswith("app_key"):
            indent = line[: len(line) - len(line.lstrip())]
            updated_lines.append(f'{indent}app_key = "{app_key}"')
            app_key_written = True
            continue

        updated_lines.append(line)

    if not app_section_found:
        if updated_lines and updated_lines[-1].strip():
            updated_lines.append("")
        updated_lines.append("[app]")
        updated_lines.append(f'app_key = "{app_key}"')
    elif in_app and not app_key_written:
        updated_lines.append(f'app_key = "{app_key}"')

    config_file.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")


def _build_command_context(name: str) -> tuple[list[str], Path, dict[str, str] | None]:
    repo = _repo_path(name)
    if name == "cliproxyapi":
        go_exe = _find_go()
        if not go_exe:
            raise RuntimeError("未找到 go，可在设置中先安装 Go 或将 go.exe 加入 PATH")
        _ensure_cliproxyapi_runtime_config(repo)
        config_path = repo / "config.local.yaml"
        return [go_exe, "run", "./cmd/server", "-config", str(config_path)], repo, None

    if name == "cpa-codex-cleanup":
        env = os.environ.copy()
        env.update(
            {
                "CPA_MANAGEMENT_URL": _cliproxyapi_management_ui_url(),
                "CPA_MANAGEMENT_TOKEN": _get_setting("cliproxyapi_management_key", "cliproxyapi"),
                "CPA_WEB_HOST": "0.0.0.0",
                "CPA_WEB_PORT": "39023",
            }
        )
        return [
            sys.executable,
            "cpa_codex_cleanup_web.py",
            "--host",
            "0.0.0.0",
            "--port",
            "39023",
        ], repo, env

    if name == "resin":
        go_exe = _find_go()
        if not go_exe:
            raise RuntimeError("未找到 go，可在设置中先安装 Go 或将 go 加入 PATH")
        resin_data = repo / "data"
        state_dir = resin_data / "state"
        cache_dir = resin_data / "cache"
        log_dir = resin_data / "log"
        state_dir.mkdir(parents=True, exist_ok=True)
        cache_dir.mkdir(parents=True, exist_ok=True)
        log_dir.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env.update(
            {
                "RESIN_AUTH_VERSION": "V1",
                "RESIN_ADMIN_TOKEN": _get_setting("resin_admin_token", "resin-admin"),
                "RESIN_PROXY_TOKEN": _get_setting("resin_proxy_token", "resin-proxy"),
                "RESIN_LISTEN_ADDRESS": "0.0.0.0",
                "RESIN_PORT": "39024",
                "RESIN_STATE_DIR": str(state_dir),
                "RESIN_CACHE_DIR": str(cache_dir),
                "RESIN_LOG_DIR": str(log_dir),
            }
        )
        return [go_exe, "run", "./cmd/resin"], repo, env

    if name == "goproxy":
        go_exe = _find_go()
        if not go_exe:
            raise RuntimeError("未找到 go，可在设置中先安装 Go 或将 go 加入 PATH")
        data_dir = repo / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env.update(
            {
                "WEBUI_PASSWORD": _get_setting("goproxy_webui_password", "goproxy"),
                "WEBUI_PORT": "7778",
                "RANDOM_PORT": "7777",
                "STABLE_PORT": "7776",
                "SOCKS5_RANDOM_PORT": "7779",
                "SOCKS5_STABLE_PORT": "7780",
                "DATA_DIR": str(data_dir),
                "TZ": "Asia/Shanghai",
            }
        )
        return [go_exe, "run", "."], repo, env

    if name == "grok2api":
        _ensure_grok2api_runtime_config(repo)
        env_name = _ensure_grok2api_conda_env(repo)
        conda = _conda_exe()
        return [
            conda,
            "run",
            "--no-capture-output",
            "-n",
            env_name,
            "python",
            "-m",
            "granian",
            "--interface",
            "asgi",
            "--host",
            "127.0.0.1",
            "--port",
            "8011",
            "--workers",
            "1",
            "main:app",
        ], repo, None

    if name == "kiro-manager":
        exe = _resolve_kiro_exe()
        if exe:
            return [exe], repo, None
        cargo = shutil.which("cargo")
        if not cargo:
            raise RuntimeError("未找到 Kiro Account Manager 可执行文件，且系统未安装 Rust/Cargo，无法从源码启动")
        return ["npm", "run", "tauri", "dev"], repo, None

    raise KeyError(name)


def start(name: str) -> dict[str, Any]:
    with _LOCK:
        if name not in _SERVICE_META:
            raise KeyError(name)
        repo = _repo_path(name)
        if not repo.exists():
            raise RuntimeError(f"{_SERVICE_META[name]['label']} 未安装，请先在插件页点击“安装”")
        if _status_one(name)["running"]:
            return _status_one(name)

        log_file = _open_log(name)
        try:
            command, cwd, env = _build_command_context(name)
            proc = subprocess.Popen(
                command,
                cwd=str(cwd),
                stdout=log_file,
                stderr=subprocess.STDOUT,
                env=env,
                **_popen_kwargs(),
            )
            _PROCS[name] = proc
            _LAST_ERROR[name] = ""
        except Exception as e:
            _LAST_ERROR[name] = str(e)
            _close_log(name)
            raise

    if _SERVICE_META[name]["kind"] == "web":
        startup_timeout = int(_SERVICE_META[name].get("startup_timeout") or 90)
        for _ in range(startup_timeout):
            time.sleep(1)
            if _health_ok(name):
                return _status_one(name)
            proc = _PROCS.get(name)
            if proc and proc.poll() is not None:
                _LAST_ERROR[name] = f"启动失败，退出码={proc.returncode}"
                return _status_one(name)
        _LAST_ERROR[name] = "启动超时"
    else:
        time.sleep(2)
    return _status_one(name)


def stop(name: str) -> dict[str, Any]:
    with _LOCK:
        proc = _PROCS.get(name)
        port_pid = None
        desktop_pid = None
        if _SERVICE_META[name]["kind"] == "web":
            port_pid = _find_pid_by_port(int(_SERVICE_META[name].get("port") or 0))
        else:
            desktop_pid = _find_desktop_pid(name)
        if proc and proc.poll() is None:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=_creationflags(),
                )
            else:
                proc.terminate()
                try:
                    proc.wait(timeout=8)
                except Exception:
                    proc.kill()
        if port_pid and (not proc or port_pid != proc.pid):
            _terminate_pid(port_pid)
        if desktop_pid and (not proc or desktop_pid != proc.pid):
            _terminate_pid(desktop_pid)
        _PROCS.pop(name, None)
        _close_log(name)
    if _SERVICE_META[name]["kind"] == "web":
        for _ in range(10):
            if not _health_ok(name):
                break
            time.sleep(1)
    return _status_one(name)


def start_all() -> list[dict[str, Any]]:
    results = []
    for name in _SERVICE_META:
        try:
            if not _repo_path(name).exists():
                item = _status_one(name)
                item["last_error"] = "未安装；如需使用请先手动安装"
                results.append(item)
            else:
                results.append(start(name))
        except Exception:
            results.append(_status_one(name))
    return results


def stop_all() -> list[dict[str, Any]]:
    return [stop(name) for name in _SERVICE_META]
