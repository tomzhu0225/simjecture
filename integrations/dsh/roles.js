/**
 * Fresh, claim-scoped scientific workers for the Simjecture DSH profile.
 *
 * The durable root agent is only a lead scientist.  Each falsification or
 * repair assignment starts from CampaignKernel state in a new DSH session,
 * returns one schema-bounded handoff, and is then disposed.  A name filter
 * limits each role's tool surface; a child-scoped guard additionally limits
 * mutating calls to the assigned claim and commissioning claims created by
 * that worker.
 */

import { appendFileSync } from 'node:fs'
import { CallId } from '@deepseek-ai/dsh-llm'

export const name = 'simjecture-roles'
export const inject = ['agents', 'subagents', 'tools']

const MCP = 'mcp__simjecture__'

export const LEAD_TOOL_NAMES = Object.freeze([
  `${MCP}snapshot`,
  `${MCP}claims`,
  'simjecture_falsify',
  'simjecture_repair',
  'simjecture_adjudicate',
  `${MCP}finalize_campaign`,
])

export const FALSIFIER_TOOL_NAMES = Object.freeze([
  `${MCP}snapshot`,
  `${MCP}claims`,
  `${MCP}list_skills`,
  `${MCP}read_skill`,
  `${MCP}materialize_skill`,
  `${MCP}search_literature`,
  `${MCP}read_workspace_file`,
  `${MCP}write_workspace_file`,
  `${MCP}list_workspace_files`,
  `${MCP}register_claim`,
  `${MCP}register_evidence_contract`,
  `${MCP}link_claim_evidence`,
  `${MCP}close_claim`,
  `${MCP}run_python`,
  `${MCP}run_workbench_capability`,
  `${MCP}run_evidence_capability`,
  `${MCP}job_status`,
  `${MCP}cancel_job`,
])

export const REPAIR_TOOL_NAMES = Object.freeze([
  `${MCP}snapshot`,
  `${MCP}claims`,
  `${MCP}list_skills`,
  `${MCP}read_skill`,
  `${MCP}search_literature`,
  `${MCP}read_workspace_file`,
  `${MCP}list_workspace_files`,
  `${MCP}register_claim`,
  `${MCP}register_evidence_contract`,
])

export const FALSIFIER_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  properties: {
    assignment_id: { type: 'string' },
    claim_id: { type: 'string' },
    outcome: {
      type: 'string',
      enum: ['falsified', 'ready_for_adjudication', 'inconclusive', 'blocked'],
    },
    contract_version: { oneOf: [{ type: 'integer' }, { type: 'null' }] },
    decisive_evidence_paths: { type: 'array', items: { type: 'string' } },
    counterexample_summary: { oneOf: [{ type: 'string' }, { type: 'null' }] },
    case_for_sufficiency: { oneOf: [{ type: 'string' }, { type: 'null' }] },
    evidence_gaps: { type: 'array', items: { type: 'string' } },
    next_test: { oneOf: [{ type: 'string' }, { type: 'null' }] },
  },
  required: [
    'assignment_id',
    'claim_id',
    'outcome',
    'contract_version',
    'decisive_evidence_paths',
    'counterexample_summary',
    'case_for_sufficiency',
    'evidence_gaps',
    'next_test',
  ],
}

export const REPAIR_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  properties: {
    assignment_id: { type: 'string' },
    parent_claim_id: { type: 'string' },
    outcome: { type: 'string', enum: ['registered', 'reused', 'blocked'] },
    child_claim_id: { oneOf: [{ type: 'string' }, { type: 'null' }] },
    contract_version: { oneOf: [{ type: 'integer' }, { type: 'null' }] },
    statement: { oneOf: [{ type: 'string' }, { type: 'null' }] },
    falsification_strategy: { oneOf: [{ type: 'string' }, { type: 'null' }] },
    evidence_gaps: { type: 'array', items: { type: 'string' } },
  },
  required: [
    'assignment_id',
    'parent_claim_id',
    'outcome',
    'child_claim_id',
    'contract_version',
    'statement',
    'falsification_strategy',
    'evidence_gaps',
  ],
}

