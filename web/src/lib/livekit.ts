export interface LiveKitConfig {
  enabled: boolean;
  url: string;
  tokenEndpoint: string;
  showStatusBadge: boolean;
}

export const livekitConfig: LiveKitConfig = {
  enabled: process.env.NEXT_PUBLIC_LIVEKIT_ENABLED === 'true',
  url: process.env.NEXT_PUBLIC_LIVEKIT_URL ?? '',
  tokenEndpoint: process.env.NEXT_PUBLIC_LIVEKIT_TOKEN_ENDPOINT ?? '/api/livekit/token',
  showStatusBadge: process.env.NEXT_PUBLIC_LIVEKIT_STATUS_BADGE === 'true',
};

export function isLiveKitConfigured(config: LiveKitConfig = livekitConfig): boolean {
  return Boolean(config.enabled && config.url && config.tokenEndpoint);
}
