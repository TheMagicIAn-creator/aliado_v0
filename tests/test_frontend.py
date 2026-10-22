"""Regressao de concorrencia da interface com Node nativo, sem navegador ou rede."""

import shutil
import subprocess
from pathlib import Path

import pytest


def test_attachment_and_question_share_the_conversation():
    """INT-01: criacao compartilhada, navegacao, fixados e nova tentativa apos falha."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node necessario para executar a regressao de concorrencia da interface.")
    script = Path(__file__).parent / "js" / "conversation_start.cjs"
    result = subprocess.run([node, str(script)], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
