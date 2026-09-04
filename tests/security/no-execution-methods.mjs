import { readFileSync } from "node:fs";
import { join, relative } from "node:path";
import { readdirSync, statSync } from "node:fs";

const root = process.cwd();
const scanRoots = ["apps", "packages", "services"];
const skipped = new Set(["node_modules", ".next", "dist", "coverage", "__pycache__", "tests"]);
const extensions = new Set([".ts", ".tsx", ".js", ".mjs", ".py", ".json", ".md"]);
const forbidden = [
  "place" + "Order",
  "cancel" + "Order",
  "req" + "Global" + "Cancel",
  "transmit" + "Order",
  "modify" + "Order",
  "submit" + "Order",
  "execute" + "Trade",
  "auto" + "Rebalance",
  "auto" + "Hedge",
  "Buy" + " button",
  "Sell" + " button",
  "Submit" + " order",
  "Transmit" + " order",
  "Cancel" + " broker order",
  "Live" + " execution toggle"
];

function extension(path) {
  const index = path.lastIndexOf(".");
  return index === -1 ? "" : path.slice(index);
}

function walk(dir, files = []) {
  for (const entry of readdirSync(dir)) {
    if (skipped.has(entry)) continue;
    const path = join(dir, entry);
    const stat = statSync(path);
    if (stat.isDirectory()) walk(path, files);
    if (stat.isFile() && extensions.has(extension(path))) files.push(path);
  }
  return files;
}

const violations = [];
for (const scanRoot of scanRoots) {
  const absolute = join(root, scanRoot);
  for (const file of walk(absolute)) {
    const text = readFileSync(file, "utf8");
    for (const pattern of forbidden) {
      if (text.includes(pattern)) {
        violations.push(`${relative(root, file)} contains ${pattern}`);
      }
    }
  }
}

if (violations.length > 0) {
  console.error(violations.join("\n"));
  process.exit(1);
}

console.log("No forbidden broker action method names found in application source.");
