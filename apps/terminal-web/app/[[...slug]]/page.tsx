import TerminalShell from "../../components/shell";

export default async function TerminalPage({ params }: { params: Promise<{ slug?: string[] }> }) {
  const { slug } = await params;
  return <TerminalShell route={`/${slug?.join("/") || "overview"}`} />;
}
