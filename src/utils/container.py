"""Detect whether NovelTrad is running inside a container.

Native installs can open folders with the host file explorer. Docker/CasaOS
cannot: ``xdg-open`` inside the container never reaches the user's desktop, and
paths like ``/app/translated_files`` are volume mounts, not a Windows folder.
"""
from pathlib import Path


def running_in_container() -> bool:
    """Return True when this process is inside Docker/Podman/OCI."""
    if Path("/.dockerenv").is_file():
        return True
    try:
        cgroup = Path("/proc/1/cgroup").read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    return "docker" in cgroup or "containerd" in cgroup or "kubepods" in cgroup
