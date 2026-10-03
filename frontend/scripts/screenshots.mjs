import { chromium } from '@playwright/test'
const out = process.argv[2]
const browser = await chromium.launch()
const errors = []
async function open(width, height, scheme = 'light') {
  const page = await browser.newPage({ viewport: { width, height }, colorScheme: scheme })
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()) })
  page.on('pageerror', (e) => errors.push('pageerror: ' + e.message))
  await page.goto('http://localhost:5173/')
  return page
}
// 1. empty state
let page = await open(1280, 800)
await page.screenshot({ path: `${out}/01-welcome.png` })
// 2. shipping example
await page.getByRole('button', { name: /배송 조회/ }).click()
await page.getByText('턴 1').waitFor({ timeout: 60000 })
await page.locator('.row-assistant .prose').last().waitFor({ timeout: 60000 })
await page.waitForTimeout(1500)
await page.locator('.tool-card summary').first().click()
await page.screenshot({ path: `${out}/02-chat-shipping.png` })
// 3. hesitant refund -> approval card
await page.getByRole('textbox', { name: '메시지' }).fill('A1004 환불해야 하나 싶은데… 잘 모르겠네요. 일단 환불 접수해 주세요')
await page.keyboard.press('Enter')
try {
  await page.getByRole('alertdialog').waitFor({ timeout: 60000 })
  await page.screenshot({ path: `${out}/03-approval.png` })
  await page.getByRole('button', { name: '거절' }).click()
  await page.getByText('실행 안 함').waitFor({ timeout: 60000 })
  await page.waitForTimeout(4000)
  console.log('approval: card shown, reject resumed')
} catch (e) { console.log('approval: NOT shown -', e.message.split('\n')[0]) }
await page.screenshot({ path: `${out}/04-after-reject.png`, fullPage: false })
// 4. pattern tabs
const tabs = ['메모리 압축', '도구 게이트', '검색·모델 라우팅', '브라우저 액션']
for (const [i, name] of tabs.entries()) {
  await page.getByRole('tab', { name }).click()
  if (name === '도구 게이트') await page.getByRole('button', { name: '실행 전: 환경 변수 전송' }).click()
  if (name === '브라우저 액션') await page.getByRole('button', { name: '결제 버튼' }).click()
  await page.getByRole('button', { name: 'Jev 에 묻기' }).click()
  await page.getByRole('region', { name: '판단 결과' }).waitFor({ timeout: 30000 })
  await page.screenshot({ path: `${out}/1${i}-${i}.png`, fullPage: false })
}
// back to chat: conversation preserved?
await page.getByRole('tab', { name: '고객지원 에이전트' }).click()
console.log('chat preserved after tab switch:', await page.locator('.row-human').count(), 'user messages')
await page.close()
// 5. mobile + dark
page = await open(375, 812)
await page.screenshot({ path: `${out}/20-mobile-welcome.png` })
console.log('mobile horizontal overflow:', await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth))
await page.getByRole('tab', { name: '도구 게이트' }).click()
await page.getByRole('button', { name: 'Jev 에 묻기' }).click()
await page.getByRole('region', { name: '판단 결과' }).waitFor({ timeout: 30000 })
await page.screenshot({ path: `${out}/21-mobile-pattern.png`, fullPage: true })
console.log('mobile pattern overflow:', await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth))
await page.close()
page = await open(1280, 800, 'dark')
await page.getByRole('button', { name: /프롬프트 인젝션/ }).click()
await page.getByText('턴 1').waitFor({ timeout: 60000 })
await page.waitForTimeout(1500)
await page.screenshot({ path: `${out}/30-dark-chat.png` })
await page.close()
console.log('console errors:', errors.length, errors.slice(0, 5))
await browser.close()
