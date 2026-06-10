"""NovelTrad v4 deterministic build entrypoint.

Subcommands (mutually exclusive; ``--all`` is a convenience):

* ``--wheel``     build sdist + wheel via ``python -m build`` (dist/wheel/)
* ``--exe``       build the standalone PyInstaller bundle (dist/NovelTrad/)
* ``--installer`` build the Inno Setup installer (Setup_NovelTrad-<ver>.exe)
* ``--all``       chain the three above

The version is read from ``src/__init__.__version__`` so the wheel, the
PyInstaller bundle (written to ``dist/NovelTrad/VERSION``) and the
Inno Setup installer all agree. ``build_script.py`` is kept as a thin
shim that forwards ``--all`` for backward compatibility.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"


def read_version() -> str:
    """Read the single source-of-truth version from ``src/__init__.py``.

    We import the module rather than grepping the file so the value is
    always the one that would actually be baked into the bundle.
    """
    sys.path.insert(0, str(ROOT))
    try:
        import src  # type: ignore[import-not-found]

        version = getattr(src, "__version__", None)
        if not version:
            raise RuntimeError("src.__version__ is not set")
        return str(version)
    finally:
        try:
            del sys.modules["src"]
        except KeyError:
            pass
        # Also clear cached submodule imports so a re-import picks up edits.
        for mod in list(sys.modules):
            if mod == "src" or mod.startswith("src."):
                sys.modules.pop(mod, None)


def _run(cmd: list[str], **kwargs) -> None:
    print("+", " ".join(cmd))
    subprocess.check_call(cmd, **kwargs)  # noqa: S603


def _clean(paths: list[Path]) -> None:
    for p in paths:
        if p.exists():
            print(f"clean {p}")
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()


def cmd_wheel(version: str) -> None:
    print(f"== wheel ({version}) ==")
    out = ROOT / "dist" / "wheel"
    out.mkdir(parents=True, exist_ok=True)
    # `python -m build` writes to ./dist by default; we copy what we
    # need into dist/wheel/ and keep the rest. We don't pass --outdir
    # so the user can also see a unified dist/ tree.
    _run([sys.executable, "-m", "build", "--wheel", "--sdist"])
    # Move artefacts into dist/wheel/ for clarity.
    for f in (ROOT / "dist").iterdir():
        if f.is_file() and (f.suffix in (".whl", ".tar.gz") or f.name.startswith("noveltrad")):
            shutil.move(str(f), str(out / f.name))
    print(f"wheel artefacts in {out}")


def cmd_exe(version: str) -> None:
    print(f"== exe ({version}) ==")
    _clean([ROOT / "build"])
    # Keep dist/NovelTrad/ between runs so a previous installer build
    # doesn't lose its source tree.
    _run([sys.executable, "-m", "PyInstaller", "build.spec", "--noconfirm"])
    # Write VERSION next to the executable so the updater can detect
    # the frozen build version without re-importing src.
    bundle = ROOT / "dist" / "NovelTrad"
    (bundle / "VERSION").write_text(version + "\n", encoding="utf-8")
    print(f"exe bundle in {bundle}")


def find_iscc() -> Path | None:
    candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
        Path("C:/Program Files (x86)/Inno Setup 6/ISCC.exe"),
        Path("C:/Program Files/Inno Setup 6/ISCC.exe"),
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def cmd_installer(version: str) -> None:
    print(f"== installer ({version}) ==")
    iscc = find_iscc()
    if iscc is None:
        raise SystemExit(
            "ISCC.exe not found. Install Inno Setup 6 or add it to PATH."
        )
    if not (ROOT / "dist" / "NovelTrad").exists():
        raise SystemExit(
            "dist/NovelTrad/ missing. Run `python build.py --exe` first."
        )
    env = os.environ.copy()
    env["NOVELTRAD_VERSION"] = version
    _run([str(iscc), "NovelTrad.iss"], env=env)
    print(f"installer built: Setup_NovelTrad-{version}.exe")


def cmd_all(version: str) -> None:
    cmd_wheel(version)
    cmd_exe(version)
    cmd_installer(version)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="NovelTrad v4 build helper")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--wheel", action="store_true", help="build sdist + wheel only")
    group.add_argument("--exe", action="store_true", help="build PyInstaller bundle only")
    group.add_argument("--installer", action="store_true", help="build Inno Setup installer only")
    group.add_argument("--all", action="store_true", help="chain wheel + exe + installer")
    parser.add_argument("--version", action="version", version=read_version())
    args = parser.parse_args(argv)

    version = read_version()
    print(f"NovelTrad build, version={version}")

    if args.wheel:
        cmd_wheel(version)
    elif args.exe:
        cmd_exe(version)
    elif args.installer:
        cmd_installer(version)
    elif args.all:
        cmd_all(version)
    return 0


if __name__ == "__main__":
    sys.exit(main())
