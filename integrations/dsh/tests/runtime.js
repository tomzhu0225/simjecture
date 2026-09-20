import { Context } from '@deepseek-ai/cordis'
import AgentRegistry from '@deepseek-ai/dsh-agent'
import AgentLoop from '@deepseek-ai/dsh-agent-loop'
import DefaultModel from '@deepseek-ai/dsh-agent-default-model'
import LlmRuntime, { LlmAdapter } from '@deepseek-ai/dsh-llm'
import SessionStore from '@deepseek-ai/dsh-session'
import Projection from '@deepseek-ai/dsh-session-projection'
import SystemPrompt from '@deepseek-ai/dsh-system-prompt'
import Tools from '@deepseek-ai/dsh-tools'
import Persistence from '@deepseek-ai/dsh-session-persistence-jsonl'
import Subagents from '@deepseek-ai/dsh-subagent'
import * as Spawn from '@deepseek-ai/dsh-subagent-spawn-in-process'

export function response(block) {
  const delta = block.type === 'text'
    ? { type: 'text-delta', index: 0, text: block.text }
    : { type: 'tool-call-delta', index: 0, id: block.id, name: block.name, argumentsDelta: block.arguments }
  return [
    { type: 'block-start', index: 0, blockType: block.type }, delta,
    { type: 'block-end', index: 0, block },
    { type: 'usage', usage: { inputTokens: 10, outputTokens: 5 } },
    { type: 'finish', reason: { kind: block.type === 'text' ? 'stop' : 'tool-calls' } },
  ]
}
export const answer = text => response({ type: 'text', text })
export const call = (name, args, id = 'call-1') => response({ type: 'tool-call', id, name, arguments: JSON.stringify(args) })

class ScriptedModel extends LlmAdapter {
  requests = []
  constructor(script) { super(); this.script = [...script] }
  async resolveModel(provider, model) { return { provider, id: model, name: model } }
  async *stream(options) {
    this.requests.push(options)
    const next = this.script.shift()
    if (!next) throw new Error('script exhausted')
    yield* typeof next === 'function' ? await next(options) : next
  }
}

export async function runtime(script = [], root) {
  const ctx = new Context()
  for (const plugin of [LlmRuntime, SessionStore, Projection, SystemPrompt, Tools, AgentRegistry]) {
    await ctx.plugin(plugin)
  }
  if (root) await ctx.plugin(Persistence, { root, compression: 'none' })
  await ctx.plugin(DefaultModel, { provider: 'test', model: 'scripted' })
  await ctx.plugin(AgentLoop, { agents: [] })
  await ctx.plugin(Subagents)
  await ctx.plugin(Spawn, { providerName: 'spawn' })
  const model = new ScriptedModel(script)
  ctx.llm.registerAdapter(['test'], model)
  return { ctx, model }
}

export function tool(ctx, name, execute = () => ({})) {
  ctx.tools.register({
    name, description: name, parameters: { type: 'object' },
    output: { schema: {}, render: (_args, value) => [{ type: 'text', text: JSON.stringify(value) }] },
    execute: async (args, exec) => execute(args, exec),
  })
}
