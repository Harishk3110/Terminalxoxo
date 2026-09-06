import { describe, expect, it } from "vitest";
import { apiOrigin } from "../config/api-environment.mjs";

describe("API deployment configuration", () => {
  it("allows the local default only in an explicit local environment", () => {
    expect(apiOrigin({ NEXT_PUBLIC_APP_ENV: "local" })).toBe("http://127.0.0.1:8000");
    expect(() => apiOrigin({ NODE_ENV: "production" })).toThrow("Set KNK_API_URL");
    expect(() => apiOrigin({})).toThrow("Set KNK_API_URL");
  });
  it("accepts a public HTTPS origin without leaking it into browser requests", () => {
    expect(apiOrigin({ VERCEL: "1", KNK_API_URL: "https://api.example.com/" })).toBe("https://api.example.com");
    expect(apiOrigin({ NEXT_PUBLIC_APP_ENV: "production-paper", NEXT_PUBLIC_API_BASE_URL: "https://api.example.com" })).toBe("https://api.example.com");
  });
  it.each(["http://api.example.com", "https://localhost", "https://localhost.", "https://app.localhost", "https://127.0.0.1", "https://127.1", "https://2130706433", "https://0.0.0.0", "https://10.1.2.3", "https://192.168.1.1", "https://172.31.2.3", "https://169.254.169.254", "https://[::1]", "https://[::]", "https://[::ffff:127.0.0.1]", "https://[fd00::1]", "https://api.internal", "https://api.local", "https://api"])("rejects unsafe hosted origin %s even with a local-mode flag", (url) => {
    expect(() => apiOrigin({ VERCEL: "1", NEXT_PUBLIC_APP_ENV: "local", KNK_API_URL: url })).toThrow();
  });
  it.each(["https://user:secret@api.example.com", "https://api.example.com/api", "https://api.example.com/?token=bad", "https://api.example.com/#fragment", "file:///data", "not-a-url"])("rejects malformed or credential-bearing configuration %s", (url) => {
    expect(() => apiOrigin({ NEXT_PUBLIC_APP_ENV: "local", KNK_API_URL: url })).toThrow();
  });
});
