import Link from 'next/link';
import { ResearchPanel } from '@/components/ResearchPanel/ResearchPanel';
import s from './page.module.css';

export const metadata = {
  title: 'OmegA Research — Governed Research Copilot',
  description: 'Evidence-grounded, governed research with full pipeline trace.',
};

export default function ResearchPage() {
  return (
    <div className={s.root}>
      <header className={s.header}>
        <div>
          <div className={s.title}>ΩA RESEARCH</div>
          <div className={s.subtitle}>Governed Research Copilot · AEGIS-gated · Evidence-grounded</div>
        </div>
        <Link href="/" className={s.backLink}>← Back</Link>
      </header>
      <div className={s.body}>
        <ResearchPanel />
      </div>
    </div>
  );
}
