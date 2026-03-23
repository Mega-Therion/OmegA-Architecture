import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(req: NextRequest) {
  // Check if auth is required
  const authRequired = process.env.OMEGA_UI_PASSWORD;
  if (!authRequired) return NextResponse.next();

  // Basic Auth
  const basicAuth = req.headers.get('authorization');
  if (basicAuth) {
    const authValue = basicAuth.split(' ')[1];
    const [user, pwd] = atob(authValue).split(':');

    if (user === 'omega' && pwd === authRequired) {
      return NextResponse.next();
    }
  }

  // If not authenticated, request it
  return new NextResponse('Authentication Required', {
    status: 401,
    headers: {
      'WWW-Authenticate': 'Basic realm="OmegA Sovereign"',
    },
  });
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
