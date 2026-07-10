export enum AccessLevel {
  Full = 'full',
  KbOnly = 'kb_only',
}

export const KB_ONLY_ALLOWED_NAV = ['/datasets'] as const;

export const KB_ONLY_ALLOWED_SETTING_PATHS = [
  '/user-setting/profile',
] as const;
