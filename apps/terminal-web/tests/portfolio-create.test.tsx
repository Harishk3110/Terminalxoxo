// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { knkApi } from "@knk/api-client";
import {
  newPortfolioDraft,
  portfolioCreatePayload,
  PortfolioCreateDialog,
} from "../components/ledger/portfolio-create";
import { creationOptions, researchLedger } from "./fixtures/portfolios";
import { renderLedger } from "./ledger-render";

beforeEach(() => {
  Object.defineProperties(HTMLDialogElement.prototype, {
    showModal: {
      configurable: true,
      value: function (this: HTMLDialogElement) {
        this.setAttribute("open", "");
      },
    },
    close: {
      configurable: true,
      value: function (this: HTMLDialogElement) {
        this.removeAttribute("open");
      },
    },
  });
  vi.spyOn(knkApi, "get").mockResolvedValue(creationOptions);
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

async function fillRequired() {
  await userEvent.type(
    await screen.findByLabelText("Portfolio code"),
    "research",
  );
  await userEvent.type(
    screen.getByLabelText("Portfolio name"),
    "Research allocation",
  );
  await userEvent.type(
    screen.getByLabelText("Opening contribution"),
    "1000.12345678",
  );
}

describe("explicit portfolio creation", () => {
  it("leaves capital empty and uses server date rather than copying the default book's contribution", () => {
    const draft = newPortfolioDraft(creationOptions);
    expect(draft.reference_capital).toBe("");
    expect(draft.opening_date).toBe("2026-09-06");
    expect(draft.code).toBe("");
    expect(draft.benchmark).toBe("SPY");
    expect(draft.base_currency).toBe("SGD");
    expect(draft.allow_short).toBe(false);
    expect(draft.capitalize_commissions).toBe(true);
    expect(draft.capitalize_fees).toBe(false);
  });

  it("uses configured alternatives when SGD or SPY are not available", () => {
    const options = {
      ...creationOptions,
      currencies: ["EUR"],
      benchmarks: [creationOptions.benchmarks[0]],
    };
    const draft = newPortfolioDraft(options);
    expect(draft.base_currency).toBe("EUR");
    expect(draft.benchmark).toBe("AAPL");
  });

  it("normalizes identifiers but never converts a capital string through floating point", () => {
    const draft = {
      ...newPortfolioDraft(creationOptions),
      code: " research ",
      name: " Allocation ",
      reference_capital: " 999999999.12345678 ",
      allow_short: true,
      capitalize_fees: true,
    };
    expect(portfolioCreatePayload(draft)).toEqual({
      ...draft,
      code: "RESEARCH",
      name: "Allocation",
      reference_capital: "999999999.12345678",
    });
    expect(draft.code).toBe(" research ");
  });

  it("exposes the supported currencies, benchmark list, opening policy and date limit", async () => {
    renderLedger(
      <PortfolioCreateDialog onClose={() => {}} onCreated={() => {}} />,
    );
    await screen.findByLabelText("Portfolio code");
    expect(knkApi.get).toHaveBeenCalledWith(
      "/api/v1/portfolios/creation-options",
      expect.any(AbortSignal),
    );
    expect(
      (screen.getByLabelText("Opening date") as HTMLInputElement).max,
    ).toBe("2026-09-06");
    expect(screen.getByText("Opening date / UTC")).toBeTruthy();
    expect(
      (screen.getByLabelText("Opening contribution") as HTMLInputElement).value,
    ).toBe("");
    expect(
      (screen.getByLabelText("Base currency") as HTMLSelectElement).options
        .length,
    ).toBe(3);
    expect(
      (
        screen.getByRole("button", {
          name: "Create internal ledger",
        }) as HTMLButtonElement
      ).disabled,
    ).toBe(true);
    await userEvent.selectOptions(
      screen.getByLabelText("Base currency"),
      "USD",
    );
    expect(screen.getByText("Opening contribution / USD")).toBeTruthy();
  });

  it("posts the exact requested contribution and explicit policy once before handing back persisted metadata", async () => {
    const post = vi.spyOn(knkApi, "post").mockResolvedValue(researchLedger);
    const created = vi.fn();
    renderLedger(
      <PortfolioCreateDialog onClose={() => {}} onCreated={created} />,
    );
    await fillRequired();
    await userEvent.selectOptions(
      screen.getByLabelText("Base currency"),
      "USD",
    );
    await userEvent.selectOptions(
      screen.getByLabelText("Opening cost-basis method"),
      "FIFO",
    );
    await userEvent.click(screen.getByLabelText("Allow short positions"));
    await userEvent.click(
      screen.getByLabelText("Capitalize opening-policy commissions"),
    );
    await userEvent.click(
      screen.getByLabelText("Capitalize opening-policy fees"),
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Create internal ledger" }),
    );
    await waitFor(() => expect(created).toHaveBeenCalledWith(researchLedger));
    expect(post).toHaveBeenCalledTimes(1);
    expect(post).toHaveBeenCalledWith("/api/v1/portfolios", {
      code: "RESEARCH",
      name: "Research allocation",
      base_currency: "USD",
      reference_capital: "1000.12345678",
      opening_date: "2026-09-06",
      benchmark: "SPY",
      allow_short: true,
      method: "FIFO",
      capitalize_commissions: false,
      capitalize_fees: true,
    });
  });

  it("preserves the draft when a duplicate code or storage boundary is rejected", async () => {
    vi.spyOn(knkApi, "post").mockRejectedValue(
      new Error("Record conflicts with an existing identifier or version"),
    );
    const created = vi.fn();
    renderLedger(
      <PortfolioCreateDialog onClose={() => {}} onCreated={created} />,
    );
    await fillRequired();
    await userEvent.click(
      screen.getByRole("button", { name: "Create internal ledger" }),
    );
    expect((await screen.findByRole("alert")).textContent).toContain(
      "Record conflicts",
    );
    expect(
      (screen.getByLabelText("Portfolio code") as HTMLInputElement).value,
    ).toBe("RESEARCH");
    expect(
      (screen.getByLabelText("Opening contribution") as HTMLInputElement).value,
    ).toBe("1000.12345678");
    expect(created).not.toHaveBeenCalled();
    expect(
      (
        screen.getByRole("button", {
          name: "Create internal ledger",
        }) as HTMLButtonElement
      ).disabled,
    ).toBe(false);
  });

  it("prevents cancellation and duplicate submission while the opening ledger write is pending", async () => {
    let finish!: (value: typeof researchLedger) => void;
    vi.spyOn(knkApi, "post").mockImplementation(
      () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    );
    const close = vi.fn();
    renderLedger(
      <PortfolioCreateDialog onClose={close} onCreated={() => {}} />,
    );
    await fillRequired();
    await userEvent.click(
      screen.getByRole("button", { name: "Create internal ledger" }),
    );
    const cancel = screen.getByRole("button", {
      name: "Cancel portfolio creation",
    }) as HTMLButtonElement;
    expect(cancel.disabled).toBe(true);
    await userEvent.click(cancel);
    fireEvent(
      screen.getByRole("dialog"),
      new Event("cancel", { cancelable: true }),
    );
    expect(close).not.toHaveBeenCalled();
    expect(
      (
        screen.getByRole("button", {
          name: "Creating ledger...",
        }) as HTMLButtonElement
      ).disabled,
    ).toBe(true);
    finish(researchLedger);
    await waitFor(() => expect(cancel.disabled).toBe(false));
    await userEvent.click(cancel);
    expect(close).toHaveBeenCalledTimes(1);
  });

  it("does not expose a submit form if creation options cannot be fetched", async () => {
    vi.mocked(knkApi.get).mockRejectedValue(
      new Error("Authentication required"),
    );
    renderLedger(
      <PortfolioCreateDialog onClose={() => {}} onCreated={() => {}} />,
    );
    expect((await screen.findByRole("alert")).textContent).toBe(
      "Authentication required",
    );
    expect(
      screen.queryByRole("button", { name: "Create internal ledger" }),
    ).toBeNull();
    expect(screen.queryByLabelText("Opening contribution")).toBeNull();
  });
});
