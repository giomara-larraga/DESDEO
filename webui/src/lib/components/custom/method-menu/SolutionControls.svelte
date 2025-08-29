<script lang="ts">
  import { SegmentedControl } from '$lib/components/custom/segmented-control';
  import { Combobox } from '$lib/components/ui/combobox';
  import Button from '$lib/components/ui/button/button.svelte';

  export let mode: 'iterate' | 'intermediate' | 'final';

  export let selectedType: 'current' | 'best' | 'all';
  export let onTypeChange: (t: 'current' | 'best' | 'all') => void;

  export let canFinish: boolean;
  export let onFinish: () => void;

  const frameworks = [
    { value: 'current', label: 'Current solutions' },
    { value: 'best', label: 'Best candidate solutions' },
    { value: 'all', label: 'All solutions' }
  ];
</script>

<SegmentedControl
  bind:value={mode}
  options={[
    { value: 'iterate', label: 'Iterate' },
    { value: 'intermediate', label: 'Find intermediate' }
  ]}
  class="mr-10"
/>

<span>View: </span>
<Combobox
  options={frameworks}
  defaultSelected={selectedType}
  onChange={(e) => onTypeChange(e.value as "current" | "best" | "all")}
/>

<span class="inline-block" title={canFinish
  ? 'Select final solution and finish the NIMBUS method with it'
  : 'Please select exactly one solution to finish with it.'}>
  <Button
    onclick={canFinish ? onFinish : undefined}
    disabled={!canFinish}
    variant="destructive"
    class="ml-10"
  >Finish</Button>
</span>
