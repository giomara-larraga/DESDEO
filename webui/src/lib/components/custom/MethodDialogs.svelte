<script lang="ts">
  import ConfirmationDialog from '$lib/components/custom/confirmation-dialog.svelte';
  import InputDialog from '$lib/components/custom/input-dialog.svelte';
  import type { Solution } from '$lib/types/general';

  export let confirmOpen: boolean;
  export let confirmTitle = '';
  export let confirmDescription = '';
  export let confirmText = 'OK';
  export let cancelText = 'Cancel';
  export let onConfirm: () => void = () => {};
  export let onCancel: () => void = () => {};
  export let confirmVariant: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link" = "default";

  export let renameOpen: boolean;
  export let initialName = '';
  export let onRenameConfirm: (name: string) => void = () => {};
  export let onRenameCancel: () => void = () => {};
</script>

<ConfirmationDialog
  bind:open={confirmOpen}
  title={confirmTitle}
  description={confirmDescription}
  confirmText={confirmText}
  cancelText={cancelText}
  onConfirm={onConfirm}
  onCancel={onCancel}
  confirmVariant={confirmVariant}
/>

<InputDialog
  bind:open={renameOpen}
  title="Rename Solution"
  description="Enter a name for this solution."
  confirmText="Save"
  cancelText="Cancel"
  initialValue={initialName}
  placeholder="Solution name"
  onConfirm={(name) => onRenameConfirm(name)}
  onCancel={onRenameCancel}
/>
