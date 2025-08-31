<script lang="ts">
	import type { ProblemInfo } from '$lib/types/interactive-method';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import Button from '$lib/components/ui/button/button.svelte';
	import { Slider } from '$lib/components/ui/slider';

	export let problem: ProblemInfo;
	export let currentPreference: number[] = [];
	export let onPreferenceChange: (values: number[]) => void;
	export let numSolutions: number = 1;

	$: objectives = problem?.objectives || [];

	function handlePreferenceInput(index: number, value: number) {
		const newPreference = [...currentPreference];
		newPreference[index] = value;
		onPreferenceChange(newPreference);
	}
</script>

<div class="space-y-6 p-4">
	<div class="space-y-2">
		<Label>Number of solutions</Label>
		<Input type="number" min="1" max="10" bind:value={numSolutions} />
	</div>

	<div class="space-y-4">
		<Label>Preferences</Label>
		{#each objectives as objective, i}
			<div class="space-y-2">
				<Label>{objective.name}</Label>
				<Slider
					min={objective.minimize ? objective.ideal : objective.nadir}
					max={objective.minimize ? objective.nadir : objective.ideal}
					step={0.01}
					value={currentPreference[i] || 0}
					onValueChange={(value) => handlePreferenceInput(i, value)}
				/>
				<Input
					type="number"
					value={currentPreference[i] || 0}
					onChange={(e) => handlePreferenceInput(i, parseFloat(e.target.value))}
				/>
			</div>
		{/each}
	</div>
</div>
