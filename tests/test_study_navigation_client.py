"""Run the shared study navigation state machine without browser or provider access."""

import json
import re

import pytest

from tests.test_gui_workflows import STATIC, run_js


def client_function(name, filename="workspace.js"):
    """Extract a top-level function while executing its actual shipped implementation."""
    source = (STATIC / filename).read_text()
    start = re.search(rf"^(?:async )?function {name}\(", source, re.MULTILINE)
    assert start, name
    following = re.search(r"^(?:async )?function \w+\(", source[start.end() :], re.MULTILINE)
    end = start.end() + following.start() if following else len(source)
    return source[start.start() : end]


DOM = """
const assert = require('node:assert/strict');
class Element {
  constructor(tag) {
    this.tagName = tag;
    this.children = [];
    this.attributes = {};
    this.dataset = {};
    this.classList = {toggle() {}};
  }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  setAttribute(name, value) { this.attributes[name] = value; }
  querySelectorAll() { return []; }
}
const document = {createElement: tag => new Element(tag)};
const window = {};
"""


def navigation_source():
    return (STATIC / "study-navigation.js").read_text()


def test_navigation_urls_round_trip_exact_ids_without_extra_parameters():
    run_js(
        DOM
        + navigation_source()
        + """
const project = 'owner & name', campaign = 'campaign?#/=', turn = 'review & turn';
const route = new URL(window.StudyNavigation.workspace(project, campaign,
  'interactive', {turn}), 'http://localhost');
const params = new URLSearchParams(route.hash.slice(1));
assert.equal(route.pathname, '/workspace');
assert.equal(params.get('project'), project);
assert.equal(params.get('study'), campaign);
assert.equal(params.get('view'), 'interactive');
assert.equal(params.get('turn'), turn);
assert.equal([...params].length, 4);
const evidence = new URL(window.StudyNavigation.evidence(campaign), 'http://localhost');
assert.equal(evidence.pathname, '/monitor');
assert.deepEqual([...evidence.searchParams], [['campaign', campaign]]);
"""
    )


@pytest.mark.parametrize("page", ["conversation", "study", "evidence"])
def test_owned_navigation_has_one_current_step_and_keeps_study_on_return(page):
    run_js(
        DOM
        + navigation_source()
        + f"const page = {json.dumps(page)};\n"
        + """
const container = new Element('nav');
window.StudyNavigation.render(container,
  {project:'owner', campaign:'older-study', page, title:'Original question'});
const links = container.children[0].children.map(item => item.children[0]);
assert.deepEqual(links.map(link => link.textContent),
  ['Conversation', 'Study', 'Evidence & review']);
assert.equal(links.filter(link => link.attributes['aria-current'] === 'page').length, 1);
assert.equal(links[['conversation','study','evidence'].indexOf(page)].tagName, 'span');
for (const [index, link] of links.entries()) {
  if (index < 2 && link.href) {
    const params = new URLSearchParams(new URL(link.href, 'http://localhost').hash.slice(1));
    assert.equal(params.get('project'), 'owner');
    assert.equal(params.get('study'), 'older-study');
  }
}
assert.equal(links[1].title, 'Original question');
window.StudyNavigation.render(container, {project:'owner', campaign:'newer-study', page});
assert.equal(container.children.length, 1, 're-render must replace, not duplicate the trail');
"""
    )


def test_standalone_evidence_does_not_invent_an_owning_conversation():
    run_js(
        DOM
        + navigation_source()
        + """
const container = new Element('nav');
window.StudyNavigation.render(container, {project:null, campaign:'cli-study', page:'evidence'});
const links = container.children[0].children.map(item => item.children[0]);
assert.deepEqual(links.map(link => link.textContent),
  ['Workspace', 'Standalone study', 'Evidence & review']);
assert.equal(links[0].href, '/workspace');
assert.equal(links[1].tagName, 'span');
assert.equal(links[1].href, undefined);
assert.equal(links[2].attributes['aria-current'], 'page');
window.StudyNavigation.render(container, {project:'new-conversation', campaign:null,
  page:'conversation'});
const unavailable = container.children[0].children[2].children[0];
assert.equal(unavailable.tagName, 'span');
assert.equal(unavailable.href, undefined);
assert.match(unavailable.title, /after a study is started/);
"""
    )


