"""Deployable registry service entrypoint."""

import os

import uvicorn

from cfi_core.tracing import configure_tracing
from cfi_registry import create_app
from cfi_registry.config import ServiceConfig, create_registry_store

configure_tracing("registry")

if __name__ == "__main__":
    config = ServiceConfig.from_env()
    store = create_registry_store(config)
    uvicorn.run(create_app(store), host=config.host, port=config.port)
