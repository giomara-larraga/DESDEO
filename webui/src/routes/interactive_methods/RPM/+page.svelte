<script lang="ts">
	import { methodSelection } from '../../../stores/methodSelection';
	import { onMount } from 'svelte';
	import Button from '$lib/components/ui/button/button.svelte';
	import type { ProblemInfo } from '$lib/types';
	import type { RPMState, RPMSolveRequest } from './types';

	// Basic state
	let problem: ProblemInfo | null = $state(null);
	let reference_point: number[] = $state([]);
	let solutions: RPMState['solver_results'][] = $state([]);

	// Get problem from route data
	const { data } = $props<{ data: { problems: ProblemInfo[] } }>();

	async function solve() {
		if (!problem || reference_point.length === 0) {
			console.error('Missing problem or reference point');
			return;
		}

		try {
			// Convert reference points to object with objective names as keys
			const aspiration_levels = problem.objectives.reduce(
				(acc, obj, index) => {
					acc[obj.symbol] = reference_point[index];
					return acc;
				},
				{} as { [key: string]: number }
			);

			const request: RPMSolveRequest = {
				problem_id: problem.id,
				preference: {
					preference_type: 'reference_point',
					aspiration_levels
				},
				scalarization_options: { rho: 0.1 },
				solver: 'scipy',
				solver_options: { maxiter: 1000 }
			};

			const response = await fetch('/interactive_methods/RPM?type=solve', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(request)
			});

			if (!response.ok) {
				throw new Error(`Failed to solve RPM: ${response.statusText}`);
			}

			const result = await response.json();
			console.log('API Response:', result);
			if (!result.success) {
				throw new Error(result.error || 'Unknown error occurred');
			}

			const rpmState: RPMState = result.data;
			const solverResults = rpmState.solver_results;
			console.log('Solver Results:', solverResults);
			solutions = Array.isArray(solverResults) ? solverResults : [solverResults];
		} catch (error) {
			console.error('Error solving RPM:', error);
		}
	}

	onMount(() => {
		if ($methodSelection.selectedProblemId) {
			const foundProblem = data.problems?.find(
				(p: { id: any }) => String(p.id) === String($methodSelection.selectedProblemId)
			);

			if (foundProblem) {
				problem = foundProblem;
				reference_point = foundProblem.objectives.map(
					(obj: { ideal_value: any }) => obj.ideal_value ?? 0
				);
			}
		}
	});
</script>

<div class="p-4">
	{#if problem}
		<div class="mx-auto max-w-xl space-y-4">
			<h2 class="text-lg font-semibold">Reference Point Method</h2>

			<div class="space-y-2">
				{#each problem.objectives as obj, i}
					<div class="flex items-center gap-4">
						<label class="flex-1">{obj.name}</label>
						<input
							type="number"
							bind:value={reference_point[i]}
							class="w-32 rounded border p-2"
							step="0.1"
						/>
					</div>
				{/each}
			</div>

			<Button onclick={solve} class="w-full">Solve</Button>

			{#if solutions.length > 0}
				<div class="mt-8">
					<h3 class="mb-4 text-lg font-semibold">Solutions</h3>
					<div class="space-y-6">
						{#each solutions as solution, i}
							<div class="rounded border p-4">
								<h4 class="mb-2 font-medium">Solution {i + 1}</h4>
								<pre class="mb-4 rounded bg-gray-50 p-2 text-xs">{JSON.stringify(
										solution,
										null,
										2
									)}</pre>
								<div class="grid gap-2">
									{#each problem.objectives as obj, j}
										<div class="flex items-center justify-between">
											<span class="text-sm">{obj.name}:</span>
										</div>
									{/each}
								</div>
							</div>
						{/each}
					</div>
				</div>
			{/if}
		</div>
	{:else}
		<div class="text-center text-gray-500">No problem selected</div>
	{/if}
</div>
