// Shared --help guard for the CLI tools. A tool opts in with
//   import "./_help.mjs";
// as its FIRST import: ES modules evaluate imports in order, so this runs
// before the tool's own imports or any of its work, prints the tool's leading
// comment block, and exits 0. Without it, `node tools/x.mjs --help` ignores
// the flag and runs the whole tool (some of them rewrite the font library).
// Importing a tool from a test never trips it: argv carries no -h/--help.
import { readFileSync } from "node:fs";

const args = process.argv.slice(2);
if (args.includes("--help") || args.includes("-h")) {
  let text = "";
  try {
    const lines = readFileSync(process.argv[1], "utf8").split(/\r?\n/);
    const out = [];
    for (const line of lines) {
      if (line.startsWith("#!")) continue;
      if (line.startsWith("//")) out.push(line.replace(/^\/\/ ?/, ""));
      else break;
    }
    text = out.join("\n").trim();
  } catch { /* fall through to the bare usage line */ }
  console.log(text || `Usage: node ${process.argv[1]}`);
  process.exit(0);
}
