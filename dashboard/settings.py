from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "dashboard.yaml"


@dataclass(frozen=True)
class TeamOutput:
    name: str
    owner: str
    file: Path
    produced_by: str


@dataclass(frozen=True)
class Settings:
    raw_dir: Path
    register: Path
    progress_history: Path
    portfolio_dir: Path
    priority_runs: dict
    team_outputs: dict = field(default_factory=dict)

    def priority_dir(self, method, dataset):
        return self.priority_runs[method][dataset]


def resolve(path, root):
    path = Path(path)
    return path if path.is_absolute() else root / path


def load_settings(path=CONFIG_PATH, root=ROOT):
    with open(path, encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    runs = {
        method: {dataset: resolve(folder, root) for dataset, folder in datasets.items()}
        for method, datasets in config["priority_runs"].items()
    }
    team_outputs = {
        name: TeamOutput(name, item["owner"], resolve(item["file"], root), item["produced_by"])
        for name, item in config.get("team_outputs", {}).items()
    }
    return Settings(
        raw_dir=resolve(config["raw_dir"], root),
        register=resolve(config["register"], root),
        progress_history=resolve(config["progress_history"], root),
        portfolio_dir=resolve(config["portfolio_dir"], root),
        priority_runs=runs,
        team_outputs=team_outputs,
    )
