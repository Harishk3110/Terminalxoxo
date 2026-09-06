import TerminalShell from "../../components/shell";

export default function TerminalPage({ params }: { params: { slug?: string[] } }) {
  return <TerminalShell route={`/${params.slug?.join("/") || "overview"}`} />;
}
