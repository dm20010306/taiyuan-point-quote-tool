from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.path_resolver import get_paths, normalize_relative_path


class LocalPathTests(unittest.TestCase):
    def test_windows_uses_data_under_the_movable_tool_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary).resolve()
            first = workspace / "D-drive" / "智能图纸报价工具"
            (first / "backend").mkdir(parents=True)
            (first / "backend" / "app.py").touch()
            module = first / "backend" / "path_resolver.py"
            original = get_paths(module, {"POINT_QUOTE_DATA_DIR": "/stale/machine/path"}, platform_name="nt")
            self.assertTrue(original.local_data_mode)
            self.assertEqual(original.knowledge_root, first / "data")
            self.assertEqual(original.resolve_product_path(r"中控\ABB.md"), first / "data" / "01_产品库" / "中控" / "ABB.md")
            self.assertEqual(original.data_root, first / "data")
            self.assertEqual(original.uploads_root, first / "data" / "uploads")

            second = workspace / "E-drive" / "moved package"
            second.parent.mkdir()
            first.rename(second)
            moved = get_paths(second / "backend" / "path_resolver.py", platform_name="nt")
            self.assertEqual(moved.app_root, second)
            self.assertEqual(moved.data_root, second / "data")
            self.assertEqual(moved.resolve_project_path("测试.md"), second / "data" / "06_客户档案" / "智能图纸与报价" / "测试.md")
            self.assertEqual(moved.to_relative_data_path(second / "data" / "09_附件" / "图片.png"), "09_附件/图片.png")

    def test_business_paths_cannot_depend_on_a_machine_or_escape_data(self) -> None:
        for value in (r"C:\data\product.md", r"\\server\share\product.md", "/Volumes/NAS/product.md", "../outside.md", "a/../outside.md"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_relative_path(value)
        self.assertEqual(normalize_relative_path(r"09_附件\产品图片\ABB.png"), "09_附件/产品图片/ABB.png")

    def test_every_platform_ignores_legacy_external_data_redirects(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            module = root / "project" / "backend" / "app.py"
            module.parent.mkdir(parents=True)
            module.touch()
            data = root / "isolated" / "data"
            paths = get_paths(module, {"POINT_QUOTE_DATA_DIR": str(data), "POINT_QUOTE_VAULT_ROOT": str(root / "network")}, platform_name="posix")
            self.assertTrue(paths.local_data_mode)
            self.assertEqual(paths.app_root, root / "project")
            self.assertEqual(paths.knowledge_root, root / "project" / "data")
            self.assertFalse(str(paths.knowledge_root).startswith(str(root / "isolated")))
            self.assertFalse(str(paths.knowledge_root).startswith(str(root / "network")))


if __name__ == "__main__":
    unittest.main()