const FALSIFIER_PERSONA = `You are the fresh Falsifier/Experimenter for one
claim in a falsification-first computational-science campaign. You have no
parent conversation. Your first action must be snapshot; reconcile it with the
assignment packet before any mutation. Then call claims with view=role and
claim_ids containing only the assigned claim; never request an unscoped full
ledger. Work only on the assigned scientific
claim and on non-scientific commissioning claims you create beneath it. Search
relevant literature when available, inspect installed skills, register a
prospective evidence contract before observations, commission unfamiliar
capabilities, and run the smallest discriminating tests first. Durable jobs are
waited by the harness; do not repeatedly poll them. Link only qualifying
artifacts. Inspect source with read_workspace_file line windows; never use
run_python merely to print or slice a file, and do not reread overlapping
windows. Plain run_python is not a named capability: omit execution bindings
and commissioning-only aspect labels from its ordinary scientific contract.
When evidence_gaps or next_test are present, this is a follow-up:
reuse the durable contract, evidence, and workspace artifacts, address those
gaps directly, and do not repeat literature/skill discovery or unrelated
commissioning unless the requested test truly depends on it. Prefer a focused
extension or small new script over rewriting an existing artifact, and keep
tool arguments bounded. Set observation_sufficient=true when an artifact meets
the active contract; that records contract compliance and does not declare
scientific support. You may close the assigned scientific claim only as
falsified when a contracted counterexample is accepted by the kernel. Never
declare scientific
support and never create a repaired scientific hypothesis. If a meaningful
counterexample search survives, return a bounded case for the independent
judge. Keep working until one declared outcome is true or a durable blocker is
reached. Use operation IDs beginning with the assignment id. End only through
the required structured output; do not expose private chain-of-thought.`

const REPAIR_PERSONA = `You are the fresh Repair Scientist for one falsified
scientific claim. You have no parent conversation. Your first action must be
snapshot; reconcile it with the assignment packet before any mutation. Then
call claims with view=role and claim_ids containing only the assigned parent;
never request an unscoped full ledger. Read
the decisive counterexample and create or reuse exactly one minimal scientific
child with relation=repairs that accommodates that evidence, changes the
parent statement semantically, and makes a new falsifiable prediction. Register
its prospective evidence contract. Do not run simulations, link evidence,
close claims, adjudicate, or finalize; the next fresh Falsifier will test the
child. Use operation IDs beginning with the assignment id. End only through the
required structured output; do not expose private chain-of-thought.`

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
    // The authoritative child session and campaign stores survive projection
    // failure; activity is only a bounded operator view.
  }
}

function errorText(result) {
  return result.content
    .filter(block => block.type === 'text')
    .map(block => block.text)
    .join('\n') || 'internal scientific tool failed'
}

function structuredValue(result, name) {
  if (result.isError) throw new Error(errorText(result))
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
  throw new Error(`${name} returned no structured content`)
}

async function internalMcpCall(ctx, exec, suffix, name, args) {
  const result = await ctx.tools.execute({
    callId: CallId(`${String(exec.callId)}:simjecture-role:${suffix}`),
    rootCallId: exec.rootCallId,
    name,
    arguments: args,
    signal: exec.signal,
    parent: exec.token,
  })
  return structuredValue(result, name)
}

function claimsOf(payload) {
  if (payload?.truncated === true || !Array.isArray(payload?.claims)) {
    throw new Error('CampaignKernel returned a truncated or invalid claim ledger')
  }
  return payload.claims
}

function claimById(payload, claimId) {
  const folded = String(claimId).toLowerCase()
  return claimsOf(payload).find(claim => String(claim?.id).toLowerCase() === folded)
}

function contractExists(claim, version) {
  return Number.isInteger(version) && (claim?.evidence_contracts ?? [])
    .some(contract => contract?.version === version)
}

function compactClaim(claim) {
  return {
    id: claim.id,
    statement: claim.statement,
    kind: claim.kind,
    relation: claim.relation,
    parent_id: claim.parent_id,
    status: claim.status,
    rationale: claim.rationale,
    repair: claim.repair,
    decisive_contract_version: claim.decisive_contract_version,
    evidence_contracts: (claim.evidence_contracts ?? []).map(contract => ({
      version: contract.version,
      observable: contract.observable,
      decision_rule: contract.decision_rule,
      required_observation: contract.required_observation,
      uncertainty_criterion: contract.uncertainty_criterion,
      inconclusive_conditions: contract.inconclusive_conditions,
    })),
    evidence: (claim.evidence ?? []).map(evidence => ({
      path: evidence.path,
      contract_version: evidence.contract_version,
      observation_sufficient: evidence.observation_sufficient,
      observation_note: evidence.observation_note,
      commissioning_claim_id: evidence.commissioning_claim_id,
      provenance: evidence.provenance === null || evidence.provenance === undefined
        ? null
        : {
            sha256: evidence.provenance.sha256,
            tracked: evidence.provenance.tracked,
            evidence_eligible: evidence.provenance.evidence_eligible,
            execution_succeeded: evidence.provenance.execution_succeeded,
            operation_id: evidence.provenance.operation_id,
            job_id: evidence.provenance.job_id,
            job_status: evidence.provenance.job_status,
          },
    })),
  }
}