def test_study_selection_retains_owned_history_and_rejects_foreign_campaign():
    run_js(
        DOM
        + navigation_source()
        + """
const select = window.StudyNavigation.selected;
const project = {studies:[{campaign:'older'}, {campaign:'latest'}],
  continuation_draft:{campaign:'parent'}};
assert.equal(select(project, 'older'), 'older');
assert.equal(select(project, 'latest'), 'latest');
assert.equal(select(project, 'parent'), 'parent');
assert.equal(select(project, 'foreign'), 'latest');
assert.equal(select(project, null), 'latest');
assert.equal(select({studies:[], continuation_draft:{campaign:'parent'}}, null), 'parent');
assert.equal(select({studies:[]}, 'foreign'), null);
assert.equal(select(null, 'foreign'), null);
"""
    )


def test_project_links_and_mode_switches_preserve_selected_older_study():
    run_js(
        DOM
        + navigation_source()
        + """
const state = {project:{id:'owner', studies:[{campaign:'older'}, {campaign:'latest'}]},
  routeStudy:'older', mode:'autonomous', view:'project', routing:false};
const elements = new Map();
const $ = id => {
  if (!elements.has(id)) elements.set(id, new Element('div'));
  return elements.get(id);
};
const location = {hash:''};
const refreshTools = async () => {};
const renderStudies = async () => {};
const toast = error => {throw error;};
"""
        + client_function("projectHash")
        + client_function("renderStudyNavigation")
        + client_function("mode")
        + """
mode('interactive');
let params = new URLSearchParams(location.hash);
assert.equal(params.get('view'), 'interactive');
assert.equal(params.get('study'), 'older');
mode('autonomous');
params = new URLSearchParams(location.hash);
assert.equal(params.get('view'), 'autonomous');
assert.equal(params.get('study'), 'older');
assert.equal(state.routeStudy, 'older');
assert.equal(new URLSearchParams(projectHash('other', {view:'autonomous'})).get('study'), null);
assert.equal(new URLSearchParams(projectHash('owner', {study:'latest'})).get('study'), 'latest');
"""
    )


@pytest.mark.parametrize("outcome", ["success", "failure"])
def test_late_monitor_snapshot_cannot_replace_new_campaign_or_clear_its_pending_flag(outcome):
    run_js(
        """
const assert = require('node:assert/strict');
const state = {selectedCampaign:'old', snapshotRequest:0, pollInFlight:false};
const pending = new Map(), rendered = [], sync = [], errors = [];
const api = path => new Promise((resolve,reject) => pending.set(path,{resolve,reject}));
const renderSnapshot = () => rendered.push(state.snapshot.id);
const setSync = (...args) => sync.push(args);
const showToast = (...args) => errors.push(args);
"""
        + client_function("refreshSnapshot", "app.js")
        + f"const outcome = {json.dumps(outcome)};\n"
        + """
(async () => {
 const old = refreshSnapshot(true);
 state.selectedCampaign = 'new';
 const newer = refreshSnapshot(true);
 const request = pending.get('/api/snapshot?campaign=old');
 if (outcome === 'success') request.resolve({id:'old'});
 else request.reject(Error('Old request failed'));
 await old;
 assert.equal(state.pollInFlight,true, 'old completion must not unlock a newer poll');
 assert.equal(state.snapshot, undefined);
 assert.deepEqual(rendered, []);
 assert.deepEqual(errors, []);
 assert.deepEqual(sync, []);
 pending.get('/api/snapshot?campaign=new').resolve({id:'new'});
 await newer;
 assert.equal(state.pollInFlight,false);
 assert.equal(state.snapshot.id,'new');
 assert.deepEqual(rendered,['new']);
})().catch(error => {console.error(error);process.exitCode=1;});
"""
    )


