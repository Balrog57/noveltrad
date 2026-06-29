"""``project`` subcommand: list / create / activate / rename / inspect / delete / clean projects.

The eight actions share one client and the same routing pattern. Each
``if args.action == "..."`` branch is short and self-contained.
"""
from __future__ import annotations

import json
from argparse import ArgumentParser

from ..cli_client import get_client


def add_arguments(sub: ArgumentParser) -> None:
    sub.add_help = True
    pa = sub.add_subparsers(dest="action", required=True)
    pa.add_parser("list", help="List all projects")
    pcr = pa.add_parser("create", help="Create a new project")
    pcr.add_argument("name")
    pcr.add_argument("--dir", required=True, help="Working directory")
    pa.add_parser("active", help="Show active project")
    pa_act = pa.add_parser("activate", help="Set active project")
    pa_act.add_argument("project_id")
    pi = pa.add_parser("inspect", help="Show project details")
    pi.add_argument("project_id")
    prn = pa.add_parser("rename", help="Rename a project")
    prn.add_argument("project_id")
    prn.add_argument("new_name")
    pd = pa.add_parser("delete", help="Delete a project")
    pd.add_argument("project_id")
    pc = pa.add_parser("clean", help="Clean project data files")
    pc.add_argument("project_id")


def run(args) -> int:
    client = get_client(args)

    if args.action == "list":
        data = client.get("/projects").json()
        projects = data.get("projects", [])
        if not projects:
            print("[project] No projects found.")
            return 0
        print(f"{'ID':<14} {'Name':<30} {'Folder':<50}")
        print("-" * 95)
        for p in projects:
            sid = p.get("project_id", "")[:12]
            name = p.get("name", f"Project-{sid}")
            folder = p.get("project_dir", "")
            print(f"{sid:<14} {name:<30} {folder:<50}")
        return 0

    if args.action == "create":
        name = args.name
        folder = args.dir
        res = client.post("/projects", json={"name": name, "project_dir": folder})
        data = res.json()
        pid = data.get("project_id", "?")
        print(f"[project] Created: {pid} ({name} -> {folder})")
        return 0

    if args.action == "active":
        data = client.get("/projects/active").json()
        proj = data.get("project")
        if proj:
            print(f"Active: {proj.get('name','?')} ({proj.get('project_id','?')})")
            print(f"  Folder: {proj.get('project_dir','?')}")
        else:
            print("No active project.")
        return 0

    if args.action == "activate":
        pid = args.project_id
        res = client.post(f"/projects/{pid}/activate")
        data = res.json()
        proj = data.get("project", {})
        print(f"[project] Activated: {proj.get('name', pid)}")
        return 0

    if args.action == "rename":
        pid = args.project_id
        new_name = args.new_name
        client.put(f"/projects/{pid}", json={"name": new_name})
        print(f"[project] Renamed {pid} -> {new_name}")
        return 0

    if args.action == "inspect":
        pid = args.project_id
        try:
            data = client.get(f"/projects/{pid}").json()
            print(json.dumps(data, indent=2, default=str))
        except Exception:
            print(f"Project {pid} not found")
            return 1
        return 0

    if args.action == "delete":
        pid = args.project_id
        try:
            client.delete(f"/projects/{pid}")
            print(f"[project] Deleted {pid}")
        except Exception as e:
            print(f"ERROR: {e}")
            return 1
        return 0

    if args.action == "clean":
        pid = args.project_id
        try:
            client.delete(f"/projects/{pid}/local-data")
            print(f"[project] Cleaned {pid}")
        except Exception as e:
            print(f"ERROR: {e}")
            return 1
        return 0

    return 0
