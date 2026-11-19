// Hard-coded spacing. Expected: lines 8, 9, 10, 11, 12, 13 only.
import { Box } from '@workiva/unify';
import { getToken } from '@workiva/grc-component-library';

export const Spacing = () => (
  <>
    <Box
      sx={{ p: '12px' }}
      style={{ margin: 16 }}
      sx={{ paddingTop: '0.5rem' }}
      sx={{ gap: '8px 16px' }}
      style={{ marginLeft: -4 }}
      sx={{ mx: '12' }}
    />
    <Box sx={{ p: 2, mt: 1.5, gap: 0.5 }} />
    <Box sx={{ padding: getToken('radius/nested'), margin: '0 auto', m: '0px', p: 0 }} />
    <Box style={{ margin: 0, padding: 'var(--dt-grc-spacing-page-x)', gap: `calc(100% - 4px)` }} />
    <Box sx={{ width: '320px', top: '12px', p: { xs: 1, md: 2 } }} />
    <Box style={{ padding: space * 2, marginTop: offset }} />
  </>
);
