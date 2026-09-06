import { NextRequest } from "next/server";
import { apiOrigin } from "../../../config/api-environment.mjs";

export const dynamic = "force-dynamic";

async function proxy(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params;
  let base: string;
  try { base = apiOrigin(); } catch {
    return Response.json({ detail: "API configuration is unavailable. Configure the server API origin." }, { status: 503 });
  }
  const url = new URL(
    `/${path.map(encodeURIComponent).join("/")}`,
    base,
  );
  url.search = request.nextUrl.search;
  const headers = new Headers();
  for (const key of ["content-type", "cookie", "x-correlation-id", "origin"]) {
    const value = request.headers.get(key);
    if (value) headers.set(key, value);
  }
  try {
    const upstream = await fetch(url, {
      method: request.method,
      headers,
      body: ["POST", "PUT", "DELETE"].includes(request.method)
        ? await request.arrayBuffer()
        : undefined,
      cache: "no-store",
      signal: request.signal,
      redirect: "manual",
    });
    const responseHeaders = new Headers();
    for (const key of [
      "content-type",
      "content-disposition",
      "set-cookie",
      "x-correlation-id",
    ]) {
      const value = upstream.headers.get(key);
      if (value) responseHeaders.set(key, value);
    }
    responseHeaders.set("Cache-Control", "no-store");
    return new Response(upstream.body, {
      status: upstream.status,
      headers: responseHeaders,
    });
  } catch {
    return Response.json(
      { detail: "API is unavailable. Check the configured API service." },
      { status: 503 },
    );
  }
}

export { proxy as GET, proxy as POST, proxy as PUT, proxy as DELETE };
