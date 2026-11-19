// Planning responses panel.
import { useState } from 'react';
import {
  Box, Button, CircularProgress, Dialog, DialogActions, DialogContent, DialogTitle,
  Divider, Drawer, IconButton, Link, Stack, Typography,
} from '@workiva/unify';
import { UnifyIcons } from '@workiva/unify/UnifyIcons';
import { getToken } from '@workiva/ts-grc-component-library';

export const PlantedIssues = ({ rows, loading, name, onSave }: {
  rows: string[]; loading: boolean; name: string; onSave: (v: string) => void;
}) => {
  const [value, setValue] = useState('');
  const [open, setOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  return (
    <Stack>
      <Button variant="text" onClick={() => setOpen(true)}>Log Response</Button>
      <Dialog open={open}>
        <DialogTitle>Log Management Response</DialogTitle>
        <DialogContent>
          <input value={value} onChange={(e) => setValue(e.target.value)} />
        </DialogContent>
        <DialogActions>
          <Button variant="text" onClick={() => setOpen(false)}>Cancel</Button>
          <Button variant="contained" disabled={value.length === 0} onClick={() => onSave(value)}>Add</Button>
        </DialogActions>
      </Dialog>

      <Dialog open={confirmDelete}>
        <DialogTitle>Delete {name}?</DialogTitle>
        <DialogActions>
          <Button variant="text" onClick={() => setConfirmDelete(false)}>Cancel</Button>
          <Button variant="contained" onClick={() => setConfirmDelete(false)}>Delete</Button>
        </DialogActions>
      </Dialog>

      <IconButton onClick={() => setConfirmDelete(true)}>
        <UnifyIcons.Delete />
      </IconButton>

      <Drawer open>
        <Stack direction="row" justifyContent="flex-end">
          <IconButton aria-label="Close"><UnifyIcons.Close /></IconButton>
        </Stack>
        <Divider />
        <Typography variant="h5">Details</Typography>
        <Box sx={{ bgcolor: getToken('surface/page/section-1'), p: 2 }}>Drawer body</Box>
      </Drawer>

      {loading && <CircularProgress />}

      {rows.length === 0 && (
        <Stack alignItems="center">
          <Typography>No responses yet</Typography>
          <Link href="/help">Learn more</Link>
          <Button variant="contained">Create response</Button>
        </Stack>
      )}
      <Button variant="outlined">Export</Button>

      <Stack direction="row" alignItems="center">
        <Typography sx={{ color: '#9E64D5' }}>Suggested summary</Typography>
        <UnifyIcons.AutoAwesome />
      </Stack>
      <Typography sx={{ color: 'error.main' }}>Something failed</Typography>
    </Stack>
  );
};
