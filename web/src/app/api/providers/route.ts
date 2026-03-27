import { NextResponse } from 'next/server';
import { getProviderHealthSnapshot, getProviderOrder } from '@/lib/provider-routing';

export async function GET() {
  const providerHealth = getProviderHealthSnapshot();
  return NextResponse.json({
    providerHealth,
    providerOrder: getProviderOrder(),
  });
}
