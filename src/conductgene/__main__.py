"""Module entry: uv run conductgene-serve"""

from __future__ import annotations

import uvicorn

from conductgene.config import Settings


def serve() -> None:
    s = Settings()
    s.resolve_paths()
    uvicorn.run(
        "conductgene.api.app:app",
        host=s.host,
        port=s.port,
        reload=False,
    )


if __name__ == "__main__":
    serve()
