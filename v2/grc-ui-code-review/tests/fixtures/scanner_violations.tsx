// Fixture: one planted instance per static-scanner check. Line numbers are asserted in expected.json.
import { Button } from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import { Box, Paper, Stack, styled } from '@workiva/unify';
import { GrcPageSection, GrcPageTitle, getToken } from '@workiva/ts-grc-component-library';

const WrappedSection = styled(GrcPageSection)({});

export const Violations = () => (
  <>
    <div style={{ color: 'red' }}>inline style</div>
    <GrcPageTitle level="h3" weight="bold">Title</GrcPageTitle>
    <GrcPageSection insetHeader title="Deprecated" />
    <Box sx={{ bgcolor: getToken('surface/default'), borderRadius: 12, border: '1px solid', boxShadow: 1 }} />
    <Stack sx={{ outline: '1px solid', filter: 'none', boxShadow: 2 }} />
    <Paper sx={{ maxHeight: 300 }} />
    <Box sx={{ bgcolor: getToken('surface/page/section-1'), p: 2 }}>
      <Box sx={{ border: '1px solid', borderRadius: 8, p: 2 }}>nested</Box>
    </Box>
    <Button variant="contained">One</Button>
    <Button variant="contained">Two</Button>
    <Button variant="contained">Three</Button>
    <WrappedSection />
    <AddIcon />
  </>
);

// Added 2026-09-24 after the backtest: color checks + inline-style tiers.
export const ColorViolations = ({ x }: { x: number }) => (
  <>
    <Box sx={{ color: '#9E64D5' }} />
    <Box sx={{ borderColor: 'rgba(0, 0, 0, 0.12)' }} />
    <Box sx={{ color: 'text.secondary', bgcolor: 'background.paper' }} />
    <div style={{ left: x, width: 20 }} />
  </>
);

// Added 2026-09-24: dialog dismissal + getToken source.
import { getToken as unifyGetToken } from '@workiva/unify';
export const DialogViolations = () => (
  <>
    <Dialog open>no onClose</Dialog>
    <Dialog open onClose={() => {}} disableEscapeKeyDown>esc disabled</Dialog>
  </>
);
export const Crumbs = () => <GrcBreadcrumbs defaultExpanded={true} />;
// Token catalog: unknown (line 48), deprecated (line 49), legacy Core/* skipped (line 50).
const unknownToken = getToken('radius/card');
const deprecatedToken = getToken('action/primary/hover');
const legacyToken = getToken('Core/Icon/icon-error');
