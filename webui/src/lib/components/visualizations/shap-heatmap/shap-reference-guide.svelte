<script lang="ts">
	import InfoIcon from '@lucide/svelte/icons/info';
	import * as Tooltip from '$lib/components/ui/tooltip/index.js';
	import type { ProblemInfo } from '$lib/types';

	interface Props {
		shapRow: Record<string, number>;
		selectedOutputSymbol: string;
		problem: ProblemInfo;
	}

	let { shapRow, selectedOutputSymbol, problem }: Props = $props();

	const objNameMap = $derived(
		Object.fromEntries(problem.objectives.map((o) => [o.symbol, o.name ?? o.symbol]))
	);

	const objMaximizeMap = $derived(
		Object.fromEntries(problem.objectives.map((o) => [o.symbol, o.maximize ?? false]))
	);

	const focusOutcomeName = $derived(objNameMap[selectedOutputSymbol] ?? selectedOutputSymbol);

	const recommendations = $derived.by(() => {
		const maximize = objMaximizeMap[selectedOutputSymbol] ?? false;
		const entries = Object.entries(shapRow).map(([inputSym, value]) => {
			const aspirationSymbol = inputSym.startsWith('z_') ? inputSym.slice(2) : inputSym;
			const helpful = maximize ? value > 0 : value < 0;
			return {
				inputSym,
				aspirationSymbol,
				name: objNameMap[aspirationSymbol] ?? aspirationSymbol,
				value,
				helpful,
				isOwnAspiration: aspirationSymbol === selectedOutputSymbol,
				actionLabel: helpful ? 'Make aspiration more ambitious' : 'Make aspiration less demanding',
				strength: Math.abs(value)
			};
		});

		entries.sort((left, right) => {
			if (left.helpful !== right.helpful) return left.helpful ? -1 : 1;
			return right.strength - left.strength;
		});

		const maxStrength = Math.max(1e-9, ...entries.map((entry) => entry.strength));
		return entries.map((entry) => ({
			...entry,
			strengthRatio: entry.strength / maxStrength,
			widthPct: (entry.strength / maxStrength) * 100,
			impactLabel:
				entry.strength / maxStrength >= 0.67
					? 'High impact'
					: entry.strength / maxStrength >= 0.34
						? 'Medium impact'
						: 'Low impact'
		}));
	});

	const firstHelpful = $derived(recommendations.find((entry) => entry.helpful) ?? null);
	const ownAspirationWarning = $derived(
		recommendations.find((entry) => entry.isOwnAspiration && !entry.helpful) ?? null
	);

	function formatValue(value: number): string {
		return value.toFixed(2);
	}
</script>

<div class="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-3 text-xs text-emerald-950">
	<p class="font-medium">Suggested next reference point</p>
	<p class="mt-1 text-emerald-900">
		For <strong>{focusOutcomeName}</strong>, start with the aspiration that is most likely to help this outcome.
	</p>
	{#if firstHelpful}
		<p class="mt-1 text-emerald-900">
			Start by <strong>{firstHelpful.actionLabel.toLowerCase()}</strong> for
			<strong>{firstHelpful.name}</strong>.
		</p>
	{/if}
	{#if ownAspirationWarning}
		<p class="mt-1 text-amber-700">
			The aspiration for <strong>{focusOutcomeName}</strong> itself may be too strict.
		</p>
	{/if}
	<div class="mt-2 flex items-start gap-1 text-[11px] text-emerald-900">
		<span>Bars and labels show relative impact, not how many units to change.</span>
		<Tooltip.Root>
			<Tooltip.Trigger class="mt-0.5 inline-flex items-center text-emerald-700 hover:text-emerald-900">
				<InfoIcon class="h-3.5 w-3.5" />
			</Tooltip.Trigger>
			<Tooltip.Content sideOffset={6} class="max-w-72">
				A high-impact aspiration matters more for this outcome than a low-impact aspiration. The value is an explanation score, not a recommended number of units to change in the reference point.
			</Tooltip.Content>
		</Tooltip.Root>
	</div>

	<div class="mt-3 space-y-2">
		{#each recommendations as item}
			<div class="rounded-md bg-white/70 px-2 py-2 ring-1 ring-black/5">
				<div class="flex items-start justify-between gap-2">
					<div>
						<p class="font-medium text-gray-900">
							{item.name}
							{#if item.isOwnAspiration}
								<span class="font-normal text-gray-500">(own aspiration)</span>
							{/if}
						</p>
						<p class="mt-0.5 text-[11px] text-gray-600">{item.actionLabel}</p>
					</div>
					<span
						class={`rounded-full px-2 py-0.5 text-[10px] font-medium ${item.helpful ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}`}
					>
						{item.helpful ? 'Helpful' : 'Use caution'}
					</span>
				</div>
				<div class="mt-2 h-2 rounded-full bg-gray-200">
					<div
						class={`h-2 rounded-full ${item.helpful ? 'bg-emerald-500' : 'bg-amber-500'}`}
						style={`width:${item.widthPct}%`}
					></div>
				</div>
				<div class="mt-1 flex items-center justify-between gap-2 text-[10px] text-gray-500">
					<span>{item.impactLabel}</span>
					<Tooltip.Root>
						<Tooltip.Trigger class="inline-flex items-center text-gray-400 hover:text-gray-600">
							<span class="underline decoration-dotted underline-offset-2">Details</span>
						</Tooltip.Trigger>
						<Tooltip.Content sideOffset={6} class="max-w-64">
							Exact explanation value: <strong>{formatValue(item.value)}</strong>.<br />
							This shows relative impact on the outcome, not the amount to change the aspiration.
						</Tooltip.Content>
					</Tooltip.Root>
				</div>
			</div>
		{/each}
	</div>
</div>