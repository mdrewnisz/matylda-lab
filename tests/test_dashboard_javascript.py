"""Browser-facing syntax checks for the generated Matylda Lab dashboard."""
from __future__ import annotations

import re
import shutil
import subprocess

import pytest

from matylda_lite.dashboard import build


def test_generated_inline_javascript_parses(tmp_path):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is not available for JavaScript syntax validation")

    scripts = re.findall(r"<script[^>]*>(.*?)</script>", build(server_mode=True), re.DOTALL)
    assert scripts, "dashboard did not contain an inline script"

    script_path = tmp_path / "dashboard.js"
    script_path.write_text(max(scripts, key=len), encoding="utf-8")
    result = subprocess.run(
        [node, "--check", str(script_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