def test_monitor_history_changes_campaign_without_creating_a_history_loop():
    run_js(
        DOM
        + """
let current = new URL('http://localhost/monitor?campaign=old&extra=kept');
const location = {};
Object.defineProperties(location, {
 href:{get:()=>current.href}, search:{get:()=>current.search}
});
const historyCalls = [];
const history = {};
for (const method of ['pushState','replaceState']) history[method] = (_,__,url) => {
 historyCalls.push([method,String(url)]); current = new URL(url,current);
};
const elements = new Map();
const get = id => {
 if (!elements.has(id)) elements.set(id,new Element('div'));
 return elements.get(id);
};
document.getElementById = get;
const ui = new Proxy({}, {get:(_,id)=>get(id)});
const state = {selectedCampaign:'old',snapshot:{id:'old'},
 expandedDetails:new Set(['stale']),executionConsoleCache:new Map([['stale',{}]]),
 executionLoads:new Set(['stale'])};
let loaded = [];
const loadGraphPositions = () => {};
const resetRenderSignatures = () => {};
const setSync = () => {};
const refreshSnapshot = async () => loaded.push(state.selectedCampaign);
"""
        + client_function("writeCampaignRoute", "app.js")
        + client_function("selectCampaign", "app.js")
        + """
(async () => {
 await selectCampaign('new');
 assert.equal(current.searchParams.get('campaign'),'new');
 assert.equal(current.searchParams.get('extra'),'kept');
 assert.equal(historyCalls.length,1);
 assert.equal(historyCalls[0][0],'pushState');
 assert.equal(ui['campaign-select'].value,'new');
 assert.equal(ui.dashboard.hidden,true);
 assert.equal(get('study-navigation').hidden,true);
 assert.equal(get('continue-study-link').hidden,true);
 assert.equal(get('conversation-return').href,'/workspace');
 assert.equal(state.expandedDetails.size,0);
 assert.equal(state.executionConsoleCache.size,0);
 current = new URL('http://localhost/monitor?campaign=old');
 await selectCampaign('old',{history:false});
 assert.equal(state.selectedCampaign,'old');
 assert.equal(historyCalls.length,1,'popstate must not append a new history entry');
 await selectCampaign('old');
 assert.deepEqual(loaded,['new','old'],'reselecting the same campaign must be inert');
})().catch(error => {console.error(error);process.exitCode=1;});
"""
    )


@pytest.mark.parametrize("interruption", ["project", "mode", "request"])
def test_stale_study_list_response_does_not_repaint_newer_context(interruption):
    run_js(
        """
const assert = require('node:assert/strict');
const state = {project:{id:'old',studies:[{campaign:'old'}]},
 mode:'autonomous',studyRequest:0};
let resolve;
const api = () => new Promise(done=>resolve=done);
const renderStudyNavigation = () => {throw Error('Stale navigation rendered');};
const $ = () => {throw Error('Stale studies rendered');};
"""
        + client_function("renderStudies")
        + f"const interruption = {json.dumps(interruption)};\n"
        + """
(async () => {
 const pending = renderStudies();
 if (interruption === 'project') state.project = {id:'new',studies:[]};
 if (interruption === 'mode') state.mode = 'interactive';
 if (interruption === 'request') state.studyRequest++;
 resolve({snapshot:{}});
 await pending;
 assert.equal(state.studyRevision,undefined);
})().catch(error => {console.error(error);process.exitCode=1;});
"""
    )


