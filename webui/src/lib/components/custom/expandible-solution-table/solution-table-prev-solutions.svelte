<script lang="ts">
	import * as Table from '$lib/components/ui/table/index.js';
	import { formatNumber } from '$lib/helpers';
	import type { ProblemInfo } from '$lib/gen/endpoints/DESDEOFastAPI';
	import * as Tooltip from '$lib/components/ui/tooltip/index.js';
	import TooltipContent from '$lib/components/ui/tooltip/tooltip-content.svelte';

	let {
		problem,
		previousObjectiveValues,
		currentObjectiveValues = null,
		displayAccuracy,
		columnsLength
	}: {
		problem: ProblemInfo;
		previousObjectiveValues: { [key: string]: number }[];
		currentObjectiveValues?: { [key: string]: number } | null;
		displayAccuracy: number[];
		columnsLength: number;
	} = $props();

	const metadataColumnCount = $derived(Math.max(1, columnsLength - problem.objectives.length));

	function compareValues(
		currentValue: number | undefined,
		previousValue: number | undefined,
		maximize: boolean
	): {
		status: 'improved' | 'worsened' | 'same' | 'missing';
		magnitude: number;
		delta: number;
	} {
		if (!Number.isFinite(currentValue) || !Number.isFinite(previousValue)) {
			return { status: 'missing', magnitude: 0, delta: 0 };
		}

		const delta = Number(currentValue) - Number(previousValue);
		const tolerance = 1e-9;

		if (Math.abs(delta) <= tolerance) {
			return { status: 'same', magnitude: 0, delta };
		}

		const improved = maximize ? delta > 0 : delta < 0;

		return {
			status: improved ? 'improved' : 'worsened',
			magnitude: Math.abs(delta),
			delta
		};
	}
</script>

{#if previousObjectiveValues && previousObjectiveValues.length > 0}
	{@const previousObjectiveValue = previousObjectiveValues[0]}

	<!-- Previous presented solution -->
	<Table.Row class="pointer-events-none bg-gray-50/60">
		<Table.Cell colspan={metadataColumnCount}>
			<div class="flex items-center gap-2 text-sm text-gray-600">
				<svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">
					<polygon points="3,4 11,4 7,11" fill="#FFFFFF" stroke="#6B7280" stroke-width="1.5" />
				</svg>
				<span class="italic">Previous solution</span>
			</div>
		</Table.Cell>

		{#each problem.objectives as objective, idx}
			<Table.Cell class="pr-6 text-right text-gray-500">
				{formatNumber(previousObjectiveValue[objective.symbol], displayAccuracy[idx])}
			</Table.Cell>
		{/each}
	</Table.Row>

	<!-- Direction-aware change from previous presented solution -->
	{#if currentObjectiveValues}
		<Table.Row class="pointer-events-none bg-gray-50/30">
			<Table.Cell colspan={metadataColumnCount} class="border-l-4 border-transparent">
				<span class="text-sm font-medium text-gray-600">Change from previous</span>
			</Table.Cell>

			{#each problem.objectives as objective, idx}
				{@const comparison = compareValues(
					currentObjectiveValues[objective.symbol],
					previousObjectiveValue[objective.symbol],
					Boolean(objective.maximize)
				)}

				<Table.Cell class="pr-6 text-right text-gray-500">
					{#if comparison.status === 'missing'}
						—
					{:else if comparison.status === 'same'}
						<span title="No achieved-value change">No change</span>
					{:else}
						<Tooltip.Provider>
							<Tooltip.Root>
								<Tooltip.Trigger
									class="pointer-events-auto underline decoration-dotted underline-offset-2"
								>
									<span class="font-medium">
										{#if comparison.status === 'improved'}
											<span class="font-semibold text-gray-700">
												{formatNumber(comparison.magnitude, displayAccuracy[idx])} ↑</span
											>
										{:else}
											<span class="font-semibold text-gray-700">
												{formatNumber(comparison.magnitude, displayAccuracy[idx])}↓</span
											>
										{/if}
									</span>
								</Tooltip.Trigger>
								<Tooltip.Content sideOffset={6}>
									<p>
										This value has {comparison.status === 'improved' ? 'improved' : 'worsened'} by {formatNumber(
											comparison.magnitude,
											displayAccuracy[idx]
										)} units compared to the previous solution.
									</p>
								</Tooltip.Content>
							</Tooltip.Root>
						</Tooltip.Provider>
					{/if}
				</Table.Cell>
			{/each}
		</Table.Row>
	{/if}
{/if}