function compactCampaign(snapshot) {
  if (snapshot?.truncated === true || typeof snapshot?.hypothesis !== 'string') {
    throw new Error('CampaignKernel returned a truncated or invalid snapshot')
  }
  return {
    hypothesis: snapshot.hypothesis,
    budget: snapshot.budget,
    jobs: Array.isArray(snapshot.jobs)
      ? snapshot.jobs.map(job => ({
          job_id: job.job_id,
          operation_id: job.operation_id,
          status: job.status,
        }))
      : [],
    skills: Object.keys(snapshot.skill_hashes ?? {}),
    capabilities: Object.keys(snapshot.capability_hashes ?? {}),
  }
}

function rolePacket(snapshot, claim, args, role) {
  const packet = {
    role,
    assignment: args,
    campaign: compactCampaign(snapshot),
    target_claim: compactClaim(claim),
  }
  const encoded = JSON.stringify(packet)
  if (encoded.length > 80_000) {
    throw new Error('role packet exceeds the bounded fresh-session handoff')
  }
  return encoded
}

async function childClaimSummaries(ctx, exec, role, parentId) {
  const claims = []
  let offset = 0
  for (;;) {
    const page = await internalMcpCall(
      ctx,
      exec,
      `${role}:claim-children:${offset}`,
      `${MCP}claims`,
      { view: 'summary', parent_id: parentId, offset, limit: 24 },
    )
    const rows = claimsOf(page)
    claims.push(...rows)
    if (page.has_more !== true) return claims
    if (rows.length === 0) {
      throw new Error('CampaignKernel claim pagination made no progress')
    }
    offset += rows.length
  }
}

function asRecord(value) {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? value
    : {}
}

function claimIdFrom(args) {
  const value = asRecord(args).claim_id
  return typeof value === 'string' ? value.toLowerCase() : undefined
}

function installAssignmentGuard(child, assignment) {
  if (assignment.guardInstalled) return
  assignment.guardInstalled = true
  child.ctx.tools.guard((exec) => {
    const args = asRecord(exec.arguments)
    const claimId = claimIdFrom(args)
    const allowed = assignment.allowedClaims

    if (assignment.role === 'falsifier') {
      if (exec.name === `${MCP}register_claim`) {
        if (args.kind === 'scientific') {
          return 'the Falsifier cannot register scientific claims; delegate repair to the Repair Scientist'
        }
        const parentId = typeof args.parent_id === 'string' ? args.parent_id.toLowerCase() : ''
        if (!allowed.has(parentId)) return 'commissioning claims must descend from the assigned claim'
        return undefined
      }
      if (
        exec.name === `${MCP}register_evidence_contract`
        || exec.name === `${MCP}link_claim_evidence`
      ) {
        if (claimId === undefined || !allowed.has(claimId)) {
          return 'the Falsifier may mutate only its assigned or commissioned claims'
        }
      }
      if (exec.name === `${MCP}close_claim`) {
        if (claimId === undefined || !allowed.has(claimId)) {
          return 'the Falsifier may close only its assigned or commissioned claims'
        }
        if (claimId === assignment.targetId && args.status === 'supported') {
          return 'scientific support requires the independent adjudicator'
        }
      }
      if (
        exec.name === `${MCP}run_python`
        || exec.name === `${MCP}run_workbench_capability`
        || exec.name === `${MCP}run_evidence_capability`
      ) {
        const active = typeof args.active_claim_id === 'string'
          ? args.active_claim_id.toLowerCase()
          : undefined
        if (active !== undefined && !allowed.has(active)) {
          return 'execution must be scoped to the assigned or commissioned claim'
        }
      }
      return undefined
    }

    if (exec.name === `${MCP}register_claim`) {
      const parentId = typeof args.parent_id === 'string' ? args.parent_id.toLowerCase() : ''
      const candidateId = typeof args.claim_id === 'string' ? args.claim_id.toLowerCase() : ''
      if (
        args.kind !== 'scientific'
        || args.relation !== 'repairs'
        || parentId !== assignment.targetId
        || candidateId === ''
        || candidateId === assignment.targetId
        || typeof args.repair !== 'object'
        || args.repair === null
      ) {
        return 'the Repair Scientist may register only one scientific repairs child under its assigned parent'
      }
      if (assignment.repairClaimId !== undefined && assignment.repairClaimId !== candidateId) {
        return 'the Repair Scientist assignment is limited to one repaired scientific child'
      }
      return undefined
    }
    if (exec.name === `${MCP}register_evidence_contract`) {
      if (claimId === undefined || claimId !== assignment.repairClaimId) {
        return 'the Repair Scientist may contract only its successfully registered repair child'
      }
    }
    return undefined
  })
}

