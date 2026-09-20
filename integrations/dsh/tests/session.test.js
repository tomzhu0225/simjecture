import assert from 'node:assert/strict'
import { test } from 'node:test'
import { mkdtemp, readFile, rm, writeFile, mkdir } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { Session, SessionId } from '@deepseek-ai/dsh-session'
import { createAssistantMessage, createToolResultMessage } from '@deepseek-ai/dsh-llm'
import TokenMeter from '@deepseek-ai/dsh-token-meter'
import Pruner from '@deepseek-ai/dsh-compaction-tool-result-pruner'
import * as Elider from '../context-elider.js'
import * as Runner from '../runner.js'
import { LEAD_TOOL_NAMES } from '../roles.js'
import { runtime, tool, answer } from './runtime.js'

test('real V3 sessions retain original events while eliding balanced calls and pruning results', async () => {
  const { ctx } = await runtime()
  await ctx.plugin(TokenMeter)
  await ctx.plugin(Pruner, { thresholdChars: 1000, headChars: 100, tailChars: 100 })
  let preStep
  Elider.apply({ tokenMeter: ctx.tokenMeter, toolResultPruner: ctx.toolResultPruner,
    logger: { warn: message => assert.fail(message) }, on: (_name, handler) => { preStep = handler } })
  try {
    for (const [name, args, result] of [
      ['mcp__simjecture__write_workspace_file', JSON.stringify({ content: 'x'.repeat(3000) }), '{"path":"result.txt","sha256":"abc"}'],
      ['mcp__simjecture__claims', '{}', 'y'.repeat(3000)],
    ]) {
      const session = Session.create(SessionId(`test-${name}`))
      session.append('assistant/message', { turn: 1, step: 1, stream: [], message: createAssistantMessage({
        content: [{ type: 'tool-call', id: 'call', name, arguments: args }], source: { provider: 'test', model: 'scripted' },
      }) }, { surfaceOp: 'append' })
      session.append('tool/result', { turn: 1, step: 1, message: createToolResultMessage({
        callId: 'call', content: [{ type: 'text', text: result }], isError: false,
      }) }, { surfaceOp: 'append' })
      const original = JSON.stringify(session.snapshotEvents())
      const count = session.seq
      const step = () => preStep({ agent: { session }, signal: new AbortController().signal }, () => {})
      await step()
      assert.equal(session.seq, count, 'one request must see the complete exchange')
      await step()
      assert.ok(session.seq > count)
      assert.equal(JSON.stringify(session.snapshotEvents().slice(0, count)), original)
      assert.ok(JSON.stringify(session.deriveMessages()).length < 2000)
      const restored = Session.create(SessionId('replay'), session.snapshotEvents())
      assert.deepEqual(restored.deriveMessages(), session.deriveMessages())
      assert.equal(session.snapshotEvents().filter(e => e.type === 'compaction/prune').length, 1)
    }
  } finally { await ctx.fiber.dispose() }
})

test('production runner persists and resumes the same real agent with lead tool restrictions', async () => {
  const root = await mkdtemp(join(tmpdir(), 'simjecture-dsh-runner-'))
  await mkdir(join(root, 'records'))
  const saved = { ...process.env }
  Object.assign(process.env, {
    SIMJECTURE_WORKSPACE: join(root, 'records'), SIMJECTURE_DSH_RESEARCH_ROOT: join(root, 'research'),
    SIMJECTURE_DSH_SESSION_ID: 'simjecture-test', SIMJECTURE_DSH_ACTIVITY_FILE: join(root, 'activity.jsonl'),
    SIMJECTURE_DSH_STATE_FILE: join(root, 'state.json'), SIMJECTURE_DSH_CONTROL_FILE: join(root, 'control.json'),
  })
  try {
    for (const resume of [false, true]) {
      process.env.SIMJECTURE_DSH_RESUME = resume ? '1' : '0'
      const { ctx, model } = await runtime([answer(resume ? 'resumed' : 'fresh')], join(root, 'sessions'))
      try {
        for (const name of LEAD_TOOL_NAMES) tool(ctx, name)
        tool(ctx, 'native_shell')
        const exited = new Promise(resolve => ctx.provide('appExit', resolve))
        Runner.apply(ctx, { task: resume ? 'reconcile snapshot and continue' : 'begin campaign' })
        assert.equal(await exited, 0)
        const state = JSON.parse(await readFile(join(root, 'state.json'), 'utf8'))
        assert.equal(state.resumed, resume)
        assert.equal(state.status, 'idle')
        const names = model.requests[0].tools.map(t => t.name)
        assert.deepEqual(names.sort(), [...LEAD_TOOL_NAMES, 'native_shell'].sort())
        const text = JSON.stringify(model.requests[0].messages)
        assert.equal(text.includes('fresh'), resume)
      } finally { await ctx.fiber.dispose() }
    }
  } finally {
    for (const key of Object.keys(process.env)) if (!(key in saved)) delete process.env[key]
    Object.assign(process.env, saved)
    await rm(root, { recursive: true, force: true })
  }
})

test('V2 campaign history migrates to V3 without changing the original log', async () => {
  const root = await mkdtemp(join(tmpdir(), 'simjecture-dsh-migration-'))
  const directory = join(root, '_no-cwd', 'legacy')
  await mkdir(directory, { recursive: true })
  const source = join(directory, 'session.v2.jsonl')
  const rows = [
    { type: 'turn/start', data: { turn: 1 } },
    { type: 'step/start', data: { turn: 1, step: 1 } },
    { type: 'user/message', surfaceOp: 'append', data: { id: 'question', role: 'user', source: { kind: 'user' }, content: [{ type: 'text', text: 'old campaign' }] } },
    { type: 'request/header', data: { header: { config: { provider: 'test', model: 'scripted' }, system: 'original scientist persona' }, reason: 'change' } },
    { type: 'step/end', data: { turn: 1, step: 1 } },
    { type: 'turn/end', data: { turn: 1, reason: { kind: 'completed' } } },
  ]
  const original = [
    { type: 'session', version: 2, id: 'legacy', createdAt: 1, isSeeded: false, delegationDepth: 0 },
    ...rows.map((row, seq) => ({ ...row, seq, time: seq + 10 })),
  ].map(row => JSON.stringify(row)).join('\n') + '\n'
  await writeFile(source, original)
  const { ctx } = await runtime([], root)
  try {
    const handle = await ctx.sessionPersistence.open('legacy', 'write')
    assert.equal(handle.header.version, 3)
    const { events } = await handle.read()
    assert.ok(events.some(e => e.type === 'system/message'))
    assert.ok(JSON.stringify(events).includes('original scientist persona'))
    await handle.close()
    assert.equal(await readFile(source, 'utf8'), original)
    assert.equal(JSON.parse((await readFile(join(directory, 'session.v3.jsonl'), 'utf8')).split('\n')[0]).version, 3)
  } finally { await ctx.fiber.dispose(); await rm(root, { recursive: true, force: true }) }
})
