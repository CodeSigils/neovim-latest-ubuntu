"""Shared release-metadata schema, validation, and hashing helpers."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

ARTIFACTS = {
    "amd64": "nvim-linux-x86_64.deb",
    "arm64": "nvim-linux-arm64.deb",
}
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
IMAGE_DIGEST = re.compile(r"^[0-9a-f]{64}$")
STABLE_VERSION = re.compile(r"^[0-9]+[.][0-9]+[.][0-9]+$")


@dataclass(frozen=True)
class BuildInputs:
    source_version: str
    source_commit: str
    package_version: str
    repository_commit: str
    ubuntu_version: str
    ubuntu_codename: str
    ubuntu_image_digest: str

    @property
    def upstream_ref(self) -> str:
        if self.source_version == "nightly":
            return "refs/heads/master"
        return f"refs/tags/v{self.source_version}"

    def validation_errors(self, *, allow_nightly: bool) -> list[str]:
        errors: list[str] = []
        stable = STABLE_VERSION.fullmatch(self.source_version)
        if not stable and not (allow_nightly and self.source_version == "nightly"):
            errors.append("source version must be a stable X.Y.Z version")
        if not self.package_version:
            errors.append("package version must not be empty")
        if not FULL_SHA.fullmatch(self.source_commit):
            errors.append("source commit must be a full lowercase Git SHA")
        if not FULL_SHA.fullmatch(self.repository_commit):
            errors.append("repository commit must be a full lowercase Git SHA")
        if not IMAGE_DIGEST.fullmatch(self.ubuntu_image_digest):
            errors.append("Ubuntu image digest must contain 64 lowercase hex characters")
        if not self.ubuntu_version or not self.ubuntu_codename:
            errors.append("Ubuntu version and codename must not be empty")
        return errors


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_metadata(inputs: BuildInputs, artifact: Path, architecture: str) -> dict:
    return {
        "artifact": {
            "architecture": architecture,
            "name": artifact.name,
            "sha256": file_sha256(artifact),
        },
        "build_environment": {
            "ubuntu_codename": inputs.ubuntu_codename,
            "ubuntu_image_digest": f"sha256:{inputs.ubuntu_image_digest}",
            "ubuntu_version": inputs.ubuntu_version,
        },
        "package_version": inputs.package_version,
        "packaging_repository_commit": inputs.repository_commit,
        "schema_version": 1,
        "upstream": {
            "commit": inputs.source_commit,
            "ref": inputs.upstream_ref,
            "repository": "https://github.com/neovim/neovim",
        },
    }
