import { NextRequest } from "next/server";

export const dynamic = "force-dynamic";

async function proxy(
  request: NextRequest,
  { params }: { params: { path: string[] } },
) {
  const base = process.env.KNK_API_URL || "http://127.0.0.1:8000";
  const url = new URL(
    `/${params.path.map(encodeURIComponent).join("/")}`,
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
      body: request.method === "POST" ? await request.arrayBuffer() : undefined,
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
      { detail: "API is unavailable. Check the local API service." },
      { status: 503 },
    );
  }
}

export { proxy as GET, proxy as POST };
