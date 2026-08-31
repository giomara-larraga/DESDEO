<script lang="ts">
	/**
	 * history-browser.svelte
	 *
	 * @author Stina Palomäki <palomakistina@gmail.com>
	 * @created December 2025
	 * @updated December 2025
	 *
	 * @description
	 * History navigation component for GDM SCORE Bands iterations.
	 * Provides expandable list of previous iterations with navigation controls.
	 * Only visible to group owners who can revert to previous states.
	 *
	 * @props
	 * @property {Array} history - Array of iteration responses (both consensus and decision phases)
	 * @property {number} currentIterationId - ID of the currently active iteration
	 * @property {Function} onRevertToIteration - Callback to revert to a specific iteration
	 * @property {boolean} [isOwner=false] - Whether current user is group owner
	 *
	 * @features
	 * - Toggle-based history visibility (show/hide)
	 * - Iteration list with identification of current and final phases
	 * - Buttons to revert to selected iterations (disabled for current/decision phases)
	 * - Owner-only access control
	 *
	 * @todo_features
	 * - Add mini-graph visualization for expanded iterations, or something else to give some info about iterations
	 * - Implement iteration expansion state management (expandedIterations already prepared)
	 *
	 * @dependencies
	 * - $lib/components/ui/button for navigation controls
	 * - $lib/api/client-types for OpenAPI-generated TypeScript types
	 * - Svelte 5 runes for reactive state management
	 */
	import { Button } from '$lib/components/ui/button';
	import type { GDMSCOREBandsResponse, GDMSCOREBandsDecisionResponse } from '$lib/gen/endpoints/DESDEOFastAPI';

	type RestartPhase =
	| 'learning'
	| 'consensus'
	| 'decision';

	// Component props
	const {
		history,
		currentIterationId,
		onRevertToIteration,
		isOwner = false,
		onRestartToPhase,
		canRestartToPhase,
		isRestartingPhase = false
	} = $props<{
		history: (
			| GDMSCOREBandsResponse
			| GDMSCOREBandsDecisionResponse
		)[];
		currentIterationId: number | null;
		onRevertToIteration: (iteration: number) => void;
		isOwner?: boolean;
		onRestartToPhase:
			(
				phase: RestartPhase
			) => void | Promise<void>;

		canRestartToPhase:
			(phase: RestartPhase) => boolean;

		isRestartingPhase?: boolean;

	}>();

	// Local state for this component
	let showHistory = $state(false);
	let expandedIterations = $state(new Set<number>());

	let isRestarting = $state(false);
	let isRevertingTo = $state<number | null>(null);
	let errorMessage = $state<string | null>(null);

	// Helper function to toggle iteration expansion (for future use)
	function toggleIterationExpansion(iterationId: number) {
		if (expandedIterations.has(iterationId)) {
			expandedIterations.delete(iterationId);
		} else {
			expandedIterations.add(iterationId);
		}
		expandedIterations = new Set(expandedIterations); // Trigger reactivity
	}
</script>

{#if isOwner}
	<div class="card bg-base-100 shadow-xl">
		<div class="card-body">
			<h2 class="card-title">History</h2>
			<div class="space-y-2">
				<p
					class="
						text-sm font-medium
					"
				>
					Reset process
				</p>

				<Button
	class="w-full"
	variant="outline"
	onclick={() =>
		onRestartToPhase('learning')}
	disabled={isRestartingPhase}
>
	Reset to Learning Phase
</Button>

<Button
	class="w-full"
	variant="outline"
	onclick={() =>
		onRestartToPhase('consensus')}
	disabled={isRestartingPhase}
>
	Reset to Consensus Phase
</Button>

<Button
	class="w-full"
	variant="outline"
	onclick={() =>
		onRestartToPhase('decision')}
	disabled={isRestartingPhase}
>
	Reset to Decision Phase
</Button>
			</div>
			<div class="space-y-2 p-2">
				<Button onclick={() => (showHistory = !showHistory)} class="btn btn-secondary">
					{showHistory ? 'Hide History' : 'Show History'}
				</Button>

				{#if showHistory}
					<div class="mt-4 max-h-100 space-y-2 overflow-y-auto">
						{#each history as historyItem, index}
							<div class="flex items-center justify-between rounded border p-2">
								<span class="text-sm">
									Iteration {historyItem.group_iter_id}
									{#if historyItem.group_iter_id === currentIterationId}
										<span class="text-xs text-blue-600">(current)</span>
									{/if}
									{#if historyItem.method === 'gdm-score-bands-final'}
										<span class="text-xs text-orange-600">(final)</span>
									{/if}
								</span>
								<Button
									onclick={() => onRevertToIteration(historyItem.group_iter_id)}
									class="btn btn-xs btn-primary"
									disabled={
										currentIterationId === null ||
										historyItem.group_iter_id === currentIterationId ||
										historyItem.method === 'gdm-score-bands-final'
									}
								>
									Go to this iteration
								</Button>
							</div>
						{/each}
						{#if history.length <= 1}
							<p class="text-center text-sm text-gray-500">No previous iterations available</p>
						{/if}
					</div>
				{/if}
			</div>
		</div>
	</div>
{/if}
