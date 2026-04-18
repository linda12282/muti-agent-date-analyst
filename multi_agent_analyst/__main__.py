"""启动 Web：python -m multi_agent_analyst"""

from __future__ import annotations

import uvicorn

from .config import server_port


def main() -> None:
    uvicorn.run(
        "multi_agent_analyst.web_app:app",
        host="0.0.0.0",
        port=server_port(),
        reload=False,
    )


if __name__ == "__main__":
    main()
