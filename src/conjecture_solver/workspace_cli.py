"""JSON-first local workspace/project operations, sharing the browser services."""

import base64
import json
from pathlib import Path

from .workspace_projects import WorkspaceDirectory


def configure(parser, kind):
    parser.add_argument("--runs-root", type=Path, default=Path("artifacts"))
    parser.add_argument("--workspace", default="personal", help="Explicit workspace ID")
    actions = parser.add_subparsers(dest="action", required=True)
    actions.add_parser("list")
    create = actions.add_parser("create")
    create.add_argument("--name", required=True)
    if kind == "workspace":
        create.add_argument("--id")
        call = actions.add_parser("call", help="Call an existing workspace operation using JSON")
        call.add_argument("operation", choices=("message", "stop", "brief", "launch", "status"))
        call.add_argument("--conversation", required=True)
        call.add_argument("--payload-file", type=Path)
    if kind == "project":
        create.add_argument("--instructions-file", type=Path)
        show = actions.add_parser("show")
        show.add_argument("id")
        update = actions.add_parser("update")
        update.add_argument("id")
        update.add_argument("--name")
        update.add_argument("--instructions-file", type=Path)
        update.add_argument("--description")
        upload = actions.add_parser("add-file")
        upload.add_argument("id")
        upload.add_argument("file", type=Path)
        upload.add_argument("--name")
        snapshot = actions.add_parser("snapshot", help="Freeze context for an external agent/study")
        snapshot.add_argument("--conversation", required=True)
        snapshot.add_argument("--output", type=Path, required=True)
    if kind == "conversation":
        create.add_argument("--project", help="Optional collection ID")
        show = actions.add_parser("show")
        show.add_argument("id")
        move = actions.add_parser("move")
        move.add_argument("id")
        move.add_argument("--project", help="Omit to remove from a project")
    parser.set_defaults(handler=run, workspace_kind=kind)


def run(args):
    directory = WorkspaceDirectory(args.runs_root)
    try:
        workspace = directory.open(args.workspace)
        kind, action = args.workspace_kind, args.action
        values = {
            key: getattr(args, key)
            for key in ("name", "description")
            if getattr(args, key, None) is not None
        }
        if getattr(args, "instructions_file", None):
            values["instructions"] = args.instructions_file.read_text()
        if kind == "workspace":
            if action == "list":
                result = directory.list()
            elif action == "create":
                result = directory.create(values | ({"id": args.id} if args.id else {}))
            else:
                payload = json.loads(args.payload_file.read_text()) if args.payload_file else {}
                if not isinstance(payload, dict):
                    raise ValueError("Payload must be a JSON object")
                methods = {"message": workspace.send, "brief": workspace.save_brief}
                if args.operation in methods:
                    result = methods[args.operation](args.conversation, payload)
                elif args.operation == "launch":
                    from .web.application import SimjectureWebApplication

                    result = workspace.launch(
                        args.conversation,
                        payload,
                        SimjectureWebApplication(runs_root=args.runs_root),
                    )
                elif args.operation == "stop":
                    result = workspace.stop(args.conversation)
                else:
                    result = workspace.project(args.conversation)
        elif kind == "project":
            if action == "list":
                result = workspace.collections()
            elif action in ("create", "update"):
                result = workspace.save_collection(
                    values | ({"id": args.id} if action == "update" else {})
                )
            elif action == "show":
                result = workspace.collection(args.id)
            elif action == "add-file":
                if args.file.stat().st_size > 20 * 1024**2:
                    raise ValueError("Shared files may be at most 20 MB per upload")
                result = workspace.collection_file(
                    {
                        "id": args.id,
                        "name": args.name or args.file.name,
                        "content": base64.b64encode(args.file.read_bytes()).decode(),
                    }
                )
            else:
                with workspace.lock():
                    result = workspace.freeze_context(args.conversation, args.output)
        else:
            if action == "list":
                result = workspace.projects()
            elif action == "create":
                result = workspace.create(values | {"collection": args.project})
            elif action == "move":
                result = workspace.assign_collection(args.id, args.project)
            else:
                result = workspace.project(args.id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, TypeError) as error:
        print(json.dumps({"error": str(error)}))
        return 2
