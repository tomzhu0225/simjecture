import assert from 'node:assert/strict'
import { test } from 'node:test'
import { mkdtemp, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { createUserMessage } from '@deepseek-ai/dsh-llm'
import * as Waiter from '../job-waiter.js'
import { runtime, tool, answer, call } from './runtime.js'

for (const recovering of [false, true]) {
  test(`job waiter ${recovering ? 'recovers an existing' : 'submits one'} job without model polling or resubmission`, async () => {
    const { ctx, model } = await runtime([
      call(recovering ? 'mcp__simjecture__job_status' : 'mcp__simjecture__run_python', recovering ? { job_id: 'durable-1' } : { operation_id: 'op-1' }),
      answer('job reconciled'),
    ])
    let submitted = 0
    let reads = 0
    tool(ctx, 'mcp__simjecture__run_python', () => {
      submitted++
      return { structuredContent: { job_id: 'durable-1', status: 'running' } }
    })
    tool(ctx, 'mcp__simjecture__job_status', args => {
      assert.equal(args.job_id, 'durable-1')
      reads++
      return { structuredContent: { job_id: 'durable-1', status: reads === 1 ? 'running' : 'succeeded',
        ...(args.report ? { receipt: 'authenticated-test-receipt' } : {}) } }
    })
    await ctx.plugin(Waiter)
    try {
      const { agent } = await ctx.agents.create({ sessionId: 'worker', agentOptions: { provider: 'test', model: 'scripted' } })
      agent.followup(createUserMessage({ content: [{ type: 'text', text: 'reconcile work' }], source: { kind: 'user' } }))
      await agent.whenIdle()
      assert.equal(submitted, recovering ? 0 : 1)
      assert.equal(reads, 3)
      assert.equal(model.requests.length, 2)
      assert.match(JSON.stringify(model.requests[1].messages), /authenticated-test-receipt/)
    } finally { await ctx.fiber.dispose() }
  })
}


test('interrupted wait resumes the durable session and reconciles without repeating submission', async () => {
  const root = await mkdtemp(join(tmpdir(), 'simjecture-job-resume-'))
  let submissions = 0
  try {
    for (const resume of [false, true]) {
      const { ctx, model } = await runtime(resume
        ? [call('mcp__simjecture__job_status', { job_id: 'durable-1' }), answer('recovered')]
        : [call('mcp__simjecture__run_python', { operation_id: 'op-1' })], root)
      let agent
      let timer
      tool(ctx, 'mcp__simjecture__run_python', () => {
        submissions++
        timer = setTimeout(() => agent.cancel({ kind: 'user' }, { keepInbox: true }), 20)
        return { structuredContent: { job_id: 'durable-1', status: 'running' } }
      })
      tool(ctx, 'mcp__simjecture__job_status', args => {
        assert.equal(args.job_id, 'durable-1')
        return { structuredContent: { job_id: 'durable-1', status: 'succeeded', receipt: 'recovered' } }
      })
      await ctx.plugin(Waiter)
      try {
        const options = { agentOptions: { provider: 'test', model: 'scripted' } }
        const handle = resume ? await ctx.agents.resume({ ...options, resumeSessionId: 'worker' })
          : await ctx.agents.create({ ...options, sessionId: 'worker' })
        agent = handle.agent
        agent.followup(createUserMessage({ content: [{ type: 'text', text: resume ? 'reconcile durable-1' : 'start' }], source: { kind: 'user' } }))
        await agent.whenIdle()
        await ctx.sessions.flush(agent.session)
        assert.equal(submissions, 1)
        assert.equal(model.requests.length, resume ? 2 : 1)
        const end = agent.session.snapshotEvents().findLast(e => e.type === 'turn/end')
        assert.equal(end.data.reason.kind, resume ? 'completed' : 'aborted')
      } finally { clearTimeout(timer); await ctx.fiber.dispose() }
    }
  } finally { await rm(root, { recursive: true, force: true }) }
})
