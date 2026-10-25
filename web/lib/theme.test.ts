import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { PALETTES } from "./theme";

const css = readFileSync(join(__dirname, "..", "app", "globals.css"), "utf8");

/** Custom properties declared in the first block whose selector matches `selector` exactly. */
function tokens(selector: string): Record<string, string> {
  const start = css.indexOf(`${selector} {`);
  if (start < 0) throw new Error(`selector ${selector} not found`);
  const body = css.slice(start, css.indexOf("}", start));
  return Object.fromEntries(
    [...body.matchAll(/(--[a-z-]+):\s*([^;]+);/g)].map((m) => [m[1], m[2].trim()]),
  );
}

/** Dark values are the dark block's overrides, falling back to the light :root value. */
const light = tokens(":root");
const darkOverrides = tokens(':root[data-theme="dark"]');
const fallback = tokens(":root:not([data-theme])");

describe("theme palettes mirror globals.css", () => {
  it.each(Object.entries(PALETTES.light.tokens))("light %s", (name, value) => {
    expect(light[name]).toBe(value);
  });

  it.each(Object.entries(PALETTES.dark.tokens))("dark %s", (name, value) => {
    expect(darkOverrides[name] ?? light[name]).toBe(value);
  });

  it("the no-script dark fallback repeats the dark block", () => {
    expect(fallback).toEqual(darkOverrides);
  });
});
