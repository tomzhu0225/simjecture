import assert from 'node:assert/strict'
import { test } from 'node:test'
import { existsSync } from 'node:fs'
import { mkdtemp, mkdir, writeFile, readFile, rm, symlink } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join, dirname, delimiter } from 'node:path'
import { fileURLToPath } from 'node:url'
import { promisify } from 'node:util'
import { execFile } from 'node:child_process'

const execute = promisify(execFile)
const bundle = fileURLToPath(new URL('..', import.meta.url))
const mcp = process.env.SIMJECTURE_MCP_EXECUTABLE ?? fileURLToPath(new URL('../../../.venv/bin/simjecture-mcp', import.meta.url))

test('real CLI profile and Python MCP: snapshot, finish gate, pause/resume, mandatory startup failure',
  { skip: !existsSync(mcp) && !process.env.SIMJECTURE_MCP_EXECUTABLE, timeout: 90000 }, async () => {
  assert.ok(existsSync(mcp), 'SIMJECTURE_MCP_EXECUTABLE must exist')
  const root = await mkdtemp(join(tmpdir(), 'simjecture-profile-test-'))
  await mkdir(join(root, 'records'))
  const profile = join(root, 'profiles', 'smoke')
  await mkdir(join(profile, 'node_modules', '@simjecture'), { recursive: true })
  await symlink(join(bundle, 'node_modules', '@deepseek-ai'), join(profile, 'node_modules', '@deepseek-ai'))
  await symlink(bundle, join(profile, 'node_modules', '@simjecture', 'dsh-bundle'))
  await writeFile(join(profile, 'package.json'), JSON.stringify({ name: 'smoke', private: true,
    dependencies: { '@simjecture/dsh-bundle': `link:${bundle}`, '@deepseek-ai/dsh-headless': '0.1.5-rc.2' },
    dsh: { profile: { bundles: ['@deepseek-ai/dsh-base', '@deepseek-ai/dsh-headless', '@simjecture/dsh-bundle'] } },
  }))
  await writeFile(join(profile, 'cordis.yml'), '[]\n')
  await writeFile(join(profile, 'cordis.patch.yml'), `
- id: agent-default-model
  config: { provider: test, model: scripted }
- id: session-title-llm
  disabled: true
- insert:
    - id: smoke-model
      name: ${JSON.stringify(join(bundle, 'tests/profile-model.js'))}
`)
  await writeFile(join(root, 'hypothesis.txt'), 'A testable smoke hypothesis.\n')
  const env = { ...process.env, DSH_HOME: root, CHOKIDAR_USEPOLLING: '1',
    PATH: `${dirname(mcp)}${delimiter}${process.env.PATH}`,
    SIMJECTURE_WORKSPACE: join(root, 'records'), SIMJECTURE_DSH_RESEARCH_ROOT: join(root, 'research'), SIMJECTURE_CAMPAIGN: 'campaign',
    SIMJECTURE_HYPOTHESIS_FILE: join(root, 'hypothesis.txt'),
    SIMJECTURE_DSH_SESSION_ROOT: join(root, 'sessions'), SIMJECTURE_DSH_SESSION_ID: 'smoke',
    SIMJECTURE_DSH_ACTIVITY_FILE: join(root, 'activity.jsonl'), SIMJECTURE_DSH_STATE_FILE: join(root, 'state.json'),
    SIMJECTURE_DSH_CONTROL_FILE: join(root, 'control.json'), SMOKE_REQUESTS: join(root, 'requests.jsonl'), SMOKE_PROTECTED: join(root, 'records', 'protected.txt'),
  }
  const cli = join(bundle, 'node_modules/@deepseek-ai/dsh/lib/bin.js')
  const run = (extra = {}) => execute(process.execPath, [cli, '--profile', 'smoke', 'Read the snapshot.'],
    { env: { ...env, ...extra }, timeout: 25000, maxBuffer: 1_000_000 })
  const state = async () => JSON.parse(await readFile(env.SIMJECTURE_DSH_STATE_FILE, 'utf8'))
  try {
    const dump = await execute(process.execPath, [cli, '--profile', 'smoke', '--dump-config'], { env })
    assert.equal(dump.stderr, '')
    assert.match(dump.stdout, /personaPrefix: >-/)
    await writeFile(env.SMOKE_PROTECTED, 'authoritative record')
    const fresh = await run({ SIMJECTURE_DSH_RESUME: '0' })
    assert.match(fresh.stdout, /profile smoke completed/)
    assert.equal((await state()).resumed, false)
    const resumed = await run({ SIMJECTURE_DSH_RESUME: '1' })
    assert.match(resumed.stdout, /profile smoke completed/)
    assert.equal((await state()).resumed, true)
    await writeFile(env.SIMJECTURE_DSH_CONTROL_FILE, JSON.stringify({ command: 'pause' }))
    await run({ SIMJECTURE_DSH_RESUME: '1' })
    assert.equal((await state()).status, 'paused')
    await rm(env.SIMJECTURE_DSH_CONTROL_FILE)
    await run({ SIMJECTURE_DSH_RESUME: '1' })
    assert.equal((await state()).resumed, true)
    assert.equal(await readFile(env.SMOKE_PROTECTED, 'utf8'), 'authoritative record')
    assert.equal(await readFile(join(root, 'research', 'note.txt'), 'utf8'), 'research-ok')
    const before = await readFile(env.SMOKE_REQUESTS, 'utf8')
    await assert.rejects(run({ SIMJECTURE_DSH_RESEARCH_ROOT: env.SIMJECTURE_WORKSPACE }))
    await assert.rejects(run({ SIMJECTURE_HYPOTHESIS_FILE: join(root, 'missing.txt') }))
    assert.equal(await readFile(env.SMOKE_REQUESTS, 'utf8'), before, 'no model request after MCP startup failure')
  } finally { await rm(root, { recursive: true, force: true }) }
})
