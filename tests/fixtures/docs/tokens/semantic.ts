// Offline stand-in for ts-grc packages/component-library/src/theme/tokens/semantic.ts
export const semanticTokens = {
  color: {
    'action/primary/default': { ref: ['color', 'teal-600'] },
    /** @deprecated Pending UX replacement — not in current Figma palette */
    'action/primary/hover': { ref: ['color', 'teal-800'] },
    'surface/default': { ref: ['color', 'white'] },
    'surface/page/section-1': { ref: ['color', 'gray-100'] },
    'text/secondary': { ref: ['color', 'gray-700'] },
    'border/divider': { ref: ['color', 'gray-300'] },
  },
  shape: {
    'radius/nested': { value: '12px' },
  },
};
