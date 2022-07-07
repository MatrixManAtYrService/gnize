from yaml import dump, load, BaseLoader, loader
from pathlib import Path
from textwrap import dedent
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json
import multihash
import json
from dacite import from_dict
import sqlite3
import sys


dir_path = Path.home() / ".gnize"
config_path = dir_path / "config.yaml"


@dataclass_json
@dataclass
class Editor:
    use: str
    mode: str


@dataclass_json
@dataclass
class CanvasSource:
    use: str
    path: str


@dataclass_json
@dataclass
class FingerprintStore:
    use: str
    connect: str


@dataclass_json
@dataclass
class Alternation:
    primary: str
    secondary: str


@dataclass_json
@dataclass
class Colors:
    gaps: Alternation
    signals: Alternation


@dataclass_json
@dataclass
class Runtime:
    debug_log: str
    debug_obj: str


@dataclass_json
@dataclass
class Config:
    editor: Editor
    canvasses: CanvasSource
    fingerprints: FingerprintStore
    colors: Colors
    runtime: Runtime


default_config = from_dict(
    data_class=Config,
    data={
        "editor": {"use": "prompttoolkit", "mode": "vi"},
        "canvasses": {"use": "filesystem", "path": str(dir_path / "canvasses")},
        "fingerprints": {
            "use": "sqlite3",
            "connect": str(dir_path / "fingerprints.db"),
        },
        "colors": {
            "gaps": {"primary": "#b58900", "secondary": "#cb4b16"},
            "signals": {"primary": "#2aa198", "secondary": "#7c81d4"},
        },
        "runtime": {
            "debug_log": "./.gnize.debug.log",
            "debug_obj": "./.gnize.debug.json",
        },
    },
)


def make_or_get():
    """
    If the user doesn't have a .gnize dir in their home directory, initialize it
    Otherwise just provide a config summary and return the contents of config.yaml
    """

    # ~/.gnize
    if not dir_path.exists():
        print(f"creating {dir_path}", file=sys.stderr)
        dir_path.mkdir(exist_ok=True, parents=True)
        print(f"{dir_path} exists", file=sys.stderr)

    # ~/.gnize/config.yaml
    try:
        with open(config_path, "w") as f:

            config_str = dump(json.loads(default_config.to_json()))

            # the json conversion above can be dispensed with, like so:
            # config_str = dump(default_config)

            #  but then you end up with yaml like this:
            #
            # !!python/object:gnize.dotdir.Config
            # canvasses: !!python/object:gnize.dotdir.CanvasSource
            #   path: /home/matt/.gnize/canvasses
            #  use: filesystem

            f.write(config_str)
        print(f"{config_path} already exists", file=sys.stderr)
        config = default_config

    except FileNotFoundError:
        with open(config_path, "r") as f:
            config_str = f.read()
        print("wrote {config_path}", file=sys.stderr)
        config = load(config_str, Loader=BaseLoader)

    # canvasses
    if config.canvasses.use == "filesystem":
        canvas_dir = Path(config.canvasses.path)
        canvas_dir.mkdir(parents=True, exist_ok=True)
        count = 0
        for child in canvas_dir.glob("*"):
            if multihash.is_valid(str(child)):
                count += 1
        print(f"{count} canvasses found in f{canvas_dir}", file=sys.stderr)

    # fingerprints database
    if config.fingerprints.use == "sqlite3":
        conn = sqlite3.connect(config.fingerprints.connect)
        cursor = conn.cursor()
        cursor.execute(
            dedent(
                """
                CREATE TABLE IF NOT EXISTS prints (
                    channel INTEGER NOT NULL,
                    fingerprint INTEGER NOT NULL,
                    repeat_num INTEGER NOT NULL DEFAULT 0,
                    canvas_hash TEXT NOT NULL,
                    canvas sub INTEGER NOT NULL,
                    sub_idx INTEGER NOT NULL,
                    len INTEGER NOT NULL,
                    PRIMARY KEY (channel, fingerprint, repeat_num)
                );
                """
            )
        )
        cursor.execute("SELECT count(*) from prints;")
        count = cursor.fetchone()[0]
        cursor.execute("SELECT count(distinct canvas_hash) from prints;")
        count = cursor.fetchone()[0]
        print(f"{count} fingerprints cognized so far", file=sys.stderr)

    return config
