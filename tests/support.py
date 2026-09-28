import tempfile
import unittest
from pathlib import Path

from asr_agent.environment import Project

ROOT = Path(__file__).resolve().parents[1]


class ProjectTestCase(unittest.TestCase):
    def setUp(self):
        temporary_root = ROOT / ".runtime/test-temp"
        temporary_root.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=temporary_root, prefix="case-")
        self.project = Project(Path(self.temporary.name))

    def tearDown(self):
        # 所有测试临时目录都在工作区；清理前复核最终绝对路径。
        if not self.project.root.resolve().is_relative_to(ROOT.resolve()):
            raise AssertionError("测试临时目录越过工作区边界")
        self.temporary.cleanup()