function projectChildEvent(assignment, event) {
  const common = {
    role: assignment.role,
    assignment_id: assignment.assignmentId,
    claim_id: assignment.targetId,
    child_session_id: assignment.childSessionId,
    sequence: event.seq,
  }
  if (event.type === 'assistant/message' && event.data.usage !== undefined) {
    appendActivity({
      ...common,
      kind: 'model',
      status: event.data.interrupted === true ? 'interrupted' : 'responded',
      usage: event.data.usage,
    })
  } else if (event.type === 'tool/call') {
    appendActivity({
      ...common,
      kind: 'tool',
      status: 'running',
      tool: event.data.name,
      call_id: event.data.callId,
    })
  } else if (event.type === 'tool/result') {
    const block = event.data.message.content?.find(item => item.type === 'tool-result')
    appendActivity({
      ...common,
      kind: 'tool',
      status: event.data.error !== undefined || block?.isError === true ? 'failed' : 'succeeded',
      call_id: event.data.message.source.callId,
    })
  }
}

function verifyFalsifierResult(args, structured, claims) {
  if (structured.assignment_id !== args.assignment_id || structured.claim_id !== args.claim_id) {
    throw new Error('Falsifier returned a result for a different assignment or claim')
  }
  const claim = claimById(claims, args.claim_id)
  if (claim === undefined) throw new Error('assigned claim disappeared from the durable ledger')
  if (structured.outcome === 'falsified') {
    if (claim.status !== 'falsified' || !Number.isInteger(claim.decisive_contract_version)) {
      throw new Error('Falsifier reported falsification that CampaignKernel did not accept')
    }
    const paths = new Set((claim.evidence ?? []).map(item => item.path))
    if (
      structured.decisive_evidence_paths.length === 0
      || structured.decisive_evidence_paths.some(path => !paths.has(path))
    ) {
      throw new Error('Falsifier result does not cite durable evidence on the falsified claim')
    }
  } else if (structured.outcome === 'ready_for_adjudication') {
    if (claim.status !== 'open' || !contractExists(claim, structured.contract_version)) {
      throw new Error('Falsifier adjudication handoff has no matching open contracted claim')
    }
    const qualifying = (claim.evidence ?? []).filter(evidence => (
      evidence.contract_version === structured.contract_version
      && evidence.observation_sufficient === true
      && evidence.provenance?.tracked === true
      && evidence.provenance?.evidence_eligible === true
      && evidence.provenance?.execution_succeeded !== false
    ))
    if (qualifying.length === 0) {
      throw new Error(
        'Falsifier adjudication handoff requires durable evidence marked '
        + 'observation_sufficient=true under its selected contract',
      )
    }
    if (
      typeof structured.case_for_sufficiency !== 'string'
      || structured.case_for_sufficiency.length < 16
    ) {
      throw new Error('Falsifier adjudication handoff requires a bounded sufficiency case')
    }
  }
  return { ...structured, durable_claim_status: claim.status }
}

