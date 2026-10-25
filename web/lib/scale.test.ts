import { describe, expect, it } from "vitest";

import {
  campaignWindow,
  classOf,
  colourOf,
  formatIndex,
  formatSignedPercent,
  formatTonnes,
  NO_DATA,
  quantileBreaks,
  RAMPS,
} from "./scale";

describe("quantileBreaks", () => {
  it("splits values into groups of similar size", () => {
    const values = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
    expect(quantileBreaks(values, 2)).toEqual([5]);
    expect(quantileBreaks(values, 5)).toEqual([2, 4, 6, 8]);
  });

  it("ignores missing values and handles empty input", () => {
    expect(quantileBreaks([Number.NaN, 1, 3], 2)).toEqual([2]);
    expect(quantileBreaks([], 6)).toEqual([]);
  });
});

describe("classOf / colourOf", () => {
  const breaks = [0.3, 0.35, 0.4];

  it("finds the class of a value, values on a break go up", () => {
    expect(classOf(0.2, breaks)).toBe(0);
    expect(classOf(0.35, breaks)).toBe(2);
    expect(classOf(0.9, breaks)).toBe(3);
  });

  it("never invents a colour for missing data", () => {
    expect(classOf(null, breaks)).toBeNull();
    expect(colourOf(undefined, breaks, RAMPS.ndvi_spring)).toBe(NO_DATA);
  });
});

describe("formatting", () => {
  it("formats tonnes per language", () => {
    expect(formatTonnes(392348, "es")).toBe("392.300 t");
    expect(formatTonnes(392348, "en")).toBe("392,300 t");
    expect(formatTonnes(392348, "es", true)).toBe("392 kt");
    expect(formatTonnes(96468, "es", true)).toBe("96,5 kt");
    expect(formatTonnes(null, "es")).toBe("—");
  });

  it("formats an index with two decimals", () => {
    expect(formatIndex(0.4127, "es")).toBe("0,41");
    expect(formatIndex(-0.068, "en")).toBe("-0.07");
  });
});

describe("campaignWindow", () => {
  it("covers October of the previous year to August (the data cut)", () => {
    expect(campaignWindow("2025/26")).toEqual({ start: "2024-10", end: "2025-08" });
  });
});

describe("formatSignedPercent", () => {
  it("signs over- and under-estimates with a real minus sign", () => {
    expect(formatSignedPercent(154.8, "es")).toBe("+155\u00a0%");
    expect(formatSignedPercent(-45.6, "en")).toBe("\u221246\u00a0%");
    expect(formatSignedPercent(0.3, "es")).toBe("0\u00a0%");
    expect(formatSignedPercent(null, "es")).toBe("—");
  });
});
