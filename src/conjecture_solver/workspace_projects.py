"""Optional local spaces and conversation collections; no implicit global selection.

The historical ``Workspace.projects`` API still denotes conversations. New
collections group those records without moving their files or study receipts.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import shutil
import time
import uuid
from pathlib import Path

from .research_service import put

DEFAULT_SPACE = "personal"
MAX_CONTEXT_BYTES = 512 * 1024**2


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,100}", value):
        raise ValueError("Supply a valid workspace or project ID")
    return value


def read(path):
    if path.is_symlink():
        raise ValueError("Linked metadata is not supported")
    return json.loads(path.read_text()) if path.exists() else {}


def fields(payload):
    result = {}
    for key, limit in (("name", 160), ("description", 2000), ("instructions", 20000)):
        if key in payload:
            value = payload[key]
            if not isinstance(value, str) or len(value) > limit:
                raise ValueError(f"{key} must be text of at most {limit} characters")
            result[key] = value.strip()
    if "name" in result and not result["name"]:
        raise ValueError("A name is required")
    return result


class WorkspaceDirectory:
    """Resolve one explicit local space. These are not OS security boundaries."""

    def __init__(self, runs_root):
        self.root = Path(runs_root).expanduser().resolve()
        self._opened = {}

    def path(self, space=DEFAULT_SPACE):
        identifier(space)
        if space == DEFAULT_SPACE:
            return self.root
        parent = self.root / "workspaces"
        path = parent / space
        if parent.is_symlink() or path.is_symlink() or not (path / "space.json").is_file():
            raise ValueError("Unknown workspace")
        record = read(path / "space.json")
        if record.get("id") != space:
            raise ValueError("Workspace metadata does not match its ID")
        return path

    def open(self, space=DEFAULT_SPACE):
        from .web.workspace import Workspace

        path = self.path(space) / ".workspace"
        if space not in self._opened:
            self._opened[space] = Workspace(path)
        return self._opened[space]

    def list(self):
        rows = [{"id": DEFAULT_SPACE, "name": "Personal", "path": str(self.root)}]
        for path in sorted((self.root / "workspaces").glob("*/space.json")):
            self.path(path.parent.name)
            rows.append(read(path) | {"path": str(path.parent)})
        return rows

    def create(self, payload):
        values = fields(payload)
        if not values.get("name"):
            raise ValueError("A workspace name is required")
        space = identifier(payload.get("id") or "space-" + uuid.uuid4().hex[:12])
        if space == DEFAULT_SPACE:
            raise ValueError("The personal workspace already exists")
        parent = self.root / "workspaces"
        if parent.is_symlink():
            raise ValueError("Linked workspace storage is not supported")
        path = parent / space
        path.mkdir(parents=True, mode=0o700)
        record = {"schema_version": 1, "id": space, **values, "created_at": time.time()}
        put(path / "space.json", record)
        return record | {"path": str(path)}

    def all(self):
        return [self.open(row["id"]) for row in self.list()]


class ProjectCollections:
    """Mixin for the existing local workspace; methods shared by CLI and HTTP."""

    @property
    def collections_root(self):
        return self.root / "collections"

    def collection_path(self, key):
        path = self.collections_root / identifier(key)
        if self.collections_root.is_symlink() or path.is_symlink():
            raise ValueError("Linked project storage is not supported")
        if not (path / "collection.json").is_file():
            raise ValueError("Unknown project collection")
        return path

    def collections(self):
        return [
            self.collection(p.parent.name)
            for p in sorted(self.collections_root.glob("*/collection.json"))
        ]

    def collection(self, key):
        path = self.collection_path(key)
        record = read(path / "collection.json")
        if record.get("id") != key:
            raise ValueError("Project metadata does not match its ID")
        try:
            files, context_error = self.context_files(path / "files"), None
        except ValueError as error:
            files, context_error = [], str(error)
        return record | {
            "path": str(path),
            "files": files,
            "context_error": context_error,
            "conversations": [p["id"] for p in self.projects() if p.get("collection") == key],
        }

    def save_collection(self, payload):
        values = fields(payload)
        with self.lock():
            if payload.get("id"):
                path = self.collection_path(payload["id"])
                record = read(path / "collection.json")
            else:
                if not values.get("name"):
                    raise ValueError("A project name is required")
                key = "project-" + uuid.uuid4().hex[:12]
                path = self.collections_root / key
                if self.collections_root.is_symlink():
                    raise ValueError("Linked project storage is not supported")
                (path / "files").mkdir(parents=True, mode=0o700)
                record = {"schema_version": 1, "id": key, "created_at": time.time()}
            record.update(values, updated_at=time.time())
            put(path / "collection.json", record)
        return self.collection(record["id"])

    def assign_collection(self, conversation, collection):
        # Assignment affects future context only; old receipts and paths stay intact.
        with self.lock():
            path = self.directory(conversation)
            if self.project(conversation)["running"]:
                raise ValueError("Wait for the active conversation turn before moving it")
            if collection:
                self.collection_path(collection)
            elif collection not in (None, ""):
                raise ValueError("Supply a project ID or null")
            record = read(path / "project.json")
            if record.get("collection") != (collection or None):
                record["previous_collection"] = record.get("collection")
            record["collection"] = collection or None
            record["updated_at"] = time.time()
            put(path / "project.json", record)
        return self.project(conversation)

    def collection_file(self, payload):
        from .workspace_agent import contained

        path = self.collection_path(payload.get("id")) / "files"
        if path.is_symlink():
            raise ValueError("Linked project files are not supported")
        name = payload.get("name")
        if not isinstance(name, str) or not name or len(name) > 500:
            raise ValueError("Supply a relative filename")
        target = contained(path, name)
        try:
            data = base64.b64decode(payload.get("content", ""), validate=True)
        except (ValueError, TypeError) as error:
            raise ValueError("File content must be base64") from error
        if len(data) > 20 * 1024**2:
            raise ValueError("Shared files may be at most 20 MB per upload")
        with self.lock():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        return self.collection(payload["id"])

    @staticmethod
    def context_files(root):
        if root.is_symlink():
            raise ValueError("Linked shared files are not supported")
        files = []
        for path in sorted(root.rglob("*")):
            if path.is_symlink():
                raise ValueError("Shared context must contain real files, not symbolic links")
            if path.is_file():
                files.append(
                    {"name": path.relative_to(root).as_posix(), "size": path.stat().st_size}
                )
        if len(files) > 1024 or sum(f["size"] for f in files) > MAX_CONTEXT_BYTES:
            raise ValueError("Shared context exceeds 1024 files or 512 MB; select a smaller set")
        return files

    def freeze_context(self, conversation, destination):
        """Copy explicit shared context, retaining byte hashes and the source record.

        Must be called inside the workspace lock when used with a launch/turn.
        Historical studies are links, never automatically accepted new evidence.
        """
        record = read(self.directory(conversation) / "project.json")
        key = record.get("collection")
        if not key:
            return None
        source = self.collection_path(key)
        collection = self.collection(key)
        if collection.get("context_error"):
            raise ValueError(collection["context_error"])
        files = collection.pop("files")
        destination = Path(destination)
        destination.mkdir(parents=True, exist_ok=False)
        entries = []
        for info in files:
            original = source / "files" / info["name"]
            target = destination / "files" / info["name"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(original, target)
            with target.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            entries.append(info | {"size": target.stat().st_size, "sha256": digest})
        manifest = {
            "schema_version": 1,
            "project": collection,
            "files": entries,
            "conversation": conversation,
            "evidence_status": "context_only",
        }
        revision = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
        manifest["revision"] = revision
        put(destination / "context.json", manifest)
        return manifest

    @staticmethod
    def context_prompt(manifest, location):
        if not manifest:
            return ""
        project = manifest["project"]
        return (
            f"\nCURRENT SHARED PROJECT CONTEXT: {project['name']}\n"
            "This snapshot replaces any project instructions from earlier turns.\n"
            f"Project instructions: {project.get('instructions', '')}\n"
            f"Description: {project.get('description', '')}\n"
            f"Frozen context manifest and files: {location}\n"
            f"Revision: {manifest['revision']}\n"
            "Read relevant files on demand. Shared material and earlier findings are context, "
            "not accepted evidence for this study. Distinguish experimental variants from "
            "qualified references; changes to the shared baseline do not change past runs. "
            "The current user request takes precedence over project instructions.\n"
        )
