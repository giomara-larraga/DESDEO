<script lang="ts">
	import { onMount } from 'svelte';
	import { methodSelection } from '../../../stores/methodSelection';
	import BaseMethodLayout from '$lib/components/custom/method-layout/base-method-layout.svelte';
	import { nimbusStore } from './stores/nimbus-store';
	import { createNimbusHandlers } from './handlers/nimbus-handlers';
	import NimbusSidebar from './components/sidebar/nimbus-sidebar.svelte';
	import IntermediateSidebar from './components/sidebar/intermediate-sidebar.svelte';
	import NimbusVisualizations from './components/visualizations/nimbus-visualizations.svelte';
	import SolutionTable from './components/table/solution-table.svelte';
	import ConfirmationDialog from '$lib/components/custom/confirmation-dialog.svelte';
	import InputDialog from '$lib/components/custom/input-dialog.svelte';
	import type { DialogConfig } from '$lib/types/dialog';

	const handlers = createNimbusHandlers();

	let dialogConfig: DialogConfig = {
		open: false,
		title: '',
		description: '',
		confirmText: '',
		cancelText: '',
		onConfirm: () => {},
		onCancel: () => {},
		confirmVariant: 'default'
	};

	let inputDialogConfig = {
		open: false,
		solution: null,
		initialName: ''
	};

	onMount(async () => {
		if ($methodSelection.selectedProblemId) {
			await handlers.handleInitialize($methodSelection.selectedProblemId);
		}
	});
</script>

<BaseMethodLayout state={$nimbusStore} {handlers} allowIntermediate={true}>
	<svelte:fragment slot="leftSidebar">
		{#if $nimbusStore.mode === 'iterate'}
			<NimbusSidebar
				problem={$nimbusStore.problem}
				currentPreference={$nimbusStore.currentPreference}
				onPreferenceChange={handlers.handlePreferenceChange}
			/>
		{:else}
			<IntermediateSidebar
				solutions={$nimbusStore.currentState.current_solutions}
				selectedIndexes={$nimbusStore.selectedIndexes}
				onSolutionSelect={(idx) => (nimbusStore.selectedIndexes = [idx])}
			/>
		{/if}
	</svelte:fragment>

	<svelte:fragment slot="visualizationArea">
		<NimbusVisualizations
			problem={$nimbusStore.problem}
			solutions={$nimbusStore.currentState.current_solutions}
			selectedIndexes={$nimbusStore.selectedIndexes}
		/>
	</svelte:fragment>

	<svelte:fragment slot="numericalValues">
		<SolutionTable
			problem={$nimbusStore.problem}
			solutions={$nimbusStore.currentState.current_solutions}
			selectedIndexes={$nimbusStore.selectedIndexes}
			onSave={handlers.handleSave}
			onRemove={handlers.handleRemove}
		/>
	</svelte:fragment>
</BaseMethodLayout>

<ConfirmationDialog {...dialogConfig} />
<InputDialog {...inputDialogConfig} />
