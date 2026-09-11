// @vitest-environment node
import http from "node:http";
import net from "node:net";
import { expect, test } from "vitest";
import { portOccupied } from "../../../tests/e2e/ports";

test.each(["tcp", "http-error"])("preflight detects a %s listener", async kind => {
  const server = kind === "tcp" ? net.createServer() : http.createServer((_, response) => {
    response.writeHead(503);
    response.end("Unavailable");
  });
  await new Promise<void>(resolve => server.listen(0, "127.0.0.1", resolve));
  const address = server.address();
  if (!address || typeof address === "string") throw new Error("Expected TCP address");
  try {
    expect(await portOccupied(address.port)).toBe(true);
    expect(server.listening).toBe(true);
  } finally {
    await new Promise<void>((resolve, reject) => server.close(error => error ? reject(error) : resolve()));
  }
  expect(await portOccupied(address.port)).toBe(false);
});
