# Projects and workspaces

Start a conversation as usual. Simjecture opens the Personal workspace by
default; creating a project or another workspace is optional. Existing
conversations, file paths and study links continue to work.

A **project** groups conversations around a question, device or programme. Its
shared instructions and files provide context for those conversations. Each
conversation can still have its own interactive work and autonomous studies.

A **workspace** is a separate local place for research, with its own conversations,
projects, saved model connections and machine registrations. Use the workspace
name above **New conversation** to switch or create one. Switching does not stop
running agents or studies. Selection is recorded in the URL, so two browser tabs
can work in different spaces at the same time.

## Use a project

Choose **+** beside **Projects**, give it a name and optionally add instructions.
The project overview shows its conversations and shared files. Start a conversation
there to include it in the project. For an existing conversation, use the **Project**
selector below its title. Choose **No project** to remove that membership.

Shared files are explicit uploads, not an automatic scan of your computer. Each
upload is limited to 20 MB. Larger files may be placed directly in the project's
`files/` directory shown by the CLI. The complete shared input set is limited to
1024 files and 512 MB, and symbolic links are rejected. Select reference inputs
and compact evidence indexes rather than copying entire output archives.

Every interactive turn and autonomous launch freezes the current shared files,
instructions and their hashes. The agent gets instructions and a manifest location;
it reads relevant files on demand. Changing a shared file affects subsequent work,
not the bytes recorded for a previous turn or study. These snapshots are context,
not automatically accepted scientific evidence. A study still uses the existing
experiment contracts and independent review.

Project membership does not move conversation directories or rewrite historical
study records. Moving is blocked while the interactive agent is working. A running
autonomous study retains its launch context.

## CLI and external agents

The CLI and browser use the same local services and records. No browser or running
HTTP server is required for the following commands. Commands return JSON; validation
failures return an error object and exit code 2. Place common options before the
action, and use IDs from the returned records.

```bash
simjecture workspace --runs-root artifacts list
simjecture workspace --runs-root artifacts create --name "Example lab" --id lab

simjecture project --runs-root artifacts --workspace lab create \
  --name "Magnetic-field study" --instructions-file instructions.md

simjecture conversation --runs-root artifacts --workspace lab create \
  --name "Check the reference case" --project PROJECT_ID

simjecture project --runs-root artifacts --workspace lab add-file \
  PROJECT_ID reference.json
simjecture project --runs-root artifacts --workspace lab show PROJECT_ID
simjecture conversation --runs-root artifacts --workspace lab move \
  CONVERSATION_ID --project PROJECT_ID
```

`project update` accepts `--name`, `--description` and `--instructions-file`.
`conversation move` without `--project` removes the membership. Omit `--workspace`
for Personal; selection is explicit per command and is never saved as a global
current directory or account switch.

External agents can export a frozen context into a new directory:

```bash
simjecture project --runs-root artifacts --workspace lab snapshot \
  --conversation CONVERSATION_ID --output ./selected-context
```

The JSON response includes the context revision, file hashes and
`evidence_status: context_only`. If the conversation has no project, the response
is `null` and no directory is created. Existing output directories are never
overwritten. A standalone `simjecture study` remains independent: deliberately
include the selected context in its preparation, or launch through the conversation
bridge to get the automatic snapshot.

For interactive work and autonomous handoff, `workspace call` exposes the existing
operations: `message`, `brief`, `launch`, `status` and `stop`.

```bash
simjecture workspace --runs-root artifacts --workspace lab call message \
  --conversation CONVERSATION_ID --payload-file request.json
simjecture workspace --runs-root artifacts --workspace lab call status \
  --conversation CONVERSATION_ID
```

A message payload is `{"message":"Inspect the reference inputs and prepare a study."}`.
Sending it starts the configured agent and can consume provider credit. `brief`
accepts `question`, `success_criteria`, `constraints`, `hours` and
`completion_policy`. `launch` requires a unique `request_key` and uses the saved
brief and model configuration, exactly as the browser does. It starts a real
autonomous run. `stop` stops the interactive turn; study cancellation uses the
existing study controls.

The local HTTP counterparts are under `/api/workspace/`. Append
`?workspace=WORKSPACE_ID` to every scoped request. `GET bootstrap` returns spaces,
collections and conversations; `GET collection?id=PROJECT_ID` returns shared
context. `POST workspaces`, `collections`, `assign-collection` and
`collection-file` create spaces, create/update projects, change conversation
membership, and upload base64-encoded files. Existing conversation APIs keep
their historical `project` names for compatibility. Mutations require the local
control token, and read-only servers reject them.

## Storage and deployment scope

Personal retains the existing `artifacts/.workspace` and `artifacts/projects`
locations. Additional workspaces live under `artifacts/workspaces/WORKSPACE_ID/`.
Project metadata and shared files live in `.workspace/collections/PROJECT_ID/`.
New workspaces start with separate settings; credentials are not copied from
Personal. Installed software and native CLI logins can still be shared by the
same operating-system account.

Local workspaces organise trusted research; they are not security boundaries
between mutually untrusted companies or agents. Use separate installations and
OS/container identities where that boundary is required. The hosted public trial
keeps its existing account isolation and single-workspace interface; local
workspace management is not exposed as a hosted tenant-management feature.

Private device assets belong in these user-data locations or a private repository,
not in a package example. The distributed examples and automated fixtures use
generic inputs. Creating a workspace does not publish or upload its contents.
