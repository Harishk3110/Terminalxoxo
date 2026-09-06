import registry from "../../../services/api/app/data/functions.json";

export interface TerminalFunction {
  mnemonic: string;
  name: string;
  description: string;
  category: string;
  keywords: string[];
  aliases: string[];
  requiresSecurity: boolean;
  supportsMultipleSecurities: boolean;
  supportedAssetClasses: string[];
  route: string;
  implementationStatus:
    | "available"
    | "demo_available"
    | "provider_required"
    | "in_development";
  providerRequirements: string[];
}

export const terminalFunctions = registry as TerminalFunction[];
export const functionRoute = (fn: TerminalFunction, instrumentId?: string) =>
  fn.route.replace("{instrumentId}", instrumentId ?? "AAPL");
export function findTerminalFunctions(query: string): TerminalFunction[] {
  const term = query.trim().toLowerCase();
  return terminalFunctions.filter((fn) =>
    [fn.mnemonic, fn.name, ...fn.keywords, ...fn.aliases]
      .join(" ")
      .toLowerCase()
      .includes(term),
  );
}
