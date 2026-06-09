import json
import tempfile
import yaml
from datetime import date
from pathlib import Path

from pmao.models import Initiative
from pmao.vault import init_vault, load_initiatives, save_initiatives, VAULT_FILES


def _make_initiative(id_="init-001", name="Customer Data Platform"):
    return Initiative(
        id=id_, name=name, status="not_started",
        created=date(2026, 6, 8), last_touched=date(2026, 6, 8)
    )


def test_init_vault_creates_expected_files():
    with tempfile.TemporaryDirectory() as tmp:
        vault = Path(tmp)
        init_vault(vault)
        for fname in VAULT_FILES:
            assert (vault / fname).exists(), f"Missing {fname}"
        assert (vault / "workbook.xlsx").exists()
        assert (vault / "transcripts").is_dir()
        assert (vault / "hypotheses.json").exists()


def test_init_vault_writes_config_with_project_name():
    with tempfile.TemporaryDirectory() as tmp:
        vault = Path(tmp)
        init_vault(vault, project_name="Acme LRP", owner="J. Smith")
        cfg = yaml.safe_load((vault / "project-config.yaml").read_text())
        assert cfg["project_name"] == "Acme LRP"
        assert cfg["owner"] == "J. Smith"


def test_init_vault_creates_empty_initiatives():
    with tempfile.TemporaryDirectory() as tmp:
        vault = Path(tmp)
        init_vault(vault)
        data = json.loads((vault / "initiatives.json").read_text())
        assert data == []


def test_save_and_load_round_trip():
    with tempfile.TemporaryDirectory() as tmp:
        vault = Path(tmp)
        init_vault(vault)
        initiative = _make_initiative()
        save_initiatives(vault, [initiative])
        loaded = load_initiatives(vault)
        assert len(loaded) == 1
        assert loaded[0].id == "init-001"
        assert loaded[0].name == "Customer Data Platform"


def test_save_creates_backup():
    with tempfile.TemporaryDirectory() as tmp:
        vault = Path(tmp)
        init_vault(vault)
        save_initiatives(vault, [_make_initiative()])
        save_initiatives(vault, [_make_initiative("init-002", "Second")])
        assert (vault / "initiatives.json.bak").exists()


def test_no_lrp_in_config():
    with tempfile.TemporaryDirectory() as tmp:
        vault = Path(tmp)
        init_vault(vault)
        config_text = (vault / "project-config.yaml").read_text()
        assert "lrp" not in config_text.lower()
        assert "vault_type" not in config_text


def test_init_vault_creates_hypotheses_json():
    with tempfile.TemporaryDirectory() as tmp:
        vault = Path(tmp)
        init_vault(vault)
        hyp_path = vault / "hypotheses.json"
        assert hyp_path.exists()
        assert json.loads(hyp_path.read_text()) == []
