/**
 * Replay-safe, model-free context elision for completed Simjecture tools.
 *
 * Every result remains verbatim for one model request. On a later request,
 * large results use DSH's supported content-only rewrite. Fully completed,
 * balanced execution units may instead become one deterministic receipt,
 * removing both bulky arguments and results from the model surface while the
 * append-only session retains every original event byte.
 */

import { createHash } from 'node:crypto'
import { appendFileSync } from 'node:fs'
import { createUserMessage, freezeMessage } from '@deepseek-ai/dsh-llm'

export const name = 'simjecture-context-elider'
export const inject = ['tokenMeter', 'toolResultPruner', 'tools']

const COLLAPSIBLE_TOOLS = new Set([
  'mcp__simjecture__write_workspace_file',
  'mcp__simjecture__run_python',
  'mcp__simjecture__run_workbench_capability',
  'mcp__simjecture__run_evidence_capability',
])
const RUN_TOOLS = new Set([
  'mcp__simjecture__run_python',
  'mcp__simjecture__run_workbench_capability',
  'mcp__simjecture__run_evidence_capability',
])
const RETAINED_KEYS = new Set([
  'operation_id',
  'active_claim_id',
  'claim_id',
  'path',
  'program_path',
  'program_sha256',
  'sha256',
  'capability',
  'stage',
  'job_id',
  'status',
  'returncode',
  'timed_out',
  'evidence_eligible',
])
const ARGUMENT_THRESHOLD_CHARS = 2_000
const MAX_VISIBLE_TEXT_CHARS = 2_000

function now() {
  return new Date().toISOString()
}

function appendActivity(payload) {
  const path = process.env.SIMJECTURE_DSH_ACTIVITY_FILE
  if (path === undefined || path === '') return
  try {
    appendFileSync(path, `${JSON.stringify({
      schema_version: '0.1.0',
      observed_at: now(),
      ...payload,
    })}\n`, { encoding: 'utf8', mode: 0o600 })
  } catch {
    // Non-authoritative projection only.
  }
}

function sha256(text) {
  return createHash('sha256').update(text).digest('hex')
}

function boundedText(text, maximum = MAX_VISIBLE_TEXT_CHARS) {
  if (text.length <= maximum) return text
  const half = Math.floor((maximum - 42) / 2)
  return `${text.slice(0, half)}\n[... text elided ...]\n${text.slice(-half)}`
}

function textContent(blocks) {
  let text = ''
  for (const block of blocks ?? []) {
    if (block?.type === 'text' && typeof block.text === 'string') text += block.text
  }
  return text
}

function toolResultBlock(event) {
  return event?.type === 'tool/result' ? event.data.message.content?.[0] : undefined
}

function toolResultText(event) {
  return textContent(toolResultBlock(event)?.content)
}

function resultCallId(event) {
  const block = toolResultBlock(event)
  return typeof block?.toolCallId === 'string'
    ? block.toolCallId
    : event?.data?.message?.source?.callId
}

function selectedScalars(value, output = {}, depth = 0) {
  if (depth > 8 || value === null || typeof value !== 'object') return output
  if (Array.isArray(value)) {
    for (const item of value.slice(0, 30)) selectedScalars(item, output, depth + 1)
    return output
  }
  for (const [key, item] of Object.entries(value)) {
    if (
      RETAINED_KEYS.has(key)
      && (typeof item === 'string' || typeof item === 'number' || typeof item === 'boolean')
      && String(item).length <= 240
      && output[key] === undefined
    ) {
      output[key] = item
    } else if (typeof item === 'object' && item !== null) {
      selectedScalars(item, output, depth + 1)
    }
  }
  return output
}

function parseObject(text) {
  try {
    const value = JSON.parse(text)
    return typeof value === 'object' && value !== null ? value : undefined
  } catch {
    return undefined
  }
}

function currentSurfaceEvents(session) {
  return [...session.surface.nodes].map(seq => session.events[seq])
}

function completedUnits(session) {
  const events = currentSurfaceEvents(session)
  const units = []
  for (let index = 0; index < events.length; index += 1) {
    const assistant = events[index]
    if (assistant?.type !== 'assistant/message') continue
    const calls = assistant.data.message.content.filter(block => block.type === 'tool-call')
    if (
      calls.length === 0
      || calls.some(call => !COLLAPSIBLE_TOOLS.has(call.name))
      || calls.every(call => call.arguments.length <= ARGUMENT_THRESHOLD_CHARS)
    ) {
      continue
    }
    const expected = new Map(calls.map(call => [String(call.id), call]))
    const results = []
    let cursor = index + 1
    while (cursor < events.length && events[cursor]?.type === 'tool/result') {
      const event = events[cursor]
      const callId = String(resultCallId(event))
      if (!expected.has(callId) || toolResultBlock(event)?.isError === true) break
      results.push(event)
      expected.delete(callId)
      cursor += 1
    }
    if (expected.size !== 0 || results.length !== calls.length) continue

    let durable = true
    for (const call of calls) {
      const result = results.find(event => String(resultCallId(event)) === String(call.id))
      const text = toolResultText(result)
      if (RUN_TOOLS.has(call.name) && !/"status"\s*:\s*"succeeded"/.test(text)) durable = false
      if (
        call.name === 'mcp__simjecture__write_workspace_file'
        && !/("sha256"|"path"|"accepted")/.test(text)
      ) {
        durable = false
      }
    }
    if (!durable) continue
    units.push({
      key: `unit:${assistant.seq}:${results.at(-1).seq}`,
      assistant,
      calls,
      results,
      shadowed: [assistant, ...results],
    })
    index = cursor - 1
  }
  return units
}

