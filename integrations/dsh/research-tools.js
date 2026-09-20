/** Keep native/provider tools while restricting authoritative scientific calls. */
export function isScientificTool(name) {
  return name.startsWith('mcp__simjecture__') || name.startsWith('simjecture_')
}

export function researchToolFilter(ctx, allowed) {
  const permitted = new Set(allowed)
  return { deny: ctx.tools.schemas().map(tool => tool.name)
    .filter(name => isScientificTool(name) && !permitted.has(name)) }
}

export function restrictScientificTools(ctx, allowed) {
  const permitted = new Set(allowed)
  ctx.tools.restrict(researchToolFilter(ctx, allowed))
  // Also cover scientific tools registered later by a trusted plugin.
  ctx.tools.guard(exec => isScientificTool(exec.name) && !permitted.has(exec.name)
    ? 'scientific operation is outside this role; use its assigned Simjecture tools'
    : undefined)
}
