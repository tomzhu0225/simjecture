import assert from 'node:assert/strict'
import { test } from 'node:test'
import { createUserMessage } from '@deepseek-ai/dsh-llm'
import * as Roles from '../roles.js'
import * as Judge from '../adjudicator.js'
import { runtime, tool, answer, call } from './runtime.js'

const mcp = 'mcp__simjecture__'
async function parentTurn(ctx, text = 'private parent history') {
  const handle = await ctx.agents.create({ sessionId: 'parent', agentOptions: { provider: 'test', model: 'scripted' } })
  handle.agent.followup(createUserMessage({ content: [{ type: 'text', text }], source: { kind: 'user' } }))
  await handle.agent.whenIdle()
  return handle.agent
}
function kernelTools(ctx, handler) {
  tool(ctx, 'native_search', () => ({ sources: [] }))
  const names = new Set([...Roles.FALSIFIER_TOOL_NAMES, ...Roles.REPAIR_TOOL_NAMES,
    ...Roles.BLOCKER_RESOLVER_TOOL_NAMES, ...Judge.INTERNAL_TOOL_NAMES, `${mcp}finalize_campaign`])
  for (const name of names) tool(ctx, name, args => ({ structuredContent: handler(name, args) }))
}

for (const role of ['falsifier', 'repair', 'blocker']) {
  test(`${role} child has fresh history and rejects cross-claim mutation before its first tool executes`, async () => {
    const name = role === 'falsifier' ? 'simjecture_falsify' : role === 'repair' ? 'simjecture_repair' : 'simjecture_resolve_blocker'
    const args = role === 'falsifier'
      ? { assignment_id: 'a', claim_id: 'root', focus: 'test', evidence_gaps: [], next_test: null }
      : role === 'repair' ? { assignment_id: 'a', parent_claim_id: 'root', focus: 'repair' }
        : { assignment_id: 'a', claim_id: 'root', blocker_summary: 'blocked', prior_contract_version: null,
            prior_evidence_paths: [], evidence_gaps: [], next_test: null }
    const { ctx, model } = await runtime([
      call(name, args), call(`${mcp}register_evidence_contract`, { claim_id: 'unrelated' }),
      answer('cannot proceed'), answer('role failed safely'),
    ])
    let mutations = 0
    kernelTools(ctx, (name, args) => {
      if (name === `${mcp}snapshot`) return { hypothesis: 'test hypothesis' }
      if (name === `${mcp}claims`) return { claims: args.view === 'summary' ? [] : [
        { id: 'root', kind: 'scientific', status: role === 'repair' ? 'falsified' : 'open' },
      ] }
      if (name === `${mcp}register_evidence_contract`) mutations++
      return {}
    })
    await ctx.plugin(Roles)
    try {
      const parent = await parentTurn(ctx)
      assert.equal(model.requests.length, 4, JSON.stringify(parent.session.snapshotEvents().filter(e => e.type === 'tool/result')))
      assert.equal(mutations, 0)
      assert.ok(!JSON.stringify(model.requests[1].messages).includes('private parent history'))
      const childTools = model.requests[1].tools.map(t => t.name)
      assert.ok(!childTools.includes(`${mcp}finalize_campaign`))
      assert.ok(!childTools.includes('simjecture_adjudicate'))
      assert.ok(childTools.includes('native_search'))
      assert.match(JSON.stringify(model.requests[2].messages), /assigned|successfully registered/)
    } finally { await ctx.fiber.dispose() }
  })
}

