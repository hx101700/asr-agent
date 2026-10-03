"""比较Python下载来源并持续转发安装进程的输出。"""

import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from http.client import HTTPException, HTTPResponse
from typing import TextIO, cast
from urllib.request import Request, urlopen

from .environment import Runtime, SetupError, child_environment


@dataclass(frozen=True)
class PythonIndex:
    """保存Python包索引及其wheel下载根地址。"""

    name: str
    index_url: str
    wheel_base_url: str


PIP_VERSION = "26.2.1"
PIP_WHEEL_PATH = (
    "packages/f3/6e/1736e5b4ae2b778ef2f81c47d797de9f891d4d8acb047a24ca37a60294dd/"
    "pip-26.2.1-py3-none-any.whl"
)
PIP_SHA256 = "71138adf1f4ca900cdb7d289c21b7494329f2332b6d85f0e1c42108c0384ed3e"
PYTHON_INDEXES = (
    PythonIndex("PyPI", "https://pypi.org/simple/", "https://files.pythonhosted.org/"),
    PythonIndex("Aliyun", "https://mirrors.aliyun.com/pypi/simple/", "https://mirrors.aliyun.com/pypi/"),
)
_SAMPLE_BYTES = 256 * 1024
_SAMPLE_SECONDS = 5.0
_SOCKET_TIMEOUT = 5.0


def _sample_python_index(index: PythonIndex) -> float:
    """读取锁定wheel的少量前缀并返回吞吐率，连接失败时返回负值。"""
    request = Request(index.wheel_base_url + PIP_WHEEL_PATH, headers={
        "Range": f"bytes=0-{_SAMPLE_BYTES - 1}", "Accept-Encoding": "identity",
    })
    started = time.perf_counter()
    received = 0
    try:
        with cast(HTTPResponse, urlopen(request, timeout=_SOCKET_TIMEOUT)) as response:
            while received < _SAMPLE_BYTES and time.perf_counter() - started < _SAMPLE_SECONDS:
                # read1只做一次底层读取，使慢速流能在每次收到数据后检查采样时间。
                chunk = response.read1(min(64 * 1024, _SAMPLE_BYTES - received))
                if not chunk:
                    break
                received += len(chunk)
    except (OSError, HTTPException):
        return -1.0
    return received / (time.perf_counter() - started)


def rank_python_indexes() -> list[PythonIndex]:
    """并行采样固定来源，按吞吐率排序并将失败来源留作最后候选。"""
    with ThreadPoolExecutor(max_workers=len(PYTHON_INDEXES)) as workers:
        speeds = list(workers.map(_sample_python_index, PYTHON_INDEXES))
    ranked = sorted(zip(speeds, PYTHON_INDEXES), key=lambda item: item[0], reverse=True)
    return [index for _, index in ranked]


def run_installer(runtime: Runtime, argv: list[str], log: TextIO) -> int:
    """执行安装命令，逐行保存并显示进度，结束或中断后回收子进程。"""
    try:
        process = subprocess.Popen(
            argv, cwd=runtime.workspace, env=child_environment(runtime),
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", bufsize=1, shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except OSError as exc:
        raise SetupError(f"无法启动子进程：{type(exc).__name__}") from exc
    output = cast(TextIO, process.stdout)
    try:
        for line in output:
            log.write(line)
            log.flush()
            sys.stderr.write(line)
            sys.stderr.flush()
        return process.wait()
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        output.close()
