from __future__ import annotations

import json

from content_runner import generate_plan

if __name__ == "__main__":
    print(json.dumps(generate_plan(), ensure_ascii=False, indent=2))
