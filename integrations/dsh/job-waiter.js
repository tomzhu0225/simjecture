/**
 * Harness-owned waiting for Simjecture's durable scientific jobs.
 *
 * A model-visible run call still submits exactly one idempotent CampaignKernel
 * job. This around-dispatch middleware then performs small, nested read-only
 * status calls until the kernel reports a terminal receipt and returns that
 * final bounded report as the original call's sole result. Intermediate polls
 * never enter model history.
 */

import { appendFileSync, readFileSync } from 'node:fs'
import { CallId } from '@deepseek-ai/dsh-llm'

export const name = 'simjecture-job-waiter'
export const inject = ['tools']

const MCP = 'mcp__simjecture__'
const STATUS_TOOL = `${MCP}job_status`
const RUN_TOOLS = new Set([
  `${MCP}run_python`,
  `${MCP}run_workbench_capability`,
  `${MCP}run_evidence_capability`,
])
const INTERMEDIATE = new Set(['queued', 'running', 'cancel_requested'])
const TERMINAL = new Set(['succeeded', 'failed', 'cancelled', 'outcome_unknown'])
const POLL_SECONDS = 1
const MAX_READ_RETRIES = 3
const WRITER_BUSY_CODE = 'campaign_writer_busy'

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
    // Activity is a non-authoritative operator projection.
  }
}

function heartbeatSeconds() {
  const parsed = Number(process.env.SIMJECTURE_DSH_JOB_HEARTBEAT_SECONDS ?? '30')
  return Number.isFinite(parsed) && parsed > 0 ? Math.max(1, parsed) : 30
}

function lockBusySeconds() {
  const parsed = Number(process.env.SIMJECTURE_DSH_LOCK_BUSY_SECONDS ?? '15')
  return Number.isFinite(parsed) && parsed > 0 ? Math.max(1, parsed) : 15
}

function pausePending() {
  const path = process.env.SIMJECTURE_DSH_CONTROL_FILE
  if (path === undefined || path === '') return false
  try {
    return JSON.parse(readFileSync(path, 'utf8'))?.command === 'pause'
  } catch {
    return false
  }
}

function structuredContent(result) {
  if (result.isError) return undefined
  const value = result.value
  if (
    typeof value === 'object'
    && value !== null
    && !Array.isArray(value)
    && typeof value.structuredContent === 'object'
    && value.structuredContent !== null
    && !Array.isArray(value.structuredContent)
  ) {
    return value.structuredContent
  }
  return undefined
}

function jobState(result) {
  const value = structuredContent(result)
  const jobId = typeof value?.job_id === 'string' ? value.job_id : undefined
  const status = typeof value?.status === 'string' ? value.status : undefined
  return { jobId, status }
}

function boundedFailure(result) {
  if (!result.isError) return undefined
  const structured = structuredContent(result)
  const envelope = typeof structured?.error === 'object' && structured.error !== null
    ? structured.error
    : undefined
  const code = typeof result.error?.code === 'string'
    ? result.error.code
    : typeof envelope?.code === 'string'
      ? envelope.code
      : undefined
  const message = typeof result.error?.message === 'string'
    ? result.error.message.slice(0, 500)
    : typeof envelope?.message === 'string'
      ? envelope.message.slice(0, 500)
      : undefined
  return { code, message }
}

function writerLockBusy(result) {
  const failure = boundedFailure(result)
  if (failure?.code?.toLowerCase() === WRITER_BUSY_CODE) return true
  const message = failure?.message ?? ''
  // Older Simjecture MCP bundles expose only the exception text. Retain this
  // compatibility fallback while preferring the stable code above.
  return message.includes('campaign writer lock is held')
}

function abortError(signal) {
  if (signal.reason instanceof Error) return signal.reason
  return new Error('scientific job wait aborted; the durable job remains attached to the campaign')
}

function delay(milliseconds, signal) {
  if (signal.aborted) return Promise.reject(abortError(signal))
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      signal.removeEventListener('abort', onAbort)
      resolve()
    }, milliseconds)
    const onAbort = () => {
      clearTimeout(timer)
      signal.removeEventListener('abort', onAbort)
      reject(abortError(signal))
    }
    signal.addEventListener('abort', onAbort, { once: true })
  })
}

async function statusCall(ctx, exec, jobId, report, serial) {
  return ctx.tools.execute({
    callId: CallId(`${String(exec.callId)}:job-wait:${serial}`),
    rootCallId: exec.rootCallId,
    name: STATUS_TOOL,
    arguments: { job_id: jobId, report },
    signal: exec.signal,
    parent: exec.token,
  })
}

async function readStatus(ctx, exec, jobId, serialRef, report) {
  let result
  for (let attempt = 1; attempt <= MAX_READ_RETRIES; attempt += 1) {
    serialRef.value += 1
    result = await statusCall(ctx, exec, jobId, report, serialRef.value)
    if (!result.isError || attempt === MAX_READ_RETRIES) return result
    await delay(250 * (2 ** (attempt - 1)), exec.signal)
  }
  return result
}

