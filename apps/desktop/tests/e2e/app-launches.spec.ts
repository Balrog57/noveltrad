import { test, expect } from '@playwright/test'
import { _electron as electron } from 'playwright'
import path from 'node:path'

test('app launches and shows home', async () => {
  const app = await electron.launch({
    args: [path.join(__dirname, '../../out/main/index.js')],
    cwd: path.join(__dirname, '../..')
  })

  const window = await app.firstWindow()
  await expect(window).toHaveTitle('NovelTrad 2.0')
  await expect(window.locator('h1')).toContainText('NovelTrad 2.0')

  await app.close()
})
