// Fixture: idiomatic code that must produce ZERO scanner findings.
// Mentions like style={{ color }} inside comments must be ignored.
import { Box, Button, Stack, Typography } from '@workiva/unify';
import { GrcPageSection, GrcPageSectionContent, GrcPageTitle, getToken } from '@workiva/ts-grc-component-library';

export const Clean = ({ onSave }: { onSave: () => void }) => (
  <>
    <GrcPageTitle level="h2">Plans</GrcPageTitle>
    <GrcPageSection title="Details">
      <GrcPageSectionContent>
        <Stack sx={{ display: 'flex', gap: 2, p: 2, flexDirection: 'column' }}>
          <Typography sx={{ color: getToken('text/secondary') }}>Secondary text</Typography>
          <Box sx={{ borderBottom: `1px solid ${getToken('border/divider')}`, pb: 1 }} />
          <Box data-style="not-inline" sx={{ overflow: 'auto', maxWidth: 400 }} />
        </Stack>
      </GrcPageSectionContent>
    </GrcPageSection>
    <Button variant="text">Cancel</Button>
    <Button variant="contained" onClick={onSave}>Save</Button>
  </>
);

// Added 2026-09-24: patterns the backtest showed were false positives. Must stay silent.
export const AlsoClean = () => (
  <>
    <input type="file" style={{ display: 'none' }} />
    <Box sx={{ maxHeight: 320, overflowY: 'auto' }} />
    {/* <Button variant="contained">commented out</Button> */}
    <GrcDataGrid variant="contained" />
    <Chip variant="contained" />
    <Button color="error" variant="outlined">Delete</Button>
  </>
);

export const CleanDialog = ({ onClose }: { onClose: () => void }) => (
  <Dialog open onClose={(_e, reason) => { if (reason !== 'backdropClick') onClose(); }}>ok</Dialog>
);