ACTION_DOM = """
Element.prototype.addEventListener = function(name, callback) {
 this.listeners ||= {}; this.listeners[name] = callback;
};
Element.prototype.close = function() {
 this.open = false; this.listeners?.close?.({});
};
Element.prototype.showModal = function() {this.open = true;};
Element.prototype.remove = function() {this.removed = true;};
Element.prototype.focus = function() {};
document.body = new Element('body');
document.createTextNode = text => text;
const el = (tag,text,cls) => {
 const element = new Element(tag); element.textContent = text; element.className = cls;
 return element;
};
const bytes = value => `${value} B`;
const crypto = require('node:crypto');
const state = {readonly:false,projectRequest:0,
 project:{id:'owner',studies:[{campaign:'parent'}]},researchAction:null};
const location = {hash:'#project=owner&view=autonomous&study=parent'};
let opened = [], modes = [], reloaded = 0, toasts = [];
const reloadProjects = async () => {reloaded++;};
const openProject = async id => {opened.push(id);return true;};
const mode = name => modes.push(name);
const toast = (...args) => toasts.push(args);
const renderStudies = async () => {};
const all = root => [root,...root.children.flatMap(child =>
 child instanceof Element ? all(child) : [])];
const button = (dialog,text) => all(dialog).find(item =>
 item.tagName === 'button' && item.textContent === text);
const submitEvent = dialog => ({preventDefault(){},submitter:button(dialog,'Prepare directly')});
"""


@pytest.mark.parametrize("interruption", ["hash", "project-request"])
def test_pending_continuation_preview_does_not_open_after_navigation(interruption):
    run_js(
        DOM
        + navigation_source()
        + ACTION_DOM
        + """
let resolve, previews=0;
const api = () => {previews++;return new Promise(done=>resolve=done);};
"""
        + client_function("openResearchAction")
        + f"const interruption = {json.dumps(interruption)};\n"
        + """
(async () => {
 const first = openResearchAction('parent','continue');
 await openResearchAction('parent','continue');
 assert.equal(previews,1,'repeated clicks must not fetch/open duplicate dialogs');
 if (interruption === 'hash') location.hash = '#home';
 else state.projectRequest++;
 resolve({files:[]}); await first;
 assert.equal(document.body.children.length,0);
 assert.equal(state.researchAction,null);
 assert.deepEqual(opened,[]);
})().catch(error => {console.error(error);process.exitCode=1;});
"""
    )


@pytest.mark.parametrize("dismissal", ["cancel", "escape"])
def test_cancelled_continuation_is_mutation_free_and_can_be_reopened(dismissal):
    run_js(
        DOM
        + navigation_source()
        + ACTION_DOM
        + """
const calls = [];
const api = async (path,payload) => {calls.push([path,payload]);return {files:[]};};
"""
        + client_function("openResearchAction")
        + f"const dismissal = {json.dumps(dismissal)};\n"
        + """
(async () => {
 await openResearchAction('parent','continue');
 const dialog = state.researchAction.dialog;
 if (dismissal === 'cancel') button(dialog,'Cancel').onclick();
 else {
   let prevented=false;
   dialog.listeners.cancel({preventDefault(){prevented=true;}});
   assert.equal(prevented,false);
   dialog.close();
 }
 assert.equal(state.researchAction,null);
 assert.equal(dialog.removed,true);
 await dialog.children[0].onsubmit(submitEvent(dialog));
 assert.equal(calls.length,1,'a closed dialog must not submit');
 await openResearchAction('parent','continue');
 assert.notEqual(state.researchAction.dialog,dialog);
 assert.equal(calls.length,2);
 assert.ok(calls.every(([path])=>path.startsWith('continuation-preview?')));
})().catch(error => {console.error(error);process.exitCode=1;});
"""
    )


