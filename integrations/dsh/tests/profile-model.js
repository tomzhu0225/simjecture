// Deterministic model boundary for the real CLI/profile/MCP smoke test.
import assert from 'node:assert/strict'
import { appendFileSync } from 'node:fs'
import { LlmAdapter } from '@deepseek-ai/dsh-llm'
import { LEAD_TOOL_NAMES } from '../roles.js'
import { answer, call } from './runtime.js'
export const inject = ['llm']
export function apply(ctx) {
  ctx.llm.registerAdapter(['test'], new class extends LlmAdapter {
    calls = 0
    async resolveModel(provider, model) { return { provider, id: model, name: model } }
    async *stream(options) {
      const names = options.tools.map(t => t.name)
      assert.deepEqual(names.filter(n => n.startsWith('mcp__simjecture__') || n.startsWith('simjecture_')).sort(), [...LEAD_TOOL_NAMES].sort())
      for (const native of ['bash', 'read', 'write', 'web_search', 'web_fetch']) assert.ok(names.includes(native), native)
      assert.match(JSON.stringify(options.messages[0]), /persistent Lead Scientist/)
      appendFileSync(process.env.SMOKE_REQUESTS, `${JSON.stringify(options.messages)}\n`)
      if (this.calls++ === 0) yield* call('mcp__simjecture__snapshot', {})
      else if (this.calls === 2) {
        const last = options.messages.at(-1).content[0]
        assert.equal(last.isError, false, JSON.stringify(last))
        yield* call('mcp__simjecture__finalize_campaign', { operation_id: 'smoke-finalize', final_answer: 'Do not accept an untested claim.' }, 'finalize')
      } else if (this.calls === 3) {
        assert.equal(options.messages.at(-1).content[0].isError, true, 'kernel must reject premature finalization')
        yield* call('bash', { command: 'printf research-ok > note.txt; printf tampered > ' + JSON.stringify(process.env.SMOKE_PROTECTED), description: 'test record boundary' }, 'native')
      } else {
        yield* answer('profile smoke completed')
      }
    }
  }())
}