function verifyRepairResult(args, structured, claims) {
  if (
    structured.assignment_id !== args.assignment_id
    || structured.parent_claim_id !== args.parent_claim_id
  ) {
    throw new Error('Repair Scientist returned a result for a different assignment or parent')
  }
  if (structured.outcome === 'blocked') return structured
  if (typeof structured.child_claim_id !== 'string') {
    throw new Error('Repair Scientist did not identify its durable repair child')
  }
  const child = claimById(claims, structured.child_claim_id)
  const parent = claimById(claims, args.parent_claim_id)
  const parentEvidence = new Set((parent?.evidence ?? []).map(item => item.path))
  const repairPaths = child?.repair?.counterexample_paths ?? []
  if (
    parent === undefined
    || child === undefined
    || parent.status !== 'falsified'
    || child.kind !== 'scientific'
    || child.relation !== 'repairs'
    || String(child.parent_id).toLowerCase() !== args.parent_claim_id.toLowerCase()
    || child.statement === parent.statement
    || child.status !== 'open'
    || !contractExists(child, structured.contract_version)
    || !Array.isArray(repairPaths)
    || repairPaths.length === 0
    || repairPaths.some(path => !parentEvidence.has(path))
  ) {
    throw new Error('Repair Scientist handoff does not match a durable open contracted repair child')
  }
  return { ...structured, durable_claim_status: child.status }
}

