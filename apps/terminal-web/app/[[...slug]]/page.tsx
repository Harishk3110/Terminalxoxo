import TerminalShell from "../../components/shell";
import { cookies } from "next/headers";
import { notFound, redirect } from "next/navigation";
import { apiOrigin } from "../../config/api-environment.mjs";

export const dynamic = "force-dynamic";

export default async function TerminalPage({ params }: { params: Promise<{ slug?: string[] }> }) {
  const { slug } = await params;
  if (!slug?.length) redirect("/overview");
  if (["principles", "products", "methodology", "about", "contact", "disclosures", "privacy", "legal"].includes(slug[0])) notFound();
  const token = (await cookies()).get("knk_session")?.value;
  let authenticated = false;
  if (token) {
    try {
      const response = await fetch(`${apiOrigin()}/api/v1/auth/session`, {
        headers: { cookie: `knk_session=${encodeURIComponent(token)}` },
        cache: "no-store", signal: AbortSignal.timeout(10000), redirect: "error",
      });
      authenticated = response.ok && (await response.json()).authenticated === true;
    } catch { /* A failed authentication service never exposes the terminal. */ }
  }
  if (!authenticated) redirect("/login");
  return <TerminalShell route={`/${slug.join("/")}`} />;
}
