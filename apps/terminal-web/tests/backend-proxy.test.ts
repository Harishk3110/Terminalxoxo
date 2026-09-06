import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { DELETE, GET, POST, PUT } from "../app/backend/[...path]/route";
import { KnkApiClient } from "@knk/api-client";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe("backend proxy mutation contract", () => {
  it.each([
    ["POST", POST],
    ["PUT", PUT],
    ["DELETE", DELETE],
  ] as const)(
    "forwards %s JSON, credentials and query parameters",
    async (method, handler) => {
      vi.stubEnv("KNK_API_URL", "http://127.0.0.1:8001");
      const fetch = vi
        .fn()
        .mockResolvedValue(
          new Response(JSON.stringify({ audit_version: 2 }), {
            status: 200,
            headers: {
              "Content-Type": "application/json",
              "X-Correlation-Id": "response-correlation",
            },
          }),
        );
      vi.stubGlobal("fetch", fetch);
      const payload = {
        expected_version: 1,
        reason: "Correct statement quantity",
        changes: { quantity: "8.125" },
      };
      const request = new NextRequest(
        "http://localhost/backend/api/v1/portfolios/book/transactions/txn?end=2026-01-09",
        {
          method,
          headers: {
            "Content-Type": "application/json",
            Cookie: "knk-session=local-test",
            "X-Correlation-Id": "request-correlation",
            Origin: "http://localhost",
          },
          body: JSON.stringify(payload),
        },
      );
      const response = await handler(request, {
        params: Promise.resolve({
          path: ["api", "v1", "portfolios", "book", "transactions", "txn"],
        }),
      });
      expect(fetch).toHaveBeenCalledOnce();
      const [url, options] = fetch.mock.calls[0] as [URL, RequestInit];
      expect(url.toString()).toBe(
        "http://127.0.0.1:8001/api/v1/portfolios/book/transactions/txn?end=2026-01-09",
      );
      expect(options.method).toBe(method);
      expect(
        JSON.parse(new TextDecoder().decode(options.body as ArrayBuffer)),
      ).toEqual(payload);
      expect(new Headers(options.headers).get("cookie")).toBe(
        "knk-session=local-test",
      );
      expect(new Headers(options.headers).get("x-correlation-id")).toBe(
        "request-correlation",
      );
      expect(options.cache).toBe("no-store");
      expect(options.redirect).toBe("manual");
      expect(response.headers.get("x-correlation-id")).toBe(
        "response-correlation",
      );
      expect(response.headers.get("cache-control")).toBe("no-store");
      expect(await response.json()).toEqual({ audit_version: 2 });
    },
  );

  it("does not send a request body for GET", async () => {
    const fetch = vi.fn().mockResolvedValue(new Response("{}"));
    vi.stubGlobal("fetch", fetch);
    await GET(new NextRequest("http://localhost/backend/api/v1/portfolios"), {
      params: Promise.resolve({ path: ["api", "v1", "portfolios"] }),
    });
    expect(fetch.mock.calls[0][1].method).toBe("GET");
    expect(fetch.mock.calls[0][1].body).toBeUndefined();
  });

  it("preserves upstream conflict status and error details", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(JSON.stringify({ detail: "Transaction changed" }), {
            status: 409,
            headers: { "Content-Type": "application/json" },
          }),
        ),
    );
    const response = await PUT(
      new NextRequest(
        "http://localhost/backend/api/v1/portfolios/book/transactions/txn",
        { method: "PUT", body: "{}" },
      ),
      {
        params: Promise.resolve({
          path: ["api", "v1", "portfolios", "book", "transactions", "txn"],
        }),
      },
    );
    expect(response.status).toBe(409);
    expect(await response.json()).toEqual({ detail: "Transaction changed" });
  });

  it("returns an explicit service-unavailable response on network failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new Error("connect ECONNREFUSED")),
    );
    const response = await GET(
      new NextRequest("http://localhost/backend/api/v1/portfolios"),
      { params: Promise.resolve({ path: ["api", "v1", "portfolios"] }) },
    );
    expect(response.status).toBe(503);
    expect((await response.json()).detail).toContain("API is unavailable");
  });

  it("does not forward arbitrary request headers upstream", async () => {
    const fetch = vi.fn().mockResolvedValue(new Response("{}"));
    vi.stubGlobal("fetch", fetch);
    await GET(
      new NextRequest("http://localhost/backend/api/v1/portfolios", {
        headers: {
          "x-untrusted-routing": "external.example",
          "x-forwarded-host": "external.example",
        },
      }),
      { params: Promise.resolve({ path: ["api", "v1", "portfolios"] }) },
    );
    const headers = new Headers(fetch.mock.calls[0][1].headers);
    expect(headers.has("x-untrusted-routing")).toBe(false);
    expect(headers.has("x-forwarded-host")).toBe(false);
  });
});

describe("API client mutation verbs", () => {
  it.each(["post", "put", "delete"] as const)(
    "sends %s with JSON and same client credentials contract",
    async (method) => {
      const fetch = vi
        .fn()
        .mockResolvedValue(
          new Response(JSON.stringify({ saved: true }), { status: 200 }),
        );
      vi.stubGlobal("fetch", fetch);
      const client = new KnkApiClient("http://api.test");
      const result = await client[method]("/ledger", { amount: "1.125" });
      expect(result).toEqual({ saved: true });
      const [url, options] = fetch.mock.calls[0];
      expect(url).toBe("http://api.test/ledger");
      expect(options.method).toBe(method.toUpperCase());
      expect(options.credentials).toBe("include");
      expect(options.headers["Content-Type"]).toBe("application/json");
      expect(JSON.parse(options.body)).toEqual({ amount: "1.125" });
    },
  );

  it("keeps existing multipart uploads untouched", async () => {
    const fetch = vi.fn().mockResolvedValue(new Response("{}"));
    vi.stubGlobal("fetch", fetch);
    const form = new FormData();
    form.set("licence", "Test data");
    await new KnkApiClient("http://api.test").post("/upload", form);
    expect(fetch.mock.calls[0][1].body).toBe(form);
    expect(fetch.mock.calls[0][1].headers).toBeUndefined();
  });

  it("does not report success for rejected mutations", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(JSON.stringify({ detail: "Version conflict" }), {
            status: 409,
          }),
        ),
    );
    await expect(
      new KnkApiClient("http://api.test").put("/ledger", {}),
    ).rejects.toThrow("Version conflict");
  });
});
