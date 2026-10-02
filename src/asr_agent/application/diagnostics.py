"""检查本机运行环境与项目依赖。"""

import sys

from .. import BAILIAN_VERSION
from ..tools.bailian import installed_bl_version, verify_bl_installation
from ..tools.environment import (
    Project, SetupError, check_node, check_python, installed_python_versions,
    locked_python_versions,
)


def doctor(project: Project) -> dict:
    """检查本机运行时及项目依赖，返回环境诊断报告。"""
    report = {
        "platform": sys.platform,
        "python": sys.version.split()[0],
        "project": str(project.root),
        "issues": [],
    }
    try:
        check_python()
    except SetupError as exc:
        report["issues"].append(str(exc))
    try:
        node, version = check_node(project)
        report["node"] = {"path": str(node), "version": version}
    except SetupError as exc:
        report["issues"].append(str(exc))
    try:
        version = installed_bl_version(project)
        report["bailian"] = {"version": version, "expected": BAILIAN_VERSION, "entry": str(project.bl_entry)}
        if version != BAILIAN_VERSION or not project.bl_entry.is_file():
            report["issues"].append("项目内BL尚未安装或版本不匹配。")
        else:
            verify_bl_installation(project)
    except SetupError as exc:
        report["issues"].append(str(exc))
    venv_python = project.path(".venv/Scripts/python.exe")
    report["venv_python"] = str(venv_python) if venv_python.is_file() else None
    if not venv_python.is_file():
        report["issues"].append("项目虚拟环境尚未创建或不完整。")
    else:
        try:
            expected = locked_python_versions(project)
            installed = installed_python_versions(project, expected)
            if installed is None:
                report["issues"].append("Python运行依赖缺失或无法加载，请运行bootstrap。")
            else:
                report["python_packages"] = installed
                for name, version in expected.items():
                    if installed[name] != version:
                        report["issues"].append(f"Python依赖{name}版本不匹配：需要{version}，实际{installed[name]}。")
        except SetupError as exc:
            report["issues"].append(str(exc))
    report["note"] = "仅检查本地环境；不读取凭据，不验证账号权限，不执行转写。"
    return report
