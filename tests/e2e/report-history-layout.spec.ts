import { expect, test } from "@playwright/test";
import { mkdirSync } from "node:fs";

for (const route of ["excel-studio", "deck-builder"]) {
  test(`${route} contains every report-history label across viewports`, async ({
    page,
  }) => {
    const quality = "CALCULATED WITH STALE DATA";
    await page.route("**/backend/api/v1/report-jobs", async (route) => {
      await route.fulfill({
        json: {
          items: [
            {
              id: "layout-fixture",
              kind: "portfolio",
              format: "xlsx",
              status: "SUCCEEDED",
              progress: 1,
              source: "Fictional layout fixture",
              quality,
              as_of: "2026-09-04T00:00:00Z",
              created_at: "2026-09-05T01:00:00Z",
              content_hash: "a".repeat(64),
              snapshot_hash: "b".repeat(64),
              error_message: null,
              download_url: null,
              source_url: "/api/v1/report-jobs/layout-fixture/source",
            },
          ],
        },
      });
    });
    await page.goto(`/${route}`);
    const history = page.getByRole("region", {
      name: "Report history",
      exact: true,
    });
    const row = history.getByRole("button", { name: /PORTFOLIO \/ XLSX/ });
    await expect(row).toContainText(quality);
    for (const [width, height] of [
      [1366, 768],
      [1440, 900],
      [1920, 1080],
      [2560, 1440],
      [390, 844],
    ]) {
      await page.setViewportSize({ width, height });
      await row.scrollIntoViewIfNeeded();
      await expect(row).toBeInViewport({ ratio: 1 });
      const layout = await row.evaluate((button) => {
        const bounds = button.getBoundingClientRect();
        const cells = Array.from(button.children).map((cell) => {
          const box = cell.getBoundingClientRect();
          const range = document.createRange();
          range.selectNodeContents(cell);
          return {
            text: cell.textContent,
            contained: Array.from(range.getClientRects()).every(
              (text) =>
                text.left >= box.left - 1 &&
                text.right <= box.right + 1 &&
                text.top >= box.top - 1 &&
                text.bottom <= box.bottom + 1,
            ),
            insideRow:
              box.left >= bounds.left &&
              box.right <= bounds.right &&
              box.top >= bounds.top &&
              box.bottom <= bounds.bottom,
          };
        });
        return {
          cells,
          rowFits: button.scrollWidth <= button.clientWidth,
          historyFits:
            button.parentElement!.scrollWidth <=
            button.parentElement!.clientWidth,
        };
      });
      expect(layout.cells).toHaveLength(4);
      expect(layout.cells, `${route} at ${width}px`).toEqual(
        expect.arrayContaining([
          { text: quality, contained: true, insideRow: true },
        ]),
      );
      expect(
        layout.cells.every((cell) => cell.contained && cell.insideRow),
      ).toBe(true);
      expect(layout.rowFits).toBe(true);
      expect(layout.historyFits).toBe(true);
      mkdirSync("logs/report-history-layout", { recursive: true });
      await page.screenshot({
        path: `logs/report-history-layout/${route}-${width}.png`,
      });
    }
  });
}