@pytest.mark.parametrize("destination", ["owned", "foreign", "departed"])
def test_continuation_submit_captures_owner_and_ignores_duplicates_and_late_navigation(destination):
    run_js(
        DOM
        + navigation_source()
        + ACTION_DOM
        + f"const destination = {json.dumps(destination)};\n"
        + """
if (destination === 'foreign') state.project = {id:'unrelated',studies:[]};
const calls = [];
let complete;
const api = async (path,payload) => {
 calls.push([path,payload]);
 if (path.startsWith('continuation-preview?')) return {files:[{path:'calculate.py',bytes:10}]};
 return new Promise(resolve=>complete=resolve);
};
"""
        + client_function("openResearchAction")
        + """
(async () => {
 await openResearchAction('parent','continue');
 const dialog = state.researchAction.dialog, form = dialog.children[0];
 all(dialog).find(item=>item.tagName === 'textarea').value = 'Test the boundary independently';
 // Model a project refresh; the mutation must still use the captured source owner.
 state.project = {id:'later',studies:[{campaign:'parent'}]};
 const first = form.onsubmit(submitEvent(dialog));
 await form.onsubmit(submitEvent(dialog));
 assert.equal(calls.length,2,'preview and exactly one preparation request');
 const [path,payload] = calls[1];
 assert.equal(path,'prepare-continuation');
 assert.equal(payload.campaign,'parent');
 assert.equal(payload.project,destination === 'foreign' ? null : 'owner');
 assert.deepEqual(payload.files,['calculate.py']);
 assert.equal(payload.guidance,'Test the boundary independently');
 assert.equal(button(dialog,'Cancel').disabled,true);
 let prevented=false;
 dialog.listeners.cancel({preventDefault(){prevented=true;}});
 assert.equal(prevented,true,'Escape must not imply cancellation of an in-flight mutation');
 if (destination === 'departed') {
   location.hash='#home'; state.projectRequest++; dialog.close();
 }
 complete({project:'owner',view:'autonomous',message:'Prepared'});
 await first;
 assert.equal(reloaded,1);
 assert.deepEqual(opened,destination === 'departed' ? [] : ['owner']);
 assert.deepEqual(modes,destination === 'departed' ? [] : ['autonomous']);
 assert.equal(state.researchAction,null);
})().catch(error => {console.error(error);process.exitCode=1;});
"""
    )


@pytest.mark.parametrize("owned", [True, False])
@pytest.mark.parametrize("readonly", [True, False])
def test_monitor_return_and_action_links_use_server_ownership_and_respect_readonly(owned, readonly):
    run_js(
        DOM
        + navigation_source()
        + f"const owned={json.dumps(owned)}, readonly={json.dumps(readonly)};\n"
        + """
const elements = new Map();
document.getElementById = id => {
 if (!elements.has(id)) elements.set(id,new Element('div'));
 return elements.get(id);
};
const ui = new Proxy({}, {get:(_,id)=>document.getElementById(id)});
const location = {href:'http://localhost/monitor?campaign=parent'};
const context = owned ? {project_id:'owner',project_name:'Original conversation'} : null;
const data = {workspace_context:context, display_name:'Original study',
 engine:{mode:'minimal',status:'running',remaining_seconds:600}};
const state = {selectedCampaign:'parent',allowMutations:!readonly,snapshot:data};
"""
        + client_function("renderStudyNavigation", "app.js")
        + client_function("renderControls", "app.js")
        + """
renderStudyNavigation(data);
renderControls({can_pause:true,can_resume:true,can_cancel:true});
const returned = document.getElementById('conversation-return');
assert.equal(returned.textContent,owned ? 'Back to this conversation' : 'Workspace');
const target = new URL(returned.href,location.href);
const params = new URLSearchParams(target.hash.slice(1));
assert.equal(params.get('project'),owned ? 'owner' : null);
assert.equal(params.get('study'),owned ? 'parent' : null);
for (const [id,query] of [['continue-study-link','continue-study'],
 ['steer-study-link','steer-study']]) {
 const link = document.getElementById(id);
 assert.equal(link.hidden,readonly);
 const action = new URL(link.href,location.href);
 assert.equal(action.searchParams.get(query),'parent');
 const destination = new URLSearchParams(action.hash.slice(1));
 assert.equal(destination.get('project'),owned ? 'owner' : null);
 assert.equal(destination.get('study'),owned ? 'parent' : null);
}
assert.equal(ui['pause-button'].disabled,readonly);
assert.equal(ui['resume-button'].disabled,readonly);
assert.equal(ui['cancel-button'].disabled,readonly);
"""
    )


