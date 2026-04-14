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
				relationshipLabel: helpful
					? 'Currently improves the selected outcome'
					: 'Currently impairs the selected outcome',
				strength: Math.abs(value)
			};
		});

		entries.sort((left, right) => (maximize ? left.value - right.value : right.value - left.value));

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

	const relaxFirst = $derived(recommendations[0] ?? null);
	const hasImpairingAspiration = $derived(recommendations.some((entry) => !entry.helpful));
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
		For <strong>{focusOutcomeName}</strong>, identify the aspiration you should relax first to improve this outcome.
	</p>
	{#if relaxFirst}
		<p class="mt-1 text-emerald-900">
			{#if hasImpairingAspiration}
				Start by <strong>making the aspiration less demanding</strong> for
				<strong>{relaxFirst.name}</strong>, because it has the most impairing effect on
				<strong>{focusOutcomeName}</strong>.
			{:else}
				All aspirations currently support <strong>{focusOutcomeName}</strong>. If you still need to relax one,
				start with <strong>{relaxFirst.name}</strong> because it has the least improving effect.
			{/if}
		</p>
	{/if}
	{#if ownAspirationWarning}
		<p class="mt-1 text-amber-700">
			The aspiration for <strong>{focusOutcomeName}</strong> itself is currently impairing this outcome and may be too strict.
		</p>
		<p class="mt-1 text-[11px] text-amber-700/90">
			This can happen even when the target is still below the theoretical best value: the rest of the
			reference point may already push the outcome close to its local ceiling, so tightening this
			aspiration further can hurt the outcome instead of helping it.
		</p>
	{/if}
	<div class="mt-2 flex items-start gap-1 text-[11px] text-emerald-900">
		<span>Bars and labels show which aspiration is safest or most necessary to relax first, not how many units to change.</span>
		<Tooltip.Root>
			<Tooltip.Trigger class="mt-0.5 inline-flex items-center text-emerald-700 hover:text-emerald-900">
				<InfoIcon class="h-3.5 w-3.5" />
			</Tooltip.Trigger>
			<Tooltip.Content sideOffset={6} class="max-w-72">
				A high-impact aspiration has a stronger effect on the selected outcome. The recommendation ranks which aspiration to relax first: the most impairing one, or if none are impairing, the least improving one. The value is an explanation score, not a recommended number of units to change.
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
						<p class="mt-0.5 text-[11px] text-gray-600">{item.relationshipLabel}</p>
					</div>
					<span
						class={`rounded-full px-2 py-0.5 text-[10px] font-medium ${item.helpful ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}`}
					>
						{item === relaxFirst ? 'Relax first' : item.helpful ? 'Improving' : 'Impairing'}
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
							This shows how strongly this aspiration affects the selected outcome. The ranking indicates which aspiration to relax first, not the amount to change it.
						</Tooltip.Content>
					</Tooltip.Root>
				</div>
			</div>
		{/each}
	</div>
</div>