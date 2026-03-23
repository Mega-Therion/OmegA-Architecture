"use client";

import styles from "./SystemState.module.css";

const VARIABLES = [
  { symbol: "Φ", label: "Phylactery HEAD", desc: "Cryptographic hash of ratified identity" },
  { symbol: "E", label: "Active Run Envelope", desc: "Governance policy & tool manifest" },
  { symbol: "τ", label: "Task State Object", desc: "Structured representation of current task" },
  { symbol: "B", label: "Claim Budget", desc: "Evidence-paired assertions" },
  { symbol: "S", label: "Self-Tag", desc: "Immutable continuity record" },
  { symbol: "G", label: "Memory Graph", desc: "Utility-weighted MYELIN paths" },
];

export default function SystemState() {
  return (
    <div className={`${styles.container} glass`}>
      <h3 className={styles.title}>System State Vector (Ω<sub>t</sub>)</h3>
      <div className={styles.equation}>
        Ω<sub>t</sub> = ⟨
        {VARIABLES.map((v, i) => (
          <span key={v.symbol} className={styles.symbolWrapper}>
            <span className={styles.symbol}>{v.symbol}<sub>t</sub></span>
            {i < VARIABLES.length - 1 && <span className={styles.comma}>, </span>}
            <div className={styles.tooltip}>
              <strong>{v.label}</strong>
              <p>{v.desc}</p>
            </div>
          </span>
        ))}
        ⟩
      </div>
    </div>
  );
}