function receiptFor(unit) {
  const visibleText = unit.assistant.data.message.content
    .filter(block => block.type === 'text')
    .map(block => block.text)
    .join('')
  const calls = unit.calls.map(call => {
    const result = unit.results.find(event => String(resultCallId(event)) === String(call.id))
    const resultText = toolResultText(result)
    return {
      call_id: String(call.id),
      tool: call.name,
      arguments: {
        chars: call.arguments.length,
        sha256: sha256(call.arguments),
        retained: selectedScalars(parseObject(call.arguments)),
      },
      result: {
        chars: resultText.length,
        sha256: sha256(resultText),
        retained: selectedScalars(parseObject(resultText)),
      },
    }
  })
  return createUserMessage({
    content: [{
      type: 'text',
      text: [
        '<simjecture-completed-tool-receipt>',
        JSON.stringify({
          note: 'Full arguments and results remain in the append-only DSH log and durable Simjecture stores.',
          assistant_text: boundedText(visibleText),
          calls,
        }),
        '</simjecture-completed-tool-receipt>',
      ].join('\n'),
    }],
    source: { kind: 'user' },
  })
}

function shadowPrice(ctx, events) {
  return events.reduce((total, event) => {
    const message = event.type === 'assistant/message'
      ? event.data.message
      : event.type === 'tool/result'
        ? event.data.message
        : event.data
    return total + ctx.tokenMeter.estimateMessage(message)
  }, 0)
}

function collapseUnit(ctx, session, unit) {
  const first = unit.shadowed[0].seq
  const last = unit.shadowed.at(-1).seq
  const seqs = unit.shadowed.map(event => event.seq)
  session.append('compaction/prune', {
    shadowedRange: { start: first, end: last },
    shadowedSeqs: seqs,
    shadowedTokenCount: shadowPrice(ctx, unit.shadowed),
  })
  const replacement = session.append(
    'user/message',
    receiptFor(unit),
    {
      surfaceOp: { op: 'replace', start: first, end: last },
      sourceEventSeqs: seqs,
    },
  )
  appendActivity({
    kind: 'context',
    status: 'elided',
    elision: 'completed_tool_unit',
    original_nodes: seqs.length,
    replacement_sequence: replacement.seq,
    tools: unit.calls.map(call => call.name),
    argument_chars: unit.calls.reduce((total, call) => total + call.arguments.length, 0),
    result_chars: unit.results.reduce((total, event) => total + toolResultText(event).length, 0),
  })
}

function oversizedResults(ctx, session) {
  const candidates = []
  for (const event of currentSurfaceEvents(session)) {
    if (event?.type !== 'tool/result') continue
    const result = toolResultBlock(event)
    if (ctx.toolResultPruner.pruneContent(result.content) !== null) {
      candidates.push({ key: `result:${event.seq}`, event })
    }
  }
  return candidates
}

function pruneResult(ctx, session, event) {
  const result = toolResultBlock(event)
  const content = ctx.toolResultPruner.pruneContent(result.content)
  if (content === null) return
  const message = freezeMessage({
    ...event.data.message,
    content: [{ ...result, content }],
  })
  session.append('compaction/prune', {
    shadowedRange: { start: event.seq, end: event.seq },
    shadowedSeqs: [event.seq],
    shadowedTokenCount: ctx.tokenMeter.estimateMessage(event.data.message),
  })
  const replacement = session.append(
    'tool/result',
    { ...event.data, message },
    {
      surfaceOp: { op: 'replace', start: event.seq, end: event.seq },
      sourceEventSeqs: [event.seq],
    },
  )
  appendActivity({
    kind: 'context',
    status: 'elided',
    elision: 'large_tool_result',
    call_id: event.data.message.source.callId,
    original_sequence: event.seq,
    replacement_sequence: replacement.seq,
    result_chars: toolResultText(event).length,
  })
}

export function apply(ctx) {
  const states = new WeakMap()
  ctx.on('agent/pre-step', async ({ agent, signal }, next) => {
    if (!signal.aborted) {
      const state = states.get(agent.session) ?? { tick: 0, firstSeen: new Map() }
      state.tick += 1
      states.set(agent.session, state)
      try {
        for (const unit of completedUnits(agent.session)) {
          const first = state.firstSeen.get(unit.key)
          if (first === undefined) state.firstSeen.set(unit.key, state.tick)
          else if (first < state.tick) collapseUnit(ctx, agent.session, unit)
        }
        for (const candidate of oversizedResults(ctx, agent.session)) {
          const first = state.firstSeen.get(candidate.key)
          if (first === undefined) state.firstSeen.set(candidate.key, state.tick)
          else if (first < state.tick) pruneResult(ctx, agent.session, candidate.event)
        }

        const live = new Set([
          ...completedUnits(agent.session).map(unit => unit.key),
          ...oversizedResults(ctx, agent.session).map(candidate => candidate.key),
        ])
        for (const key of state.firstSeen.keys()) {
          if (!live.has(key)) state.firstSeen.delete(key)
        }
      } catch (error) {
        ctx.logger.warn(
          `Simjecture context elision failed; preserving the original surface: ${error instanceof Error ? error.message : String(error)}`,
        )
      }
    }
    return next()
  }, { prepend: true })
}
