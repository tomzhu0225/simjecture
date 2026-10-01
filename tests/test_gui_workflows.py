"""Executable client regressions independent of installed browser binaries."""

import json
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pytest

STATIC = Path(__file__).parents[1] / "src/conjecture_solver/web/static"


def run_js(code):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is required for client state-machine checks")
    result = subprocess.run([node, "-e", code], capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr


def function_source(name, next_name):
    source = (STATIC / "workspace.js").read_text()
    return source[
        source.index(f"async function {name}(") : source.index(f"async function {next_name}(")
    ]


@pytest.mark.parametrize("change", ["navigation", "typing", "none", "fetch-navigation"])
def test_send_keeps_original_destination_and_preserves_new_draft(change):
    run_js(
        """
const assert = require('node:assert/strict');
const input = {value:'Original message'};
const $ = () => input;
const state = {project:{id:'original'}};
let rendered = 0;
const calls = [];
const renderProject = () => rendered++;
const reloadProjects = async () => {};
"""
        + f"const change = {json.dumps(change)};\n"
        + """
const saveConversationAgent = async () => {
  if (change === 'navigation') {state.project = {id:'new'}; input.value = 'New draft';}
  if (change === 'typing') input.value = 'Next message';
};
const api = async (path, payload) => {
  calls.push([path, payload]);
  if (path.startsWith('project?')) {
    if (change === 'fetch-navigation') {state.project = {id:'new'}; input.value = 'New draft';}
    return {id:'original', updated:true};
  }
};
"""
        + function_source("send", "assistInstallation")
        + """
(async () => {
 await send();
 assert.deepEqual(calls[0], ['message', {project:'original', message:'Original message'}]);
 assert.equal(calls[1][0], 'project?id=original');
 const moved = ['navigation','fetch-navigation'].includes(change);
 assert.equal(state.project.id, moved ? 'new' : 'original');
 assert.equal(rendered, moved ? 0 : 1);
 assert.equal(input.value, moved ? 'New draft' : change === 'typing' ? 'Next message' : '');
})().catch(e => {console.error(e);process.exitCode=1;});
"""
    )


def test_failed_send_preserves_draft():
    run_js(
        """
const assert = require('node:assert/strict');
const input = {value:'Keep this draft'};
const $ = () => input;
const state = {project:{id:'original'}};
const saveConversationAgent = async () => {};
const api = async () => {throw Error('Offline');};
"""
        + function_source("send", "assistInstallation")
        + """
(async () => {
 await assert.rejects(send(), /Offline/);
 assert.equal(input.value,'Keep this draft');
})().catch(e => {console.error(e);process.exitCode=1;});
"""
    )


@pytest.mark.parametrize(
    "saved,expected", [(None, "dark"), ("invalid", "dark"), ("light", "light")]
)
def test_shared_theme_respects_system_and_explicit_choice(saved, expected):
    run_js(
        """
const assert = require('node:assert/strict');
let onSystemChange;
let prevented = false, focused = false;
const document = {documentElement:{dataset:{},classList:{toggle(){}}},
 addEventListener(name, cb) {cb();},
 querySelector() {return {addEventListener(name, cb) {cb({preventDefault(){prevented=true;}});}};},
 getElementById() {return {focus(){focused=true;}};}};
const window = {dispatchEvent(){}};
const matchMedia = () => ({matches:true,addEventListener(name,cb){onSystemChange=cb;}});
"""
        + f"const localStorage = {{getItem:()=>{json.dumps(saved)},setItem(){{}}}};\n"
        + (STATIC / "workspace-theme.js").read_text()
        + f"""
assert.equal(document.documentElement.dataset.theme,{json.dumps(expected)});
assert.ok(prevented && focused);
window.WorkspaceTheme.set('dark');
onSystemChange();
assert.equal(document.documentElement.dataset.theme,'dark');
window.WorkspaceTheme.set('invalid');
assert.equal(document.documentElement.dataset.theme,'dark');
"""
    )


def test_connection_failure_replaces_pending_status():
    source = (STATIC / "workspace.js").read_text()
    handler = source[
        source.index('$("settings-form").onsubmit =') : source.index('$("check-machine").onclick =')
    ]
    run_js(
        """
const assert = require('node:assert/strict');
const elements = new Map();
const $ = id => {
 if(!elements.has(id)) elements.set(id,{value:'',textContent:''});
 return elements.get(id);
};
const state = {};
let pending;
const action = (button, fn) => {pending=fn();};
const api = async () => {throw Error('Connection lost');};
"""
        + handler
        + """
(async () => {
 $('settings-form').onsubmit({preventDefault(){}});
 await assert.rejects(pending,/Connection lost/);
 assert.equal($('connection-result').textContent,'Connection not saved: Connection lost');
})().catch(e => {console.error(e);process.exitCode=1;});
"""
    )


class Elements(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.elements = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


@pytest.mark.parametrize("name", ["workspace.html", "index.html"])
def test_shared_assets_dialog_names_and_keyboard_entry(name):
    parser = Elements((STATIC / name).read_text())
    ids = {attrs["id"] for _, attrs in parser.elements if "id" in attrs}
    for tag, attrs in parser.elements:
        if tag == "dialog":
            assert attrs.get("aria-label") or attrs.get("aria-labelledby") in ids
    assert any(attrs.get("href") == "/assets/interface.css" for _, attrs in parser.elements)
    assert any(attrs.get("src") == "/assets/workspace-theme.js" for _, attrs in parser.elements)
    assert any(
        attrs.get("id") == "main-content" and attrs.get("tabindex") == "-1"
        for _, attrs in parser.elements
    )


def test_repeated_action_is_ignored_while_pending():
    source = (STATIC / "workspace.js").read_text()
    action = source[source.index("async function action(") : source.index("function md(")]
    run_js(
        """
const assert = require('node:assert/strict');
const state = {readonly:false};
const toast = () => {};
"""
        + action
        + """
(async () => {
 const button = {disabled:false};
 let complete, calls = 0;
 const fn = () => {calls++;return new Promise(resolve=>complete=resolve);};
 const pending = action(button, fn);
 await action(button, fn);
 assert.equal(calls,1);
 assert.equal(button.disabled,true);
 complete();await pending;
 assert.equal(button.disabled,false);
 await action(button,async()=>{throw Error('Offline');});
 assert.equal(button.disabled,false);
 state.project = {running:true};
 const sendButton = {id:'send-message',disabled:false};
 await action(sendButton,async()=>{});
 assert.equal(sendButton.disabled,true);
})().catch(e => {console.error(e);process.exitCode=1;});
"""
    )


def test_new_shared_assets_are_served_with_existing_csp(tmp_path):
    import threading

    import httpx

    from conjecture_solver.web.application import SimjectureWebApplication
    from conjecture_solver.web.server import create_server

    app = SimjectureWebApplication(runs_root=tmp_path, scan_roots=(tmp_path,))
    server = create_server(app, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with httpx.Client(
            base_url=f"http://127.0.0.1:{server.server_port}", trust_env=False
        ) as client:
            for path in ["/", "/monitor", "/assets/interface.css", "/assets/workspace-theme.js"]:
                response = client.get(path)
                assert response.status_code == 200
                assert "script-src 'self'" in response.headers["content-security-policy"]
            assert "--ui-radius" in client.get("/assets/interface.css").text
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.mark.parametrize("destination", ["newer-project", "home"])
def test_slow_project_response_does_not_override_newer_navigation(destination):
    source = (STATIC / "workspace.js").read_text()
    opening = source[source.index("async function openProject(") : source.index("function mode(")]
    run_js(
        """
const assert = require('node:assert/strict');
const state = {project:null,projectRequest:0,mode:'interactive'};
const $ = () => ({});
const pending = new Map();
const api = path => new Promise(resolve=>pending.set(path,resolve));
let rendered = [];
const renderProject = () => rendered.push(state.project.id);
const view = () => {};
const renderProjects = () => {};
const renderAgent = async () => {};
"""
        + opening
        + f"const destination = {json.dumps(destination)};\n"
        + """
(async () => {
 const first = openProject('first');
 if (destination === 'newer-project') {
   const second = openProject('second');
   pending.get('project?id=second')({id:'second'});
   assert.equal(await second,true);
 } else {
   state.projectRequest++;
 }
 pending.get('project?id=first')({id:'first'});
 assert.equal(await first,false);
 assert.equal(state.project?.id,destination === 'newer-project' ? 'second' : undefined);
 assert.deepEqual(rendered,destination === 'newer-project' ? ['second'] : []);
})().catch(e => {console.error(e);process.exitCode=1;});
"""
    )


@pytest.mark.parametrize("interrupt", ["agent", "creation", "none"])
def test_first_request_respects_navigation_interruptions(interrupt):
    source = (STATIC / "workspace.js").read_text()
    start = source.index('$("quick-start").onsubmit =')
    end = source.index('for (const b of document.querySelectorAll("[data-example]"))', start)
    run_js(
        """
const assert = require('node:assert/strict');
const elements = new Map();
const $ = id => {
 if(!elements.has(id)) elements.set(id,{value:'original request'});
 return elements.get(id);
};
const state = {projectRequest:0};
let pending, created=0, opened=0, sent=0;
const action = (button, fn) => {pending=fn();};
const mode = () => {};
const reloadProjects = async () => {};
const openProject = async () => {opened++;return true;};
const send = async () => {sent++;};
"""
        + f"const interrupt = {json.dumps(interrupt)};\n"
        + """
const saveConversationAgent = async () => {
 if(interrupt === 'agent') state.projectRequest++;
 return {};
};
const api = async () => {
 created++;
 if(interrupt === 'creation') state.projectRequest++;
 return {id:'new'};
};
"""
        + source[start:end]
        + """
(async () => {
 $('quick-start').onsubmit({preventDefault(){},submitter:{}});
 await pending;
 assert.equal(created,interrupt === 'agent' ? 0 : 1);
 assert.equal(opened,interrupt === 'none' ? 1 : 0);
 assert.equal(sent,interrupt === 'none' ? 1 : 0);
 assert.equal($('first-request').value,interrupt === 'none' ? '' : 'original request');
})().catch(e => {console.error(e);process.exitCode=1;});
"""
    )
