import { neon } from '@neondatabase/serverless';
import { NextRequest, NextResponse } from 'next/server';

export async function GET() {
  const dbUrl = process.env.DATABASE_URL;
  if (!dbUrl) {
    return NextResponse.json({ error: 'DATABASE_URL not set' }, { status: 500 });
  }

  try {
    const sql = neon(dbUrl);
    const signals = await sql`
      SELECT id, category, source, metric_name, metric_value, unit,
             confidence_score, raw_source_url, timestamp
      FROM ecosystem_signals
      ORDER BY timestamp DESC
      LIMIT 50
    `;
    return NextResponse.json(signals);
  } catch (e) {
    console.error('[SID] Signal fetch error:', e);
    return NextResponse.json({ error: String(e) }, { status: 500 });
  }
}

// Ingestion endpoint — POST new signals
export async function POST(req: NextRequest) {
  const dbUrl = process.env.DATABASE_URL;
  if (!dbUrl) {
    return NextResponse.json({ error: 'DATABASE_URL not set' }, { status: 500 });
  }

  try {
    const body = await req.json();
    const { category, source, metric_name, metric_value, unit, confidence_score, raw_source_url } = body;

    if (!category || !source || !metric_name || metric_value == null) {
      return NextResponse.json({ error: 'Missing required fields: category, source, metric_name, metric_value' }, { status: 400 });
    }

    const sql = neon(dbUrl);
    const result = await sql`
      INSERT INTO ecosystem_signals (category, source, metric_name, metric_value, unit, confidence_score, raw_source_url)
      VALUES (${category}, ${source}, ${metric_name}, ${metric_value}, ${unit || null}, ${confidence_score ?? 1.0}, ${raw_source_url || null})
      RETURNING id, timestamp
    `;

    return NextResponse.json(result[0], { status: 201 });
  } catch (e) {
    console.error('[SID] Signal ingest error:', e);
    return NextResponse.json({ error: String(e) }, { status: 500 });
  }
}
