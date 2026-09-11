// @vitest-environment jsdom
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { cleanup, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { knkApi } from "@knk/api-client";
import { AccountSecurity } from "../components/account-security";
import { renderLedger } from "./ledger-render";

beforeEach(() => {
  vi.spyOn(knkApi, "get").mockResolvedValue({
    totp_enabled: false,
    recovery_codes_remaining: 0,
    sessions: [],
  });
  vi.spyOn(knkApi, "post").mockResolvedValue({});
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

it("requires a confirmed enrollment before showing enabled state", async () => {
  const user = userEvent.setup();
  vi.mocked(knkApi.post)
    .mockResolvedValueOnce({
      secret: "TESTAUTHENTICATOR",
      expires_at: "2026-09-11T10:00:00Z",
    })
    .mockResolvedValueOnce({ recovery_codes: ["one-time-recovery"] });
  renderLedger(<AccountSecurity />);
  await user.click(
    await screen.findByRole("button", { name: "Enable authenticator" }),
  );
  await user.type(
    screen.getByLabelText("Current password"),
    "synthetic-test-password",
  );
  await user.click(screen.getByRole("button", { name: "Create enrollment" }));
  expect(await screen.findByDisplayValue("TESTAUTHENTICATOR")).toBeTruthy();
  await user.type(screen.getByLabelText("Authenticator code"), "123456");
  await user.click(
    screen.getByRole("button", { name: "Confirm authenticator" }),
  );
  expect(await screen.findByText("one-time-recovery")).toBeTruthy();
  expect(knkApi.post).toHaveBeenCalledWith("/api/v1/auth/totp/confirm", {
    password: "synthetic-test-password",
    totp_code: "123456",
  });
  await user.click(
    screen.getByRole("button", { name: "Dismiss recovery codes" }),
  );
  expect(screen.queryByText("one-time-recovery")).toBeNull();
  expect(screen.queryByDisplayValue("TESTAUTHENTICATOR")).toBeNull();
});

it("does not hide failed reauthentication and allows cancellation", async () => {
  const user = userEvent.setup();
  vi.mocked(knkApi.post).mockRejectedValue(
    new Error("Invalid password or one-time proof"),
  );
  renderLedger(<AccountSecurity />);
  await user.click(
    await screen.findByRole("button", { name: "Enable authenticator" }),
  );
  await user.type(screen.getByLabelText("Current password"), "wrong");
  await user.click(screen.getByRole("button", { name: "Create enrollment" }));
  expect(await screen.findByRole("alert")).toHaveProperty(
    "textContent",
    "Invalid password or one-time proof",
  );
  await user.click(screen.getByRole("button", { name: "Cancel" }));
  expect(screen.queryByLabelText("Current password")).toBeNull();
});

it("sends only the selected recovery proof when replacing codes", async () => {
  const user = userEvent.setup();
  vi.mocked(knkApi.get).mockResolvedValue({
    totp_enabled: true,
    recovery_codes_remaining: 7,
    sessions: [],
  });
  renderLedger(<AccountSecurity />);
  await user.click(
    await screen.findByRole("button", { name: "Replace recovery codes" }),
  );
  await user.type(
    screen.getByLabelText("Current password"),
    "synthetic-test-password",
  );
  await user.click(screen.getByRole("checkbox", { name: "Use recovery code" }));
  await user.type(
    screen.getByLabelText("Recovery code", { exact: true }),
    "synthetic-recovery",
  );
  await user.click(
    screen.getByRole("button", { name: "Replace codes" }),
  );
  await waitFor(() =>
    expect(knkApi.post).toHaveBeenCalledWith("/api/v1/auth/recovery-codes", {
      password: "synthetic-test-password",
      recovery_code: "synthetic-recovery",
    }),
  );
});