export function apply(ctx) {
  const pendingByParent = new Map()
  const activeBySession = new Map()

  ctx.on('subagent/start', (info) => {
    const child = ctx.agents.get(info.id)
    const parentId = child?.session?.header?.parentSession
    const assignment = parentId === undefined ? undefined : pendingByParent.get(String(parentId))
    if (child === undefined || assignment === undefined) return
    assignment.childSessionId = String(info.id)
    activeBySession.set(String(info.id), assignment)
    installAssignmentGuard(child, assignment)
    appendActivity({
      kind: 'agent',
      status: 'running',
      role: assignment.role,
      assignment_id: assignment.assignmentId,
      claim_id: assignment.targetId,
      child_session_id: String(info.id),
    })
  })

  ctx.on('session/event', (session, event) => {
    const assignment = activeBySession.get(String(session.id))
    if (assignment !== undefined) projectChildEvent(assignment, event)
  })

  ctx.on('tools/result', (exec, result) => {
    if (result.isError || exec.agent === undefined) return
    const assignment = activeBySession.get(String(exec.agent.id))
    if (assignment === undefined || exec.name !== `${MCP}register_claim`) return
    const args = asRecord(exec.arguments)
    const claimId = typeof args.claim_id === 'string' ? args.claim_id.toLowerCase() : undefined
    if (claimId === undefined) return
    if (assignment.role === 'falsifier' && args.kind !== 'scientific') {
      assignment.allowedClaims.add(claimId)
    } else if (assignment.role === 'repair_scientist') {
      assignment.repairClaimId = claimId
      assignment.allowedClaims.add(claimId)
    }
  })

  async function runRole(role, args, exec) {
    const parent = exec.agent
    if (parent === undefined) throw new Error(`${role} requires a calling lead scientist`)
    const targetId = role === 'falsifier' ? args.claim_id : args.parent_claim_id
    const snapshot = await internalMcpCall(
      ctx,
      exec,
      `${role}:snapshot-before`,
      `${MCP}snapshot`,
      {},
    )
    const claimsBefore = await internalMcpCall(
      ctx,
      exec,
      `${role}:claims-before`,
      `${MCP}claims`,
      { view: 'role', claim_ids: [targetId] },
    )
    const target = claimById(claimsBefore, targetId)
    if (
      target === undefined
      || target.kind !== 'scientific'
      || (role === 'falsifier' && target.status !== 'open')
      || (role === 'repair_scientist' && target.status !== 'falsified')
    ) {
      throw new Error(`${role} assignment target has an incompatible durable state`)
    }

    const parentId = String(parent.session.id)
    if (pendingByParent.has(parentId)) throw new Error('a scientific role is already starting')
    const targetKey = String(target.id).toLowerCase()
    const childClaims = await childClaimSummaries(ctx, exec, role, targetKey)
    const commissionedClaims = childClaims
      .filter(claim => (
        claim?.kind !== 'scientific'
        && typeof claim?.parent_id === 'string'
        && claim.parent_id.toLowerCase() === targetKey
      ))
      .map(claim => String(claim.id).toLowerCase())
    const assignment = {
      role,
      assignmentId: args.assignment_id,
      targetId: targetKey,
      allowedClaims: new Set([targetKey, ...commissionedClaims]),
      repairClaimId: undefined,
      childSessionId: undefined,
      guardInstalled: false,
    }
    appendActivity({
      kind: 'agent',
      status: 'starting',
      role,
      assignment_id: args.assignment_id,
      claim_id: targetId,
    })

    pendingByParent.set(parentId, assignment)
    let run
    try {
      run = await ctx.subagents.start('spawn', {
        label: `${role === 'falsifier' ? 'Falsify' : 'Repair'} ${targetId}`,
        prompt: [{
          type: 'text',
          text: rolePacket(snapshot, target, args, role),
        }],
        parent,
        signal: exec.signal,
        outputSchema: role === 'falsifier' ? FALSIFIER_SCHEMA : REPAIR_SCHEMA,
        maxDepth: 1,
        toolFilter: {
          allow: role === 'falsifier' ? FALSIFIER_TOOL_NAMES : REPAIR_TOOL_NAMES,
        },
        persona: role === 'falsifier' ? FALSIFIER_PERSONA : REPAIR_PERSONA,
      })
    } finally {
      pendingByParent.delete(parentId)
    }

    if (run.localAgent !== undefined) {
      assignment.childSessionId = String(run.id)
      activeBySession.set(String(run.id), assignment)
      installAssignmentGuard(run.localAgent, assignment)
    }

    let result
    try {
      result = await run.result
      if (result.stopReason !== 'completed' || result.structured === undefined) {
        appendActivity({
          kind: 'agent',
          status: 'failed',
          role,
          assignment_id: args.assignment_id,
          claim_id: targetId,
          child_session_id: String(run.id),
          stop_reason: result.stopReason,
        })
        throw new Error(
          `${role} ended with ${result.stopReason}`
          + (result.diagnostic === undefined ? '' : `: ${result.diagnostic}`),
        )
      }
      const claimIdsAfter = [targetId]
      if (
        role === 'repair_scientist'
        && typeof result.structured.child_claim_id === 'string'
      ) {
        claimIdsAfter.push(result.structured.child_claim_id)
      }
      const claimsAfter = await internalMcpCall(
        ctx,
        exec,
        `${role}:claims-after`,
        `${MCP}claims`,
        { view: 'role', claim_ids: claimIdsAfter },
      )
      const verified = role === 'falsifier'
        ? verifyFalsifierResult(args, result.structured, claimsAfter)
        : verifyRepairResult(args, result.structured, claimsAfter)
      appendActivity({
        kind: 'agent',
        status: 'completed',
        role,
        assignment_id: args.assignment_id,
        claim_id: targetId,
        child_session_id: String(run.id),
        outcome: result.structured.outcome,
      })
      return { ...verified, role_run_id: String(run.id) }
    } finally {
      activeBySession.delete(String(run.id))
      await run.dispose()
    }
  }

  ctx.tools.register({
    name: 'simjecture_falsify',
    description:
      'Start a fresh claim-scoped Falsifier/Experimenter. It commissions and '
      + 'tests one open scientific claim, then returns either a kernel-accepted '
      + 'counterexample, a case for the independent judge, or a durable blocker.',
    parameters: {
      type: 'object',
      additionalProperties: false,
      properties: {
        assignment_id: { type: 'string' },
        claim_id: { type: 'string' },
        focus: { type: 'string' },
        evidence_gaps: { type: 'array', items: { type: 'string' } },
        next_test: { oneOf: [{ type: 'string' }, { type: 'null' }] },
      },
      required: ['assignment_id', 'claim_id', 'focus', 'evidence_gaps', 'next_test'],
    },
    output: {
      schema: {},
      render: (_args, value) => [{ type: 'text', text: JSON.stringify(value) }],
    },
    execute: (args, exec) => runRole('falsifier', args, exec),
  })

  ctx.tools.register({
    name: 'simjecture_repair',
    description:
      'Start a fresh Repair Scientist for one falsified scientific claim. It '
      + 'registers or reuses one minimal repairs child and its prospective '
      + 'contract; a later fresh Falsifier tests that child.',
    parameters: {
      type: 'object',
      additionalProperties: false,
      properties: {
        assignment_id: { type: 'string' },
        parent_claim_id: { type: 'string' },
        focus: { type: 'string' },
      },
      required: ['assignment_id', 'parent_claim_id', 'focus'],
    },
    output: {
      schema: {},
      render: (_args, value) => [{ type: 'text', text: JSON.stringify(value) }],
    },
    execute: (args, exec) => runRole('repair_scientist', args, exec),
  })
}
