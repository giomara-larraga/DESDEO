<script lang="ts">
	import * as Table from '$lib/components/ui/table/index.js';
	import { formatNumber } from '$lib/helpers';
	import type { ProblemInfo } from '$lib/gen/endpoints/DESDEOFastAPI';

	let {
		problem,
		currentDesiredValues,
		previousDesiredValues = [],
		displayAccuracy,
		columnsLength
	}: {
		problem: ProblemInfo;
		currentDesiredValues: number[];
		previousDesiredValues?: number[];
		displayAccuracy: number[];
		columnsLength: number;
	} = $props();

	const metadataColumnCount = $derived(Math.max(1, columnsLength - problem.objectives.length));
</script>

{#if currentDesiredValues.length > 0 || previousDesiredValues.length > 0}
	<!-- Visual separation between achieved values and desired values -->
	<Table.Row class="pointer-events-none">
		<Table.Cell colspan={columnsLength} class="h-2 p-0"></Table.Cell>
	</Table.Row>

	{#if currentDesiredValues.length > 0}
		<Table.Row class="pointer-events-none">
			<Table.Cell colspan={metadataColumnCount}>
				<div class="flex items-center gap-2 text-sm text-gray-600">
					<svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">
						<circle cx="7" cy="7" r="4.5" fill="#FFFFFF" stroke="#374151" stroke-width="2" />
					</svg>
					<span class="italic">Current desired values</span>
				</div>
			</Table.Cell>

			{#each problem.objectives as _objective, idx}
				<Table.Cell class="pr-6 text-right text-gray-500">
					{currentDesiredValues[idx] == null
						? '—'
						: formatNumber(currentDesiredValues[idx], displayAccuracy[idx])}
				</Table.Cell>
			{/each}
		</Table.Row>
	{/if}

	{#if previousDesiredValues.length > 0}
		<Table.Row class="pointer-events-none">
			<Table.Cell colspan={metadataColumnCount}>
				<div class="flex items-center gap-2 text-sm text-gray-500">
					<svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">
						<circle cx="7" cy="7" r="4" fill="#111827" opacity="0.6" />
					</svg>
					<span class="italic">Previous desired values</span>
				</div>
			</Table.Cell>

			{#each problem.objectives as _objective, idx}
				<Table.Cell class="pr-6 text-right text-gray-400">
					{previousDesiredValues[idx] == null
						? '—'
						: formatNumber(previousDesiredValues[idx], displayAccuracy[idx])}
				</Table.Cell>
			{/each}
		</Table.Row>
	{/if}
{/if}
