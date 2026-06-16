from __future__ import annotations

from .client import MercurioClient
from .models import SysmlReleaseInfo, VersionInfo
from .process import BackendProcess, launch_backend
from .project import MercurioProject


class Mercurio:
    """High-level entrypoint for connecting to or launching Mercurio."""

    SUPPORTED_API_VERSION = 1

    def __init__(
        self,
        client: MercurioClient,
        *,
        process: BackendProcess | None = None,
    ):
        self.client = client
        self.process = process

    @classmethod
    def connect(cls, url: str, *, timeout: float = 30.0) -> "Mercurio":
        backend = cls(MercurioClient(url, timeout=timeout))
        backend.ensure_compatible()
        return backend

    @classmethod
    def launch(
        cls,
        *,
        executable: str | None = None,
        workspace: str | None = None,
        host: str = "127.0.0.1",
        port: int = 0,
        timeout: float = 30.0,
    ) -> "Mercurio":
        process = launch_backend(
            executable=executable,
            workspace=workspace,
            host=host,
            port=port,
            timeout=timeout,
        )
        backend = cls(MercurioClient(process.url, timeout=timeout), process=process)
        backend.ensure_compatible()
        return backend

    def ensure_compatible(self) -> VersionInfo:
        version = self.client.version()
        if version.api_version != self.SUPPORTED_API_VERSION:
            raise RuntimeError(
                "Unsupported Mercurio API version "
                f"{version.api_version}; expected {self.SUPPORTED_API_VERSION}."
            )
        return version

    def health(self) -> dict:
        return self.client.health()

    def version(self) -> VersionInfo:
        return self.client.version()

    def list_sysml_releases(self) -> list[SysmlReleaseInfo]:
        return self.client.list_sysml_releases()

    def resolve_sysml_release(self, selector: str) -> SysmlReleaseInfo:
        return self.client.resolve_sysml_release(selector)

    def open_project(self, path: str, *, mode: str = "lazy") -> MercurioProject:
        return MercurioProject(self.client, self.client.open_project(path, mode=mode))

    def open_workspace(self, path: str, *, mode: str = "lazy") -> MercurioProject:
        return self.open_project(path, mode=mode)

    def close(self) -> None:
        if self.process is not None:
            self.process.close()

    def __enter__(self) -> "Mercurio":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