async function waitForTerminal(ctx, exec, initial, toolName) {
  const initialState = jobState(initial)
  if (initialState.jobId === undefined || initialState.status === undefined) {
    throw new Error(`${toolName} returned no durable job id and lifecycle status`)
  }
  if (!INTERMEDIATE.has(initialState.status) && !TERMINAL.has(initialState.status)) {
    throw new Error(`${toolName} returned unknown job status ${initialState.status}`)
  }

  const jobId = initialState.jobId
  const started = Date.now()
  const serial = { value: 0 }
  let polls = 0
  let status = initialState.status
  let lastProjected = 0
  let lastStatus
  let lockBusyStarted
  if (!TERMINAL.has(status)) {
    appendActivity({
      kind: 'job',
      status: 'waiting',
      job_id: jobId,
      tool: toolName,
      poll_count: polls,
    })
  }

  try {
    while (!TERMINAL.has(status)) {
      await delay(POLL_SECONDS * 1000, exec.signal)
      const result = await readStatus(ctx, exec, jobId, serial, false)
      polls += 1
      if (result.isError) {
        if (writerLockBusy(result)) {
          lockBusyStarted ??= Date.now()
          if ((Date.now() - lockBusyStarted) / 1000 < lockBusySeconds()) continue
        } else {
          lockBusyStarted = undefined
        }
        const failure = boundedFailure(result)
        appendActivity({
          kind: 'job',
          status: 'wait_failed',
          job_id: jobId,
          tool: toolName,
          poll_count: polls,
          wait_elapsed_seconds: (Date.now() - started) / 1000,
          error_code: failure?.code,
          error: failure?.message,
        })
        return result
      }
      lockBusyStarted = undefined
      const observed = jobState(result)
      if (observed.jobId !== jobId || observed.status === undefined) {
        throw new Error('job_status returned a mismatched or malformed durable state')
      }
      if (!INTERMEDIATE.has(observed.status) && !TERMINAL.has(observed.status)) {
        throw new Error(`job_status returned unknown status ${observed.status}`)
      }
      status = observed.status
      const elapsed = (Date.now() - started) / 1000
      if (
        status !== lastStatus
        || elapsed - lastProjected >= heartbeatSeconds()
        || TERMINAL.has(status)
      ) {
        appendActivity({
          kind: 'job',
          status,
          job_id: jobId,
          tool: toolName,
          poll_count: polls,
          wait_elapsed_seconds: elapsed,
          pause_pending: pausePending(),
        })
        lastProjected = elapsed
        lastStatus = status
      }
    }

    // The small terminal state is authoritative, but the model receives one
    // bounded report containing diagnostics and the authenticated worker
    // receipt. A failure here is returned as a tool error, never guessed.
    const lockBusyDeadline = Date.now() + lockBusySeconds() * 1000
    let detailed
    do {
      detailed = await readStatus(ctx, exec, jobId, serial, true)
      if (!writerLockBusy(detailed) || Date.now() >= lockBusyDeadline) break
      await delay(POLL_SECONDS * 1000, exec.signal)
    } while (true)
    if (detailed.isError) {
      const failure = boundedFailure(detailed)
      appendActivity({
        kind: 'job',
        status: 'wait_failed',
        job_id: jobId,
        tool: toolName,
        poll_count: polls,
        wait_elapsed_seconds: (Date.now() - started) / 1000,
        error_code: failure?.code,
        error: failure?.message,
      })
      return detailed
    }
    const terminal = jobState(detailed)
    if (terminal.jobId !== jobId || !TERMINAL.has(terminal.status)) {
      throw new Error('terminal job report did not preserve the reconciled lifecycle state')
    }
    // The polling loop already projected a terminal transition. Avoid showing
    // it twice merely because we subsequently fetched the detailed report.
    // An immediately-terminal submission has not been projected yet, so it
    // still receives one terminal activity event here.
    if (lastStatus !== terminal.status) {
      appendActivity({
        kind: 'job',
        status: terminal.status,
        job_id: jobId,
        tool: toolName,
        poll_count: polls,
        wait_elapsed_seconds: (Date.now() - started) / 1000,
      })
    }
    return detailed
  } catch (error) {
    if (exec.signal.aborted) {
      appendActivity({
        kind: 'job',
        status: 'detached',
        job_id: jobId,
        tool: toolName,
        poll_count: polls,
        wait_elapsed_seconds: (Date.now() - started) / 1000,
      })
    }
    throw error
  }
}

export function apply(ctx) {
  ctx.on('tools/execute', async (exec, next) => {
    // Nested calls are the waiter's own reads or another composite's private
    // operation. Only a model-direct scientific job call owns waiting.
    if (
      exec.agent === undefined
      || exec.parent !== undefined
      || (!RUN_TOOLS.has(exec.name) && exec.name !== STATUS_TOOL)
    ) {
      return next()
    }
    const initial = await next()
    if (initial.isError) return initial
    return waitForTerminal(ctx, exec, initial, exec.name)
  })
}
