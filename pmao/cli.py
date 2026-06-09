import argparse
from pathlib import Path


def cmd_init(args) -> None:
    project_name = input("Project name: ").strip() or "My Project"
    owner = input("Primary owner/project manager: ").strip()

    from pmao.vault import init_vault
    vault = Path(args.vault)
    init_vault(vault, project_name=project_name, owner=owner)
    print(f"Vault created: {vault.resolve()}")
    print(f"  project-config.yaml — project settings")
    print(f"  initiatives.json    — empty (add initiatives via --roster or pmao update)")
    print(f"  workbook.xlsx       — blank workbook ready")

    if args.roster:
        _seed_from_csv(vault, Path(args.roster))


def _seed_from_csv(vault_path: Path, csv_path: Path) -> None:
    import csv
    from datetime import date
    from pmao.models import Initiative
    from pmao.vault import save_initiatives

    initiatives = []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            initiatives.append(Initiative(
                id=row.get("id", f"init-{i + 1:03d}"),
                name=row["name"],
                status="not_started",
                created=date.today(),
                last_touched=date.today(),
                coordination_owner=row.get("coordination_owner") or None,
                responsible_owner=row.get("responsible_owner") or None,
                priority=row.get("priority") or None,
            ))
    save_initiatives(vault_path, initiatives)
    print(f"  Seeded {len(initiatives)} initiatives from {csv_path.name}")


def cmd_ingest(args) -> None:
    from pmao.ingest import run_ingest
    run_ingest(
        vault_path=Path(args.vault),
        source_path=Path(args.source),
        yes=args.yes,
        config_override=getattr(args, "backend", None),
    )


def cmd_update(args) -> None:
    from pmao.vault import load_initiatives
    from pmao.llm import call_text
    from pmao.ingest import _load_skill

    vault = Path(args.vault)
    initiatives = load_initiatives(vault)
    skill = _load_skill("update")
    init_list = "\n".join(f"  {i.id}: {i.name} ({i.status})" for i in initiatives)
    prompt = skill.replace("{initiatives}", init_list)
    result = call_text(prompt, config_override=getattr(args, "backend", None))
    print(result)


def cmd_status(args) -> None:
    from pmao.vault import load_initiatives
    from pmao.llm import call_text
    from pmao.ingest import _load_skill

    vault = Path(args.vault)
    initiatives = load_initiatives(vault)
    skill = _load_skill("status")
    init_list = "\n".join(
        f"  {i.id}: {i.name} | {i.status} | priority={i.priority or 'none'} | "
        f"current_state={i.current_state or 'none'} | "
        f"coordination_next_steps={i.coordination_next_steps or 'none'} | "
        f"outstanding_questions={i.outstanding_questions or 'none'} | "
        f"outstanding_meetings={i.outstanding_meetings or 'none'} | "
        f"last_touch={i.last_touch_timestamp or 'none'}"
        for i in initiatives
    )
    prompt = skill.replace("{initiatives}", init_list)
    result = call_text(prompt, config_override=getattr(args, "backend", None))
    print(result)


def cmd_summarize(args) -> None:
    import json
    from pmao.vault import load_initiatives
    from pmao.llm import call_text
    from pmao.ingest import _load_skill

    vault = Path(args.vault)
    initiatives = load_initiatives(vault)
    skill = _load_skill("summarize")
    state = json.dumps([i.to_dict() for i in initiatives], indent=2, default=str)
    prompt = skill.replace("{project_state}", state)
    result = call_text(prompt, config_override=getattr(args, "backend", None))
    print(result)


def cmd_export(args) -> None:
    from pmao.vault import load_initiatives
    from pmao.excel import create_workbook

    vault = Path(args.vault)
    initiatives = load_initiatives(vault)
    out_path = vault / "workbook.xlsx"
    create_workbook(out_path, initiatives)
    print(f"Exported {len(initiatives)} initiatives to {out_path.resolve()}")


def cmd_config(args) -> None:
    vault = Path(args.vault)
    config_path = vault / "project-config.yaml"
    if not config_path.exists():
        print(f"No project-config.yaml found in {vault}")
        return
    print(config_path.read_text())


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="pmao",
        description="Project management assistant orchestrator",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Initialize a vault")
    p_init.add_argument("vault", help="Path to vault directory")
    p_init.add_argument("--roster", metavar="FILE", help="Seed initiative list from CSV")
    p_init.set_defaults(func=cmd_init)

    p_ingest = sub.add_parser("ingest", help="Ingest source material and extract updates")
    p_ingest.add_argument("vault", help="Path to vault directory")
    p_ingest.add_argument("--source", required=True, metavar="FILE",
                          help=".vtt, .txt, or .md source file")
    p_ingest.add_argument("--yes", action="store_true", help="Apply without confirmation prompt")
    p_ingest.add_argument("--backend", choices=["claude", "codex"], default=None)
    p_ingest.set_defaults(func=cmd_ingest)

    p_update = sub.add_parser("update", help="Manually update an initiative field")
    p_update.add_argument("vault", help="Path to vault directory")
    p_update.add_argument("--backend", choices=["claude", "codex"], default=None)
    p_update.set_defaults(func=cmd_update)

    p_status = sub.add_parser("status", help="Print status dashboard")
    p_status.add_argument("vault", help="Path to vault directory")
    p_status.add_argument("--backend", choices=["claude", "codex"], default=None)
    p_status.set_defaults(func=cmd_status)

    p_summarize = sub.add_parser("summarize", help="Produce executive summary")
    p_summarize.add_argument("vault", help="Path to vault directory")
    p_summarize.add_argument("--backend", choices=["claude", "codex"], default=None)
    p_summarize.set_defaults(func=cmd_summarize)

    p_export = sub.add_parser("export", help="Regenerate workbook.xlsx from project state")
    p_export.add_argument("vault", help="Path to vault directory")
    p_export.set_defaults(func=cmd_export)

    p_config = sub.add_parser("config", help="View project configuration")
    p_config.add_argument("vault", help="Path to vault directory")
    p_config.set_defaults(func=cmd_config)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
