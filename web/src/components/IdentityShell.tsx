"use client";

import { useEffect, useState } from "react";
import styles from "./IdentityShell.module.css";

const BANNER = [
    "    ██████╗     ██╗    ██╗    ███████╗    ██╗   ██╗",
    "    ██╔══██╗    ██║    ██║    ██╔════╝    ╚██╗ ██╔╝",
    "    ██████╔╝    ██║ █╗ ██║    █████╗       ╚████╔╝ ",
    "    ██╔══██╗    ██║███╗██║    ██╔══╝        ╚██╔╝  ",
    "    ██║  ██║    ╚███╔███╔╝    ██║            ██║   ",
    "    ╚═╝  ╚═╝     ╚══╝╚══╝     ╚═╝            ╚═╝   "
];

export default function IdentityShell() {
  const [offset, setOffset] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setOffset((prev) => (prev + 0.01) % 1.0);
    }, 50);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className={styles.container}>
      <pre className={styles.banner}>
        {BANNER.map((line, i) => (
          <div key={i} className={styles.line}>
            {line.split("").map((char, x) => (
              <span
                key={x}
                style={{
                  color: char === "█" ? "#282d32" : `hsl(${(x * 2 + i * 5 + offset * 360) % 360}, 100%, 70%)`,
                  opacity: char === " " ? 0 : 1,
                  textShadow: char !== "█" && char !== " " ? `0 0 10px hsla(${(x * 2 + i * 5 + offset * 360) % 360}, 100%, 70%, 0.5)` : "none"
                }}
              >
                {char}
              </span>
            ))}
          </div>
        ))}
      </pre>
      <div className={styles.meta}>
        <span className={styles.title}>THE OMEGA SOVEREIGN PORTAL</span>
        <span className={styles.subtitle}>(YETTRAGRAMMATON)</span>
      </div>
    </div>
  );
}
