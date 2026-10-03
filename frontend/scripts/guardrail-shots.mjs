// Screenshots and checks for the guardrail lab tab and the guardrail chat examples.
// Run: node scripts/guardrail-shots.mjs <output-dir>   (dev servers on 5173 and 2024 must be up)
import { chromium } from '@playwright/test'
const out = process.argv[2]
const browser = await chromium.launch()
const errors = []
const page = await browser.newPage({ viewport: { width: 1280, height: 860 } })
page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()) })
page.on('pageerror', (e) => errors.push('pageerror: ' + e.message))
await page.goto('http://localhost:5173/')

await page.getByRole('tab', { name: '가드레일 비교' }).click()
for (const [index, preset] of ['초성 욕설', '남의 욕을 전함'].entries()) {
  await page.getByRole('button', { name: preset }).click()
  await page.getByRole('button', { name: 'Jev 에 묻기' }).click()
  await page.getByRole('region', { name: '판단 결과' }).waitFor({ timeout: 30000 })
  await page.waitForTimeout(2500)
  await page.screenshot({ path: `${out}/lab-${index}.png`, fullPage: true })
}

await page.getByRole('tab', { name: '고객지원 에이전트' }).click()
await page.getByRole('button', { name: /개인정보/ }).click()
await page.locator('.row-assistant .prose').last().waitFor({ timeout: 60000 })
await page.waitForTimeout(4000)
console.log('pii example: human bubbles =', await page.locator('.row-human').count())
console.log('pii example: human text =', await page.locator('.row-human').first().innerText())
await page.screenshot({ path: `${out}/chat-pii.png` })
await page.getByRole('textbox', { name: '메시지' }).fill('너 같은 쓰레기 상담원은 죽어버려')
await page.keyboard.press('Enter')
await page.getByText('턴 2').waitFor({ timeout: 60000 })
await page.waitForTimeout(3000)
console.log('after abuse: human bubbles =', await page.locator('.row-human').count())
await page.screenshot({ path: `${out}/chat-abuse.png` })
console.log('console errors:', errors.length, errors.slice(0, 3))
await browser.close()
