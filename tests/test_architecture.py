"""验证分层依赖方向和模块迁移结果。"""

import ast
import unittest

from tests.support import ROOT


class ArchitectureTests(unittest.TestCase):
    def test_tools_do_not_depend_on_application_or_http(self):
        """验证工具层遵守单向依赖约定。"""
        for path in (ROOT / "src/asr_agent/tools").glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    self.assertFalse("application" in module.split(".") or "web" in module.split("."), str(path))
                elif isinstance(node, ast.Import):
                    self.assertTrue(all(not alias.name.startswith(("asr_agent.application", "asr_agent.web"))
                                        for alias in node.names), str(path))

    def test_old_flat_modules_are_not_kept_as_forwarding_entries(self):
        """验证迁移后的旧根模块已清除。"""
        root = ROOT / "src/asr_agent"
        for name in ("environment", "auth", "bailian", "media", "results", "documents",
                     "directory_picker", "_directory_dialog", "bootstrap", "probe",
                     "session", "transcription", "delivery", "validation"):
            self.assertFalse((root / f"{name}.py").exists(), name)