for (const inconsistent of [false, true]) {
test(`real judge isolates history and ${inconsistent ? 'rejects inconsistent verdicts' : 'records usage'}`, async () => {
  const verdict = { claim_id: 'root', contract_version: 1, decision: 'insufficient', scientific_disposition: null,
    claim_tested: false, contract_preserves_claim_semantics: true, rationale: 'need evidence', evidence_gaps: ['missing run'], next_test: 'run test' }
  const { ctx, model } = await runtime([
    call('simjecture_adjudicate', { operation_id: 'judge-1', claim_id: 'root', contract_version: 1,
      case_for_sufficiency: 'Review the provided immutable case.' }),
    call('structured_output', inconsistent ? { ...verdict, scientific_disposition: 'supported' } : verdict), answer('review recorded'),
  ])
  let recorded
  kernelTools(ctx, (name, args) => {
    if (name === `${mcp}prepare_adjudication`) return { packet: { claim: 'root' }, case_sha256: 'sha', claim_id: 'root', contract_version: 1 }
    if (name === `${mcp}record_adjudication`) recorded = args
    return { accepted: true }
  })
  await ctx.plugin(Judge)
  try {
    const parent = await parentTurn(ctx)
    if (inconsistent) {
      assert.equal(recorded, undefined)
      assert.match(JSON.stringify(parent.session.snapshotEvents()), /inconsistent decision/)
      return
    }
    assert.ok(recorded, JSON.stringify(parent.session.snapshotEvents().filter(e => e.type === 'tool/result')))
    assert.deepEqual(recorded.verdict, verdict)
    assert.deepEqual(recorded.usage, { inputTokens: 10, outputTokens: 5 })
    assert.deepEqual(model.requests[1].tools.map(t => t.name), ['structured_output'])
    assert.ok(!JSON.stringify(model.requests[1].messages).includes('private parent history'))
  } finally { await ctx.fiber.dispose() }
})

}

test('blocker resolver can finish through schema-validated handoff without mutating claims', async () => {
  const result = { assignment_id: 'a', claim_id: 'root', outcome: 'feasible_test', contract_version: null,
    evidence_purpose: null, decisive_evidence_paths: [], case_for_sufficiency: null,
    alternatives_considered: ['smaller run'], feasibility_assessment: 'A smaller run fits the available resources.',
    evidence_gaps: ['missing run'], next_test: 'run smaller case' }
  const { ctx } = await runtime([
    call('simjecture_resolve_blocker', { assignment_id: 'a', claim_id: 'root', blocker_summary: 'blocked',
      prior_contract_version: null, prior_evidence_paths: [], evidence_gaps: ['missing run'], next_test: null }),
    call('structured_output', result), answer('continue testing'),
  ])
  kernelTools(ctx, (name, args) => {
    if (name === `${mcp}snapshot`) return { hypothesis: 'test hypothesis' }
    if (name === `${mcp}claims`) return { claims: args.view === 'summary' ? [] : [{ id: 'root', kind: 'scientific', status: 'open' }] }
    assert.fail(`unexpected kernel mutation: ${name}`)
  })
  await ctx.plugin(Roles)
  try {
    const parent = await parentTurn(ctx)
    const result = parent.session.snapshotEvents().find(e => e.type === 'tool/result')
    assert.equal(result.data.message.content[0].isError, false, JSON.stringify(result))
    assert.match(JSON.stringify(result), /feasible_test/)
  } finally { await ctx.fiber.dispose() }
})

test('native delegation retains its scientific parent claim guard', async () => {
  const { ctx, model } = await runtime([
    call('simjecture_falsify', { assignment_id: 'a', claim_id: 'root', focus: 'test', evidence_gaps: [], next_test: null }),
    call('native_delegate', {}),
    call(`${mcp}register_evidence_contract`, { claim_id: 'unrelated' }),
    answer('denied'), answer('worker done'), answer('lead done'),
  ])
  let mutations = 0
  kernelTools(ctx, (name, args) => {
    if (name === `${mcp}snapshot`) return { hypothesis: 'test hypothesis' }
    if (name === `${mcp}claims`) return { claims: args.view === 'summary' ? [] : [{ id: 'root', kind: 'scientific', status: 'open' }] }
    if (name === `${mcp}register_evidence_contract`) mutations++
    return {}
  })
  tool(ctx, 'native_delegate', async (_args, exec) => {
    const run = await ctx.subagents.start('spawn', { parent: exec.agent, signal: exec.signal,
      prompt: [{ type: 'text', text: 'research assistance' }], maxDepth: 2 })
    try { return (await run.result).output } finally { await run.dispose() }
  })
  await ctx.plugin(Roles)
  try {
    await parentTurn(ctx)
    assert.equal(model.requests.length, 6)
    assert.equal(mutations, 0)
    assert.match(JSON.stringify(model.requests[3].messages), /assigned or commissioned/)
  } finally { await ctx.fiber.dispose() }
})
