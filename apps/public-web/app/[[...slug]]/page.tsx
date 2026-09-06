import { ModeBadge, SecurityNotice } from "@knk/design-system";
import { publicResearch } from "@knk/domain";
import { ArrowRight, FileText, LockKeyhole, Mail, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { products, publicRoutes } from "../../lib/content";

type PageProps = {
  params: Promise<{
    slug?: string[];
  }>;
};

function routeFromParams(params: Awaited<PageProps["params"]>) {
  return `/${params.slug?.join("/") ?? ""}`.replace(/\/$/, "") || "/";
}

function Header() {
  return (
    <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
        <Link href="/" className="text-sm font-bold uppercase tracking-normal text-slate-950">
          KnK Capital
        </Link>
        <nav className="hidden items-center gap-5 text-sm text-slate-600 md:flex">
          <Link href="/principles">Principles</Link>
          <Link href="/products">Products</Link>
          <Link href="/research">Research</Link>
          <Link href="/methodology">Methodology</Link>
          <Link href="/disclosures">Disclosures</Link>
        </nav>
        <ModeBadge>Public</ModeBadge>
      </div>
    </header>
  );
}

function Hero() {
  return (
    <section className="bg-white">
      <div className="mx-auto grid min-h-[620px] max-w-7xl grid-cols-1 gap-8 px-4 py-12 lg:grid-cols-[0.9fr_1.1fr] lg:items-center">
        <div>
          <p className="text-sm font-semibold uppercase text-copper">Singapore proprietary investment operation</p>
          <h1 className="mt-4 max-w-3xl text-5xl font-semibold tracking-normal text-slate-950 md:text-6xl">
            KnK Capital
          </h1>
          <p className="mt-5 max-w-2xl text-lg leading-8 text-slate-600">
            A private investment platform built around research discipline, risk transparency, deterministic demo data, and strict public/private separation.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/products/terminal" className="inline-flex items-center gap-2 rounded-md bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white">
              View terminal product <ArrowRight className="h-4 w-4" />
            </Link>
            <Link href="/research" className="inline-flex items-center gap-2 rounded-md border border-slate-300 px-4 py-2.5 text-sm font-semibold text-slate-900">
              Public research <FileText className="h-4 w-4" />
            </Link>
          </div>
        </div>
        <div className="terminal-visual overflow-hidden rounded-md border border-slate-900 shadow-2xl">
          <div className="border-b border-slate-700 bg-slate-950 px-4 py-3 text-xs font-semibold uppercase text-slate-300">
            KnK Capital Terminal | Demo View
          </div>
          <div className="grid gap-3 p-4 md:grid-cols-3">
            {["DEMO DATA", "SGD 70,000", "PAPER ONLY"].map((label) => (
              <div key={label} className="rounded border border-slate-700 bg-slate-900/80 p-3">
                <p className="text-xs uppercase text-slate-400">{label}</p>
                <div className="mt-3 h-16 rounded bg-slate-800">
                  <div className="h-full w-2/3 rounded bg-cyan-600/70" />
                </div>
              </div>
            ))}
          </div>
          <div className="grid gap-3 p-4 pt-0 md:grid-cols-[1.4fr_0.6fr]">
            <div className="h-56 rounded border border-slate-700 bg-slate-900/90 p-4">
              <div className="h-full rounded bg-[linear-gradient(135deg,#0e7490_0%,#0f172a_45%,#b45309_100%)] opacity-80" />
            </div>
            <div className="space-y-3">
              {["Risk", "Research", "Reports", "Health"].map((item) => (
                <div key={item} className="rounded border border-slate-700 bg-slate-900/90 px-3 py-4 text-sm font-semibold text-slate-200">
                  {item}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function PageFrame({ children }: { children: React.ReactNode }) {
  return (
    <>
      <Header />
      {children}
      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-8 text-sm text-slate-500 md:flex-row md:items-center md:justify-between">
          <span>© 2026 KnK Capital. Public demo site.</span>
          <div className="flex gap-4">
            <Link href="/privacy">Privacy</Link>
            <Link href="/legal">Legal</Link>
            <Link href="/disclosures">Disclosures</Link>
          </div>
        </div>
      </footer>
    </>
  );
}

function HomePage() {
  return (
    <PageFrame>
      <Hero />
      <main className="mx-auto max-w-7xl px-4 py-10">
        <div className="grid gap-4 md:grid-cols-3">
          <section className="rounded-md border border-slate-200 bg-white p-5">
            <ShieldCheck className="h-5 w-5 text-harbor" />
            <h2 className="mt-3 text-lg font-semibold">Risk-led research</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">Portfolio decisions are framed through exposure, drawdown, stress, liquidity, and data provenance.</p>
          </section>
          <section className="rounded-md border border-slate-200 bg-white p-5">
            <LockKeyhole className="h-5 w-5 text-copper" />
            <h2 className="mt-3 text-lg font-semibold">Private by default</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">Public publishing is explicit and sanitized. Private holdings and active signals never appear publicly.</p>
          </section>
          <SecurityNotice />
        </div>
      </main>
    </PageFrame>
  );
}

function SimplePage({ title, body }: { title: string; body: string }) {
  return (
    <PageFrame>
      <main className="mx-auto max-w-5xl px-4 py-14">
        <h1 className="text-4xl font-semibold tracking-normal text-slate-950">{title}</h1>
        <p className="mt-5 max-w-3xl text-lg leading-8 text-slate-600">{body}</p>
      </main>
    </PageFrame>
  );
}

function ProductsPage({ slug }: { slug?: string }) {
  const product = slug ? products.find((item) => item.slug === slug) : undefined;
  if (slug && !product) notFound();
  return (
    <PageFrame>
      <main className="mx-auto max-w-7xl px-4 py-14">
        <h1 className="text-4xl font-semibold tracking-normal">{product?.name ?? "Products"}</h1>
        <p className="mt-4 max-w-3xl text-lg leading-8 text-slate-600">
          {product?.summary ?? "KnK Capital products are private operating tools and sanitized public outputs built around research, portfolio risk, and reporting discipline."}
        </p>
        <div className="mt-8 grid gap-4 md:grid-cols-3">
          {(product ? [product] : products).map((item) => (
            <Link key={item.slug} href={`/products/${item.slug}`} className="rounded-md border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="text-lg font-semibold">{item.name}</h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">{item.summary}</p>
            </Link>
          ))}
        </div>
      </main>
    </PageFrame>
  );
}

function ResearchPage({ slug }: { slug?: string }) {
  const article = slug ? publicResearch.find((item) => item.slug === slug) : undefined;
  if (slug && !article) notFound();
  return (
    <PageFrame>
      <main className="mx-auto max-w-7xl px-4 py-14">
        <h1 className="text-4xl font-semibold tracking-normal">{article?.title ?? "Public Research"}</h1>
        <p className="mt-4 max-w-3xl text-lg leading-8 text-slate-600">
          {article?.summary ?? "Published research is copied from private drafts only after sanitization and explicit approval."}
        </p>
        <div className="mt-8 grid gap-4 md:grid-cols-2">
          {(article ? [article] : publicResearch).map((item) => (
            <Link key={item.slug} href={`/research/${item.slug}`} className="rounded-md border border-slate-200 bg-white p-5 shadow-sm">
              <p className="text-xs font-semibold uppercase text-copper">{item.status} | {item.publishedAt}</p>
              <h2 className="mt-2 text-xl font-semibold">{item.title}</h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">{item.summary}</p>
            </Link>
          ))}
        </div>
      </main>
    </PageFrame>
  );
}

export default async function PublicPage({ params }: PageProps) {
  const route = routeFromParams(await params);
  if (!publicRoutes.includes(route)) notFound();

  if (route === "/") return <HomePage />;
  if (route === "/products") return <ProductsPage />;
  if (route.startsWith("/products/")) return <ProductsPage slug={route.split("/")[2]} />;
  if (route === "/research") return <ResearchPage />;
  if (route.startsWith("/research/")) return <ResearchPage slug={route.split("/")[2]} />;
  if (route === "/contact") {
    return <SimplePage title="Contact" body="For KnK Capital enquiries, use the private administrator channel configured for the deployment. This public demo does not collect investor subscriptions or client onboarding data." />;
  }
  if (route === "/legal") {
    return <SimplePage title="Legal" body="KnK Capital Terminal is presented as demo software. It is not an offer, solicitation, advisory service, or public fund product." />;
  }
  if (route === "/privacy") {
    return <SimplePage title="Privacy" body="Public pages do not embed private terminal data, broker data, provider secrets, or unpublished research drafts." />;
  }
  if (route === "/disclosures") {
    return <SimplePage title="Disclosures" body="Demo market and portfolio figures are synthetic and labelled. Connected provider datasets must show provider, dataset, timestamps, currency, and quality state." />;
  }
  if (route === "/about") {
    return <SimplePage title="About KnK Capital" body="KnK Capital is modelled here as a Singapore proprietary investment operation using owner capital only in version one." />;
  }
  if (route === "/principles") {
    return <SimplePage title="Investment Principles" body="Research discipline, data honesty, risk-first construction, no hidden broker action paths, and traceable decisions guide the platform." />;
  }
  if (route === "/methodology") {
    return <SimplePage title="Methodology" body="The methodology library documents data lineage, valuation assumptions, risk measures, model validation, backtesting controls, and publishing sanitization." />;
  }

  return <SimplePage title="KnK Capital" body="Sanitized public content for KnK Capital." />;
}
