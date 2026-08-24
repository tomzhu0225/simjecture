/**
 * Resumable one-campaign DSH driver for Simjecture.
 *
 * DSH still owns model routing, retry, compaction, and event-sourced history.
 * This driver only supplies a stable session identity, a bounded operator
 * projection, and one autonomous follow-up turn per supervised invocation.
 */

import { appendFileSync, readFileSync, renameSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { installModelSelection } from '@deepseek-ai/dsh-agent'
import { createUserMessage } from '@deepseek-ai/dsh-llm'
import { SessionId } from '@deepseek-ai/dsh-session'
import { LEAD_TOOL_NAMES } from './roles.js'

export const name = 'simjecture-runner'
export const inject = ['agentDefaultModel', 'agents', 'sessions', 'tools']

const SESSION_ID = /^[A-Za-z][A-Za-z0-9_.-]{0,127}$/

function requiredEnvironment(name) {
  const value = process.env[name]
  if (value === undefined || value === '') throw new Error(`${name} is required`)
  return value
}

function now() {
  return new Date().toISOString()
}

function atomicJson(path, payload) {
  const temporary = resolve(dirname(path), `.${path.split('/').at(-1)}.${process.pid}.tmp`)
  writeFileSync(temporary, `${JSON.stringify(payload, null, 2)}\n`, { encoding: 'utf8', mode: 0o600 })
  renameSync(temporary, path)
}

function appendActivity(path, payload) {
  try {
    appendFileSync(path, `${JSON.stringify({ schema_version: '0.1.0', ...payload })}\n`, {
      encoding: 'utf8',
      mode: 0o600,
    })
  } catch {
    // The authoritative DSH session and Simjecture campaign must survive a
    // non-authoritative operator projection failure.
  }
}

function controlRequestsPause(path) {
  try {
    const payload = JSON.parse(readFileSync(path, 'utf8'))
    return payload?.command === 'pause'
  } catch {
    return false
  }
}

function projectedEvent(event) {
  const base = {
    sequence: event.seq,
    observed_at: new Date(event.time).toISOString(),
    event_type: event.type,
  }
  if (event.type === 'turn/start') return { ...base, kind: 'turn', status: 'started', turn: event.data.turn }
  if (event.type === 'turn/end') {
    return { ...base, kind: 'turn', status: event.data.reason.kind, turn: event.data.turn }
  }
  if (event.type === 'step/start') {
    return { ...base, kind: 'model', status: 'running', turn: event.data.turn, step: event.data.step }
  }
  if (event.type === 'step/end') {
    return { ...base, kind: 'model', status: 'idle', turn: event.data.turn, step: event.data.step }
  }
  if (event.type === 'tool/call') {
    return {
      ...base,
      kind: 'tool',
      status: 'running',
      turn: event.data.turn,
      step: event.data.step,
      tool: event.data.name,
      call_id: event.data.callId,
    }
  }
  if (event.type === 'tool/result') {
    const resultBlock = (event.data.message.content ?? [])
      .find(block => block.type === 'tool-result')
    const failed = event.data.error !== undefined || resultBlock?.isError === true
    return {
      ...base,
      kind: 'tool',
      status: failed ? 'failed' : 'succeeded',
      turn: event.data.turn,
      step: event.data.step,
      call_id: event.data.message.source.callId,
      error_code: event.data.error?.code,
    }
  }
  if (event.type === 'assistant/message') {
    const usage = event.data.usage
    return {
      ...base,
      kind: 'model',
      status: event.data.interrupted === true ? 'interrupted' : 'responded',
      turn: event.data.turn,
      step: event.data.step,
      usage: usage === undefined ? undefined : usage,
    }
  }
  if (event.type === 'llm/retry' || event.type === 'llm/retry-started') {
    return {
      ...base,
      kind: 'retry',
      status: event.type === 'llm/retry' ? 'waiting' : 'running',
      turn: event.data.turn,
      step: event.data.step,
      retry: event.data.retry,
      delay_ms: event.data.delayMs,
      failure_code: event.data.failure?.code,
    }
  }
  if (event.type === 'compaction/start') {
    return { ...base, kind: 'compaction', status: 'running', compaction_id: event.data.compactionId }
  }
  if (event.type === 'compaction/summary') {
    return {
      ...base,
      kind: 'compaction',
      status: 'summarized',
      compaction_id: event.data.compactionId,
      shadowed_nodes: event.data.shadowedSeqs.length,
      shadowed_tokens: event.data.shadowedTokenCount,
      provider: event.data.provider,
      model: event.data.model,
      max_tokens: event.data.maxTokens,
      usage: event.data.usage,
    }
  }
  if (event.type === 'compaction/end') {
    const rawError = event.data.error
    const error = typeof rawError === 'string'
      ? rawError.slice(0, 500)
      : typeof rawError?.message === 'string'
        ? rawError.message.slice(0, 500)
        : undefined
    return {
      ...base,
      kind: 'compaction',
      status: rawError === undefined ? 'succeeded' : 'failed',
      compaction_id: event.data.compactionId,
      error,
    }
  }
  if (event.type === 'compaction/prune') {
    return {
      ...base,
      kind: 'compaction',
      status: 'pruned',
      shadowed_nodes: event.data.shadowedSeqs.length,
      shadowed_tokens: event.data.shadowedTokenCount,
    }
  }
  if (event.type === 'request/context') {
    return {
      ...base,
      kind: 'route',
      status: 'selected',
      provider: event.data.provider,
      model: event.data.model,
      context_window: event.data.contextWindow,
    }
  }
  return undefined
}

function summarize(events, firstSeq) {
  let started = false
  let text = ''
  let reason
  for (const event of events) {
    if (event.seq < firstSeq) continue
    if (event.type === 'turn/start') {
      started = true
      continue
    }
    if (!started) continue
    if (event.type === 'assistant/message') {
      const joined = event.data.message.content
        .filter(block => block.type === 'text')
        .map(block => block.text)
        .join('')
      if (joined !== '') text = joined
    }
    if (event.type === 'turn/end') reason = event.data.reason
  }
  return { text, reason }
}

function isMissingSession(error, sessionId) {
  const message = error instanceof Error ? error.message : String(error)
  return message === `session "${sessionId}" not found`
}

async function drive(ctx, task, io) {
  await ctx.get('loader')?.await()
  const agents = ctx.get('agents')
  const defaultModel = ctx.get('agentDefaultModel')
  const sessions = ctx.get('sessions')
  if (agents === undefined || defaultModel === undefined || sessions === undefined) return

  const rawSessionId = requiredEnvironment('SIMJECTURE_DSH_SESSION_ID')
  if (!SESSION_ID.test(rawSessionId)) throw new Error('SIMJECTURE_DSH_SESSION_ID is invalid')
  const sessionId = SessionId(rawSessionId)
  const activityPath = requiredEnvironment('SIMJECTURE_DSH_ACTIVITY_FILE')
  const statePath = requiredEnvironment('SIMJECTURE_DSH_STATE_FILE')
  const controlPath = requiredEnvironment('SIMJECTURE_DSH_CONTROL_FILE')
  const resumeRequested = process.env.SIMJECTURE_DSH_RESUME === '1'
  const selection = defaultModel.currentSelection()
  const setup = (agentCtx) => {
    const selected = { current: selection, assembled: undefined }
    installModelSelection(agentCtx, selected)
    // The persistent agent is a compact coordinator, not another experiment
    // worker. Fresh scoped roles own scientific mutation and execution; the
    // lead sees only durable state, delegation, adjudication, and finalization.
    agentCtx.tools.restrict({ allow: [...LEAD_TOOL_NAMES] })
  }

  let resumed = false
  let recoveredFresh = false
  let handle
  if (resumeRequested) {
    try {
      handle = await agents.resume({
        resumeSessionId: sessionId,
        agentOptions: { provider: selection.provider, model: selection.model },
        setup,
      })
      resumed = true
    } catch (error) {
      if (!isMissingSession(error, rawSessionId)) throw error
      handle = await agents.create({
        sessionId,
        meta: { cwd: process.cwd() },
        agentOptions: { provider: selection.provider, model: selection.model },
        setup,
      })
      recoveredFresh = true
    }
  } else {
    handle = await agents.create({
      sessionId,
      meta: { cwd: process.cwd() },
      agentOptions: { provider: selection.provider, model: selection.model },
      setup,
    })
  }

  const { agent } = handle
  let pauseHonored = false
  const disposeEvents = ctx.on('session/event', (session, event) => {
    if (session === agent.session) {
      const projection = projectedEvent(event)
      if (projection !== undefined) appendActivity(activityPath, projection)
    }
    // Scientific work runs inside scoped child roles. Their completed tools
    // are action boundaries too: waiting only for a lead-scientist tool result
    // can leave a requested pause pending for an entire long-running role.
    // Cancelling the lead propagates through that role tool's abort signal,
    // while keepInbox preserves the persistent session for resume.
    if (
      !pauseHonored
      && event.type === 'tool/result'
      && controlRequestsPause(controlPath)
    ) {
      pauseHonored = true
      atomicJson(statePath, {
        schema_version: '0.1.0',
        status: 'paused',
        engine: 'dsh',
        session_id: rawSessionId,
        boundary_session_id: String(session.id),
        boundary_sequence: event.seq,
        updated_at: now(),
      })
      agent.cancel({ kind: 'user' }, { keepInbox: true })
    }
  })
  const disposeStatus = ctx.on('agent/status', ({ agent: subject, status }) => {
    if (subject !== agent) return
    appendActivity(activityPath, {
      observed_at: now(),
      kind: 'agent',
      status,
      role: 'lead_scientist',
    })
  })

  appendActivity(activityPath, {
    observed_at: now(),
    kind: 'session',
    status: resumed ? 'resumed' : recoveredFresh ? 'recovered_fresh' : 'created',
    session_id: rawSessionId,
  })
  atomicJson(statePath, {
    schema_version: '0.1.0',
    status: 'running',
    engine: 'dsh',
    session_id: rawSessionId,
    resumed,
    recovered_fresh: recoveredFresh,
    provider: selection.provider,
    model: selection.model,
    updated_at: now(),
  })

  await agent.whenIdle()
  const firstSeq = agent.session.seq
  agent.followup(createUserMessage({
    content: [{ type: 'text', text: task }],
    source: { kind: 'user' },
  }))
  await agent.whenIdle()
  await sessions.flush(agent.session)
  if (!pauseHonored && controlRequestsPause(controlPath)) pauseHonored = true
  const outcome = summarize(agent.session.events, firstSeq)
  atomicJson(statePath, {
    schema_version: '0.1.0',
    status: pauseHonored ? 'paused' : 'idle',
    engine: 'dsh',
    session_id: rawSessionId,
    resumed,
    recovered_fresh: recoveredFresh,
    turn_reason: outcome.reason?.kind,
    updated_at: now(),
  })
  disposeStatus()
  disposeEvents()
  if (outcome.text !== '') io.stdout.write(`${outcome.text}\n`)
  if (outcome.reason?.kind === 'error') {
    io.stderr.write(`dsh: ${outcome.reason.error.code}: ${outcome.reason.error.message}\n`)
  }
  io.exit(pauseHonored || outcome.reason?.kind === 'completed' ? 0 : 1)
}

export function apply(ctx, config) {
  const exit = ctx.get('appExit')
  if (exit === undefined) throw new Error('simjecture-runner requires the DSH launcher appExit service')
  const io = { stdout: process.stdout, stderr: process.stderr, exit }
  void drive(ctx, config.task, io).catch((error) => {
    const statePath = process.env.SIMJECTURE_DSH_STATE_FILE
    if (statePath !== undefined && statePath !== '') {
      try {
        atomicJson(statePath, {
          schema_version: '0.1.0',
          status: 'failed',
          engine: 'dsh',
          session_id: process.env.SIMJECTURE_DSH_SESSION_ID,
          error: error instanceof Error ? error.message : String(error),
          updated_at: now(),
        })
      } catch {}
    }
    io.stderr.write(`dsh: ${error instanceof Error ? error.message : String(error)}\n`)
    io.exit(1)
  })
}
