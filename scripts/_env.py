"""
.env 自动加载（import 即生效，无需 export）。

从本文件位置向上逐级查找最近的 .env，把 KEY=VALUE 注入 os.environ。
已存在的环境变量不会被覆盖（外部 export 优先）。所有脚本通过 `import _env`
在导入时即完成加载——与同事的 adgine-geo-skills 约定一致。
"""

from __future__ import annotations

import os
from pathlib import Path


def load_dotenv() -> Path | None:
    here = Path(__file__).resolve()
    for d in (here.parent, *here.parents):
        env = d / ".env"
        if env.is_file():
            for raw in env.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key:
                    os.environ.setdefault(key, val)
            return env
    return None


# import 时自动加载
ENV_PATH = load_dotenv()
