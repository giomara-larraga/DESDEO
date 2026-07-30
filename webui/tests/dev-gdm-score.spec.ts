import { test } from '@playwright/test';

test('open GDM-SCORE-bands as multiple users', async ({ browser }) => {
  test.setTimeout(0);

  const users = [
    { name: 'analyst1', auth: '.auth/analyst1.json' },
    { name: 'dm1', auth: '.auth/dm1.json' },
    { name: 'dm2', auth: '.auth/dm2.json' },
  ];

  for (const user of users) {
    const context = await browser.newContext({
      storageState: user.auth,
      viewport: null,
    });

    const page = await context.newPage();

    await page.goto(
      'http://localhost:5173/groups'
    );

    console.log(`Opened ${user.name}`);
  }

  await new Promise(() => {});
});