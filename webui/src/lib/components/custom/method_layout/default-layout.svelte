<script lang="ts">
	import BaseLayout from '$lib/components/custom/method_layout/reworked-layout.svelte';
	import { SegmentedControl } from '$lib/components/custom/segmented-control';
	import { Combobox } from '$lib/components/ui/combobox';
	import Button from '$lib/components/ui/button/button.svelte';
	import type { MethodHandlers } from '$lib/helpers/method-handler';
	import type { components } from '$lib/api/client-types';
	import { TYPE_SOLUTIONS_SHOWN } from '$lib/constants/index.js';
	type Solution = components['schemas']['UserSavedSolutionAddress'];

	/*export let handlers: MethodHandlers;
	export let mode: 'iterate' | 'final' | 'intermediate' = 'iterate';
	export let problem: any;
	export let selectedSolutions: Solution[] = [];
	export let selectedIndexes: number[] = [];
	export let solutionType: string = 'current';
	export let allowIntermediate: boolean = true;*/

	// Add missing props for layout control
	export let showLeftSidebar: boolean = true;
	export let showRightSidebar: boolean = false;

	// Pass through slots for custom visualization components
	/*export let visualizationComponent: any;
	export let sidebarComponent: any;
	export let tableComponent: any;*/

	/*function handleTypeChange(event: { value: string }) {
		// Type guard to ensure value is a valid SolutionViewType
		if (event.value === 'current' || event.value === 'best' || event.value === 'all') {
			handlers.handleSolutionTypeChange(event.value);
		}
	}*/
</script>

<BaseLayout {showLeftSidebar} {showRightSidebar}>
	{#snippet leftSidebar()}
		tEST
	{/snippet}

	{#snippet menuRow()}
	

		<span>View: </span>

	{/snippet}

	{#snippet topPanel()}
tOP
	{/snippet}

	{#snippet bottomPanel()}
BOTTOM
	{/snippet}
</BaseLayout>
