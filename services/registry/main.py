"""Deployable registry service entrypoint."""

import uvicorn

from cfi_registry import create_app

if __name__ == "__main__":
    uvicorn.run(create_app(), host="0.0.0.0", port=8000)
