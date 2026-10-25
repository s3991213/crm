import { expect, test as base, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { E2E_DIR } from "../playwright.config";

// Every test also fails on a browser console error (401s are expected after signing out).
const test = base.extend({
  page: async ({ page }, use) => {
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(String(e)));
    page.on("console", (m) => { if (m.type() === "error" && !/401|Unauthorized/.test(m.text())) errors.push(m.text()); });
    await use(page);
    expect(errors).toEqual([]);
  },
});

async function signIn(page: Page, username = "tester", password = "tester-pass-456") {
  await page.goto("/");
  await page.fill("#username", username);
  await page.fill("#password", password);
  await page.click("button[type=submit]");
}

async function say(page: Page, text: string) {
  await page.fill("#chat-input", text);
  await page.keyboard.press("Enter");
  await expect(page.locator(".reply--working")).toHaveCount(0);
}

test("a wrong password is refused, and a new starter must choose a password first", async ({ page }) => {
  await signIn(page, "newbie", "wrong-pass");
  await expect(page.locator(".login__error")).toContainText("don't match");

  await page.fill("#password", "temp-pass-123");
  await page.click("button[type=submit]");
  await expect(page.getByText("Choose your password")).toBeVisible();
  await expect(page.locator("#chat-input")).toBeDisabled();

  const fields = page.locator(".password input[type=password]");
  await fields.nth(0).fill("newbie-pass-456");
  await fields.nth(1).fill("newbie-pass-456");
  await page.getByText("Save password").click();
  await expect(page.getByText("All set")).toBeVisible();
  await expect(page.locator("#chat-input")).toBeEnabled();
});

test("look up a student, and open one from the at-risk list", async ({ page }) => {
  await signIn(page);
  await page.getByText("Show at-risk students").click(); // a starter, shown only in an empty chat
  await expect(page.getByText(/students may need attention/)).toBeVisible();
  const first = page.locator(".link").first();
  const name = await first.innerText();
  await first.click();
  await expect(page.locator(".card__title").last()).toContainText(name);

  await say(page, "find Liam");
  await expect(page.locator(".card__title").last()).toContainText("Liam Nguyen");
});

test("a change is saved only on Confirm, logged once, and Cancel saves nothing", async ({ page }) => {
  await signIn(page);
  await say(page, "change Arjun's status to Withdrawn");
  const card = page.locator(".confirm--pending");
  await expect(card).toContainText("Arjun Patel");
  await card.getByText("Confirm").click();
  await expect(page.getByText("Saved", { exact: true })).toBeVisible();
  await expect(page.locator(".thread")).toContainText("is now Withdrawn");
  const log = fs.readFileSync(path.join(E2E_DIR, "writes.log"), "utf8");
  expect(log.match(/student='Arjun Patel'/g)).toHaveLength(1);
  expect(log).toContain("staff='Test Staff'");

  await say(page, "change Liam's status to Deferred");
  await page.locator(".confirm--pending").getByText("Cancel").click();
  await expect(page.getByText("Cancelled, nothing changed")).toBeVisible();
  expect(fs.readFileSync(path.join(E2E_DIR, "writes.log"), "utf8")).not.toContain("Liam");
});

test("an email draft is shown, never sent", async ({ page }) => {
  await signIn(page);
  await say(page, "draft a follow-up email for Liam");
  await expect(page.getByText("Draft email · not sent")).toBeVisible();
  await expect(page.getByText("Nothing has been sent.")).toBeVisible();
});

test("signing out ends the session on the server, so a copied cookie stops working", async ({ page, context }) => {
  await signIn(page);
  await expect(page.locator("#chat-input")).toBeVisible();
  const copied = await context.cookies();
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page.locator("#username")).toBeVisible();

  await context.addCookies(copied);
  await page.reload();
  await expect(page.locator("#username")).toBeVisible();
});

test("fits a phone screen without sideways scrolling", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await signIn(page);
  await say(page, "change Liam's status to Deferred");
  await expect(page.locator(".confirm--pending")).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});
