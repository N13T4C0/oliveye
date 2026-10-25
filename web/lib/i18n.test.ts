import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { MESSAGES, t, type MessageKey } from "./i18n";

const placeholders = (text: string) => [...text.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();

describe("i18n", () => {
  it("has every message in both languages", () => {
    expect(Object.keys(MESSAGES.en).sort()).toEqual(Object.keys(MESSAGES.es).sort());
    for (const value of Object.values(MESSAGES.en)) expect(value.length).toBeGreaterThan(0);
  });

  it("fills placeholders", () => {
    expect(t("es", "aforoCloser", { n: 6, total: 9 })).toBe(
      "El aforo acertó más en 6 de 9 campañas",
    );
    expect(t("en", "municipalities", { n: 86 })).toBe("86 municipalities");
  });

  it("uses the same placeholders in both languages", () => {
    for (const key of Object.keys(MESSAGES.es) as MessageKey[]) {
      expect(placeholders(MESSAGES.en[key]), key).toEqual(placeholders(MESSAGES.es[key]));
    }
  });

  it("never calls a message with placeholders without values", () => {
    // Catches `t(lang, "key")` (or a ternary of keys) whose text has a {placeholder}: the page
    // would show the raw "{name}" to visitors.
    const dir = join(__dirname, "..", "components");
    for (const file of readdirSync(dir).filter((f) => f.endsWith(".tsx"))) {
      const source = readFileSync(join(dir, file), "utf8");
      for (const call of source.matchAll(/\bt\(lang, ([^(),]+)\)/g)) {
        for (const key of call[1].matchAll(/"(\w+)"/g)) {
          const text = MESSAGES.es[key[1] as MessageKey];
          if (text !== undefined) expect(placeholders(text), `${file}: ${key[1]}`).toEqual([]);
        }
      }
    }
  });
});
