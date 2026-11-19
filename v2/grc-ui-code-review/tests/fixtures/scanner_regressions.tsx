// Regressions from the 2026-11-19 backtest. Expected: only lines 14 and 16 (CustomFields can't be told apart from a non-icon by name).
import { Dialog, Typography } from '@workiva/unify';
import { UnifyIcons } from '@workiva/unify/UnifyIcons';
import { CustomFields } from './icons';

/**
 * Rendered inside a <Dialog> owned by the page, so it has no onClose of its own.
 */
export const Regressions = ({ open, onClose }: { open: boolean; onClose: () => void }) => (
  <>
    {/* <Dialog open> — commented-out JSX is not a dialog */}
    <Dialog open={open} onClose={onClose}>
      <UnifyIcons.Description sx={{ fontSize: 20 }} />
      <CustomFields sx={{ fontSize: 48 }} />
      <CustomFieldsIcon sx={{ fontSize: '16px' }} />
      <Typography sx={{ fontSize: 14 }}>Still a typography value</Typography>
    </Dialog>
  </>
);

const CustomFieldsIcon = UnifyIcons.Settings;