@pytest.mark.parametrize("requested", ["older", "missing", None])
def test_route_reload_recovers_and_normalizes_selected_study(requested):
    run_js(
        DOM
        + navigation_source()
        + f"const requested={json.dumps(requested)};\n"
        + """
const project = {id:'owner',studies:[{campaign:'older'},{campaign:'latest'}]};
const state = {project:null,projectRequest:0,routeStudy:null,routing:false};
const location = {hash:'#project=owner&view=autonomous' +
 (requested ? '&study=' + requested : '')};
const history = {replaceState(_,__,hash) {location.hash=hash;}};
const opened=[], rendered=[], scrolled=[];
const openProject = async id => {opened.push(id);state.project=project;return true;};
const view = name => {state.view=name;};
const mode = name => {state.mode=name;};
const renderStudies = async () => rendered.push(state.routeStudy);
document.getElementById = id => ({scrollIntoView(){scrolled.push(id);}});
const monitor = {open:async()=>{throw Error('Unexpected monitor');}};
const toast = error => {throw error;};
"""
        + client_function("followRoute")
        + """
(async () => {
 await followRoute();
 await new Promise(resolve=>setImmediate(resolve));
 const expected = requested === 'older' ? 'older' : 'latest';
 assert.deepEqual(opened,['owner']);
 assert.equal(state.routeStudy,expected);
 assert.equal(state.mode,'autonomous');
 assert.equal(state.routing,false);
 assert.equal(new URLSearchParams(location.hash.slice(1)).get('study'),expected);
 assert.ok(rendered.length > 0 && rendered.every(id=>id===expected));
 assert.ok(scrolled.every(id=>id===`study-${expected}`));
})().catch(error => {console.error(error);process.exitCode=1;});
"""
    )


@pytest.mark.parametrize("interruption", ["agent", "launch", "refresh", "none"])
def test_study_launch_keeps_original_project_and_does_not_reopen_departed_route(interruption):
    launch = client_function("launchStudy").split('\n$("brief-form").onsubmit')[0]
    run_js(
        """
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const state = {project:{id:'owner',brief:{},studies:[]},projectRequest:0,
 briefDirty:false,launchKey:null};
const location = {hash:'#project=owner&view=autonomous'};
const $ = () => ({value:'fixture'});
let renders=0, studies=0, modes=[], toasts=[], calls=[];
const renderProject = () => {renders++;};
const renderStudies = async () => {studies++;};
const mode = name => modes.push(name);
const toast = message => toasts.push(message);
const leave = () => {
 state.project={id:'newer',studies:[]};state.projectRequest++;location.hash='#home';
};
"""
        + f"const interruption={json.dumps(interruption)};\n"
        + """
const saveConversationAgent = async () => {if(interruption === 'agent') leave();};
const saveBrief = async () => {throw Error('Unexpected brief save');};
const api = async (path,payload) => {
 calls.push([path,payload]);
 if(path === 'launch') {
   if(interruption === 'launch') leave();
   return {campaign:'launched'};
 }
 if(interruption === 'refresh') leave();
 return {id:'owner',studies:[{campaign:'launched'}]};
};
"""
        + launch
        + """
(async () => {
 await launchStudy();
 if (interruption === 'agent') assert.deepEqual(calls,[]);
 else {
   assert.equal(calls[0][0],'launch');
   assert.equal(calls[0][1].project,'owner');
   assert.equal(calls[1][0],'project?id=owner');
 }
 const stayed = interruption === 'none';
 assert.equal(state.project.id,stayed ? 'owner' : 'newer');
 assert.equal(state.routeStudy,stayed ? 'launched' : undefined);
 assert.equal(renders,stayed ? 1 : 0);
 assert.equal(studies,stayed ? 1 : 0);
 assert.deepEqual(modes,stayed ? ['autonomous'] : []);
 assert.equal(toasts.length,stayed ? 1 : 0);
})().catch(error => {console.error(error);process.exitCode=1;});
"""
    )
