import json
import shutil
from pathlib import Path
from typing import List
import yaml

from pmao.models import Initiative

VAULT_FILES = [
    "project-config.yaml",
    "initiatives.json",
    "actions.json",
    "questions.json",
    "decisions.json",
    "workbook.xlsx",
]


def init_vault(vault_path: Path, project_name: str = "My Project", owner: str = "") -> None:
    vault_path.mkdir(parents=True, exist_ok=True)
    (vault_path / "transcripts").mkdir(exist_ok=True)

    config = {
        "project_name": project_name,
        "owner": owner,
        "llm_backend": None,
        "llm_timeout_seconds": 120,
    }
    (vault_path / "project-config.yaml").write_text(yaml.dump(config, default_flow_style=False))

    (vault_path / "initiatives.json").write_text("[]")
    (vault_path / "actions.json").write_text("[]")
    (vault_path / "questions.json").write_text("[]")
    (vault_path / "decisions.json").write_text("[]")

    from pmao.excel import create_workbook
    create_workbook(vault_path / "workbook.xlsx", [])


def load_initiatives(vault_path: Path) -> List[Initiative]:
    data = json.loads((vault_path / "initiatives.json").read_text())
    return [Initiative.from_dict(d) for d in data]


def save_initiatives(vault_path: Path, initiatives: List[Initiative]) -> None:
    target = vault_path / "initiatives.json"
    if target.exists():
        shutil.copy2(target, vault_path / "initiatives.json.bak")
    data = [i.to_dict() for i in initiatives]
    target.write_text(json.dumps(data, indent=2, default=str))


def seed_from_csv(vault_path: Path, csv_path: Path) -> int:
    import csv
    from datetime import date

    initiatives = []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            initiatives.append(Initiative(
                id=row.get("id") or f"init-{i + 1:03d}",
                name=row["name"],
                status="not_started",
                created=date.today(),
                last_touched=date.today(),
                coordination_owner=row.get("coordination_owner") or None,
                responsible_owner=row.get("responsible_owner") or None,
                priority=row.get("priority") or None,
            ))
    save_initiatives(vault_path, initiatives)
    return len(initiatives)
