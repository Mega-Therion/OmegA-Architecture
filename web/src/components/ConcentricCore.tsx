"use client";

import styles from "./ConcentricCore.module.css";

const LAYERS = [
  { id: "aegis", name: "AEGIS", desc: "Governance Shell", color: "var(--sovereign-gold)" },
  { id: "aeon", name: "AEON", desc: "Cognitive OS", color: "var(--omega-cyan)" },
  { id: "adccl", name: "ADCCL", desc: "Control Loop", color: "var(--omega-blue)" },
  { id: "myelin", name: "MYELIN", desc: "Graph Memory", color: "var(--sovereign-orange)" },
];

export default function ConcentricCore() {
  return (
    <div className={styles.wrapper}>
      <div className={styles.container}>
        {LAYERS.map((layer, i) => (
          <div
            key={layer.id}
            className={styles.layer}
            style={{
              width: `${100 - i * 20}%`,
              height: `${100 - i * 20}%`,
              borderColor: layer.color,
              zIndex: 10 - i,
            }}
          >
            <div className={styles.label} style={{ color: layer.color }}>
              <span className={styles.layerName}>{layer.name}</span>
              <span className={styles.layerDesc}>{layer.desc}</span>
            </div>
          </div>
        ))}
      </div>
      <div className={styles.info}>
        <h2 className={styles.infoTitle}>Ωmegα Unified Architecture</h2>
        <p className={styles.infoText}>
          A four-layer concentric architecture solving memory, cognitive, runtime, and governance failure through a single unified system state.
        </p>
      </div>
    </div>
  );
}
