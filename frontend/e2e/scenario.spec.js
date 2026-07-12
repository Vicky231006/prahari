import { test, expect } from '@playwright/test';

test.describe('Scenario Runner (Phase 10)', () => {
  // Test hitting the scenario runner and seeing that all 4 scenarios can be injected
  test('injects all 4 demo scenarios successfully', async ({ page }) => {
    // We mock the API route so the test can run purely on the frontend without the backend for speed
    await page.route('/api/demo/inject', async (route) => {
      const request = route.request();
      if (request.method() === 'POST') {
        const postData = JSON.parse(request.postData() || '{}');
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ message: `Injected scenario ${postData.scenario_type} successfully` }),
        });
      } else {
        await route.continue();
      }
    });

    // Go to the app
    await page.goto('http://localhost:5173/scenario-runner');

    // Wait for the page to load
    await expect(page.locator('h1')).toContainText('Scenario Runner');

    // Inject ATO
    await page.click('text="Inject Scenario" >> nth=0');
    await expect(page.locator('.scenario-card__result--success').first()).toContainText('Injected scenario ato successfully');

    // Inject Insider
    await page.click('text="Inject Scenario" >> nth=1');
    await expect(page.locator('.scenario-card__result--success').nth(1)).toContainText('Injected scenario insider successfully');

    // Inject Credential Stuffing
    await page.click('text="Inject Scenario" >> nth=2');
    await expect(page.locator('.scenario-card__result--success').nth(2)).toContainText('Injected scenario credential_stuffing successfully');

    // Inject HNDL
    await page.click('text="Inject Scenario" >> nth=3');
    await expect(page.locator('.scenario-card__result--success').nth(3)).toContainText('Injected scenario hndl successfully');
  });
});
