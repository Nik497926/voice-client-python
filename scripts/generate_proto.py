#!/usr/bin/env python3
"""Generate protobuf/gRPC Python stubs into src/voice/client/_generated/."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROTO_DIR = ROOT / "protos"
OUT_DIR = ROOT / "src" / "voice" / "client" / "_generated"


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "__init__.py").write_text('"""Generated protobuf stubs. Do not edit by hand."""\n', encoding="utf-8")

    protos = ["common.proto", "bots.proto", "interactions.proto"]
    for name in protos:
        if not (PROTO_DIR / name).exists():
            print(f"missing proto: {PROTO_DIR / name}", file=sys.stderr)
            return 1

    cmd = [
        sys.executable,
        "-m",
        "grpc_tools.protoc",
        f"-I{PROTO_DIR}",
        f"--python_out={OUT_DIR}",
        f"--grpc_python_out={OUT_DIR}",
        *[str(PROTO_DIR / p) for p in protos],
    ]
    print(" ".join(cmd))
    subprocess.check_call(cmd)

    # Fix imports: generated files use `import common_pb2` etc.; rewrite to relative package imports.
    for path in OUT_DIR.glob("*_pb2*.py"):
        text = path.read_text(encoding="utf-8")
        text = text.replace("import common_pb2 as common__pb2", "from . import common_pb2 as common__pb2")
        text = text.replace("import bots_pb2 as bots__pb2", "from . import bots_pb2 as bots__pb2")
        text = text.replace("import interactions_pb2 as interactions__pb2", "from . import interactions_pb2 as interactions__pb2")
        text = text.replace("import common_pb2\n", "from . import common_pb2\n")
        text = text.replace("import bots_pb2\n", "from . import bots_pb2\n")
        text = text.replace("import interactions_pb2\n", "from . import interactions_pb2\n")
        path.write_text(text, encoding="utf-8")

    print(f"generated into {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
