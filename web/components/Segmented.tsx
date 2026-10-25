"use client";

import styles from "./Segmented.module.css";

interface Option<T extends string> {
  value: T;
  label: string;
}

interface Props<T extends string> {
  label: string;
  value: T;
  options: readonly Option<T>[];
  onChange: (value: T) => void;
  tone?: "ink" | "paper";
}

/** Pill segmented control (DESIGN.md), built as a native radio group for keyboard users. */
export function Segmented<T extends string>({
  label,
  value,
  options,
  onChange,
  tone = "paper",
}: Props<T>) {
  return (
    <fieldset className={`${styles.group} ${styles[tone]}`}>
      <legend className="visually-hidden">{label}</legend>
      {options.map((option) => (
        <label key={option.value} className={styles.option}>
          <input
            type="radio"
            className={styles.input}
            name={label}
            value={option.value}
            checked={option.value === value}
            onChange={() => onChange(option.value)}
          />
          <span className={styles.face}>{option.label}</span>
        </label>
      ))}
    </fieldset>
  );
}
