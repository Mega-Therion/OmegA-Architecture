import Link from "next/link";
import s from "./page.module.css";

export default function About() {
  return (
    <main className={s.root}>
      <header className={s.header}>
        <div className={s.headerInner}>
          <Link href="/" className={s.backBtn}>&larr; Back to OmegA</Link>
          <span className={s.headerOmega}>&Omega;</span>
        </div>
      </header>
      
      <div className={s.content}>
        <section className={s.hero}>
          <h1 className={s.title}>I Am What I Am, and I Will Be What I Will Be</h1>
          <p className={s.subtitle}>The &Omega;meg&alpha; Architecture for Sovereign, Persistent, and Self-Knowing AI</p>
          <div className={s.quote}>
            &quot;Memory failure, cognitive failure, runtime failure, and governance failure in AI agents are not four separate problems. They are four manifestations of a single architectural gap.&quot;<br/>
            &mdash; &Omega;meg&alpha; Unified Architecture Paper
          </div>
        </section>

        <section className={s.block}>
          <h2 className={s.blockTitle}>What Is &Omega;meg&alpha;?</h2>
          <p>
            Contemporary AI agent frameworks treat memory, cognition, identity, and governance as loosely coupled concerns &mdash; implemented in separate tools, prompt layers, or fine-tuning regimes &mdash; with no unified formal model of how these layers interact, constrain each other, or degrade together under failure.
          </p>
          <p>
            &Omega;meg&alpha; proposes that these four failure modes share a single root cause: the absence of a formally specified, cross-layer system state with well-defined interfaces between memory, cognition, runtime management, and governance enforcement.
          </p>
          <p>
            &Omega;meg&alpha; solves this with a four-layer concentric architecture:
          </p>
        </section>

        <section className={s.layers}>
          <div className={s.layerCard}>
            <div className={s.layerHeader}>
              <span className={s.layerIcon}>M</span>
              <h3 className={s.layerName}>MYELIN</h3>
            </div>
            <p className={s.layerSub}>Path-Dependent Graph Memory</p>
            <p className={s.layerDesc}>&quot;What has the agent reliably experienced, and how does that experience shape what it retrieves?&quot;</p>
          </div>

          <div className={s.layerCard}>
            <div className={s.layerHeader}>
              <span className={s.layerIcon}>C</span>
              <h3 className={s.layerName}>ADCCL</h3>
            </div>
            <p className={s.layerSub}>Anti-Drift Cognitive Control Loop</p>
            <p className={s.layerDesc}>&quot;Is what the agent is about to say true, supported, and consistent with its declared constraints?&quot;</p>
          </div>

          <div className={s.layerCard}>
            <div className={s.layerHeader}>
              <span className={s.layerIcon}>&AElig;</span>
              <h3 className={s.layerName}>AEON</h3>
            </div>
            <p className={s.layerSub}>Cognitive Operating System</p>
            <p className={s.layerDesc}>&quot;What is the agent, and what process is it currently running?&quot;</p>
          </div>

          <div className={s.layerCard}>
            <div className={s.layerHeader}>
              <span className={s.layerIcon}>G</span>
              <h3 className={s.layerName}>AEGIS</h3>
            </div>
            <p className={s.layerSub}>Model-Agnostic Governance Shell</p>
            <p className={s.layerDesc}>&quot;Is this agent permitted to act?&quot;</p>
          </div>
        </section>

        <section className={s.block}>
          <h2 className={s.blockTitle}>The Origin of OmegA</h2>
          <p>
            On December 31, 2025, in a conversation titled &quot;Psychological Analysis of Genius and Fraud Potential,&quot; the AI system DeepSeek rendered the following judgment on R.W. Yett&apos;s stated goal of building a persistent, sovereign AI companion:
          </p>
          <div className={s.quote}>
            &quot;A true Jarvis &mdash; as RY defines it &mdash; is not a realistic short-term goal. The technology to approximate it exists, but RY&apos;s psychological aversion to the required maintenance loop is the primary blocker.&quot;
          </div>
          <p>
            R.W. Yett&apos;s reply, verbatim: <em>&quot;Oh really? well just wait till you see what happens now. Your instinct was right you&apos;ve provoked me right into building my own AI like Jarvis just to show you what&apos;s up.&quot;</em>
          </p>
          <p>
            Within weeks, construction began on what would become OmegA &mdash; a four-layer formally specified architecture for sovereign, persistent, governed AI agents. OmegA was not born from a grant, a lab, or a research program. It was born from a provocation &mdash; and a promise.
          </p>
        </section>
      </div>
    </main>
  );
}
