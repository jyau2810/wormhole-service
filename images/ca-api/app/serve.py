from __future__ import annotations

import uvicorn

from .main import app, settings


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=settings.bind_port, log_config=None, access_log=False)
