// Fails if the gzipped JS shipped to the browser exceeds the budget.
import { readdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { gzipSync } from 'node:zlib'

const BUDGET_KB = 220
const dir = 'dist/assets'
const files = readdirSync(dir).filter((f) => f.endsWith('.js'))
let total = 0
for (const f of files) {
  const kb = gzipSync(readFileSync(join(dir, f))).length / 1024
  total += kb
  console.log(`${f.padEnd(32)} ${kb.toFixed(1)} kB gzip`)
}
console.log(`total ${total.toFixed(1)} kB gzip (budget ${BUDGET_KB} kB)`)
if (total > BUDGET_KB) process.exit(1)
