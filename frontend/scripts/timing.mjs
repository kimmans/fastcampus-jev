// Measures how a chat turn feels: when each piece of feedback first appears and how the answer grows.
// Usage: node scripts/timing.mjs "<message>"   (both dev servers must be running)
import { chromium } from '@playwright/test'

const text = process.argv[2] ?? '환불 규정을 자세히 설명해 주세요'
const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } })
await page.goto('http://localhost:5173/')
await page.getByRole('textbox', { name: '메시지' }).fill(text)

const samples = await page.evaluate(async () => {
  const started = performance.now()
  const marks = {}
  const lengths = []
  const mark = (name, selector) => {
    if (marks[name] === undefined && document.querySelector(selector)) {
      marks[name] = Math.round(performance.now() - started)
    }
  }
  document.querySelector('form.composer').requestSubmit()
  return await new Promise((resolve) => {
    const timer = setInterval(() => {
      mark('human_bubble', '.row-human')
      mark('feedback_of_any_kind', '.typing, .stage-line, .tool-card, .decision')
      mark('first_decision', '.decision')
      mark('first_tool_card', '.tool-card')
      const answers = [...document.querySelectorAll('.row-assistant .prose')]
      const length = answers.reduce((sum, node) => sum + node.textContent.length, 0)
      if (length > 0 && marks.first_answer_char === undefined) {
        marks.first_answer_char = Math.round(performance.now() - started)
      }
      if (lengths.at(-1) !== length) lengths.push(length)
      const busy = document.querySelector('.send[aria-label="응답 중지"]')
      const elapsed = performance.now() - started
      if ((marks.first_answer_char !== undefined && !busy) || elapsed > 60000) {
        clearInterval(timer)
        marks.done = Math.round(elapsed)
        resolve({ marks, answer_length_steps: lengths.length, final_length: length })
      }
    }, 50)
  })
})
console.log(JSON.stringify(samples))
await browser.close()
