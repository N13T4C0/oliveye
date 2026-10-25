import { describe, expect, it } from "vitest";

import { MESSAGES, t } from "./i18n";

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
});
