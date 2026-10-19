import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
const source=await readFile(new URL("../dist/server/index.js",import.meta.url),"utf8");
JSON.parse(await readFile(new URL("../dist/.openai/hosting.json",import.meta.url),"utf8"));
const mod=await import("data:text/javascript;base64,"+Buffer.from(source).toString("base64"));
assert.equal(typeof mod.default?.fetch,"function");
console.log("Artifact is valid ESM and exports default.fetch");
