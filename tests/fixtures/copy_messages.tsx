// Fixture for extract_copy.py: every supported defaultMessage form.
import { defineMessage, FormattedMessage, useIntl } from 'react-intl';

const A = defineMessage({ defaultMessage: 'Import {count} steps?', description: 'Confirm title' });
export const B = () => {
  const intl = useIntl();
  const x = intl.formatMessage({
    defaultMessage: "Couldn't update the control",
    description: 'Error toast',
  });
  return <FormattedMessage defaultMessage="Loading control data — please wait" description="Blocking message" />;
};
const C = { defaultMessage: `Multi
  line message`, description: 'Template literal' };
const D = { defaultMessage: 'It\'s escaped', description: 'Escaped quote' };
