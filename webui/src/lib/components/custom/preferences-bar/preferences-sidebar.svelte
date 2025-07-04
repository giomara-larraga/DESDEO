<script lang="ts">
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import PreferenceSwitcher from './preference-switcher.svelte';
	import { writable } from 'svelte/store';
	import { Button } from '$lib/components/ui/button/index.js';
	import type { components } from '$lib/api/client-types';
	import {
		HorizontalBar,
		HorizontalBarRanges
	} from '$lib/components/visualizations/horizontal-bar';
	import { Input } from '$lib/components/ui/input/index.js';
	import ValidatedTextbox from '../validated-textbox/validated-textbox.svelte';
	import { COLOR_PALETTE } from '$lib/components/visualizations/utils/colors.js';
	type ProblemInfo = components['schemas']['ProblemInfo'];

	const {
		preference_types,
		problem,
		onChange,
		onIterate,
		onFinish,
		showNumSolutions = false,
		ref = null,
		referencePointValues = writable(problem.objectives.map((obj: any) => obj.ideal)), // default if not provided
		handleReferencePointChange = (idx: number, newValue: number) => {} // default noop
	} = $props<{
		preference_types: string[];
		problem: ProblemInfo;
		onChange?: (event: { value: string }) => void;
		onIterate?: () => void;
		onFinish?: () => void;
		showNumSolutions?: boolean;
		ref?: HTMLElement | null;
		referencePointValues?: typeof writable<number[]>;
		handleReferencePointChange?: (idx: number, newValue: number) => void;
	}>();

	// Store for the currently selected preference type
	const selectedPreference = writable(preference_types[0]);
	console.log('Problem in preferences sidebar:', problem);

	function handleReferencePointChangeInternal(idx: number, newValue: number) {
		referencePointValues.update((values) => {
			const updated = [...values];
			updated[idx] = newValue;
			return updated;
		});
		onChange?.({ value: String(newValue) });
	}
</script>

<Sidebar.Root
	{ref}
	collapsible="none"
	class="top-12 flex h-[calc(100vh-6rem)] min-h-[calc(100vh-3rem)] w-[25rem]"
>
	<Sidebar.Header>
		{#if preference_types.length > 1}
			<PreferenceSwitcher
				preferences={preference_types}
				defaultPreference={preference_types[0]}
				onswitch={(e: string) => selectedPreference.set(e)}
			/>
		{:else}
			<Sidebar.MenuButton
				size="lg"
				class="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
			>
				<div class="flex flex-col gap-0.5 leading-none">
					<span class="font-semibold">Preference information</span>
					<span class="text-primary-500">{$selectedPreference}</span>
				</div>
			</Sidebar.MenuButton>
		{/if}
	</Sidebar.Header>
	<Sidebar.Content class="h-full px-4">
		{#if showNumSolutions}
			<Input type="number" placeholder="Number of solutions" class="mb-2 w-full" />
		{/if}
		<!-- Stina: Add your changes here -->
		{#if $selectedPreference === 'Classification'}
			<p class="mb-2 text-sm text-gray-500">Provide one desirable value for each objective.</p>

			{#each problem.objectives as objective}
				<div>
					<HorizontalBar
						axisRanges={[objective.ideal, objective.nadir]}
						solutionValue={objective.ideal}
						selectedValue={objective.ideal}
						barColor="#4f8cff"
						direction="min"
						options={{
							decimalPrecision: 2,
							showPreviousValue: false,
							aspectRatio: 'aspect-[11/2]'
						}}
						onSelect={(value: number) => {
							console.log('Selected value:', value);
							onChange?.({ value: String(value) });
						}}
					/>
				</div>
			{/each}
		{:else if $selectedPreference === 'Reference point'}
			{#each problem.objectives as objective, idx}
				<div class="mb-4 flex flex-col gap-2">
					<div class="text-sm font-semibold text-gray-700">
						{objective.name} ({objective.lowerIsBetter ? 'min' : 'max'})
					</div>
					<div class="flex flex-row">
						<div class="flex w-1/4 flex-col justify-center">
							<span class="text-sm text-gray-500">Value</span>
							<ValidatedTextbox
								placeholder={''}
								min={objective.ideal < objective.nadir ? objective.ideal : objective.nadir}
								max={objective.nadir > objective.ideal ? objective.nadir : objective.ideal}
								value={String($referencePointValues[idx])}
								onChange={(value: String) => {
									const val = Number(value);
									if (!isNaN(val)) handleReferencePointChangeInternal(idx, val);
								}}
							/>
						</div>
						<div class="w-3/4">
							<HorizontalBar
								axisRanges={[
									objective.ideal < objective.nadir ? objective.ideal : objective.nadir,
									objective.nadir > objective.ideal ? objective.nadir : objective.ideal
								]}
								solutionValue={$referencePointValues[idx]}
								selectedValue={$referencePointValues[idx]}
								barColor={COLOR_PALETTE[idx % COLOR_PALETTE.length]}
								direction={objective.lowerIsBetter ? 'min' : 'max'}
								options={{
									decimalPrecision: 2,
									showPreviousValue: false,
									aspectRatio: 'aspect-[11/2]'
								}}
								onSelect={(value: number) => {
									handleReferencePointChangeInternal(idx, value);
								}}
							/>
						</div>
					</div>
				</div>
			{/each}
		{:else if $selectedPreference === 'Ranges'}
			{#each problem.objectives as objective, idx}
				<div class="mb-4 flex flex-col gap-2">
					<div class="text-sm font-semibold text-gray-700">
						{objective.name} ({objective.lowerIsBetter ? 'min' : 'max'})
					</div>
					<div class="flex flex-row">
						<div class="flex w-1/4 flex-col justify-center">
							<span class="text-sm text-gray-500">Value</span>
							<ValidatedTextbox
								placeholder={''}
								min={objective.ideal < objective.nadir ? objective.ideal : objective.nadir}
								max={objective.nadir > objective.ideal ? objective.nadir : objective.ideal}
								value={String($referencePointValues[idx])}
								onChange={(value: String) => {
									const val = Number(value);
									if (!isNaN(val)) handleReferencePointChangeInternal(idx, val);
								}}
							/>
						</div>
						<div class="w-3/4">
							<HorizontalBarRanges
								axisRanges={[
									objective.ideal < objective.nadir ? objective.ideal : objective.nadir,
									objective.nadir > objective.ideal ? objective.nadir : objective.ideal
								]}
								lowerBound={$referencePointValues[idx]}
								upperBound={$referencePointValues[idx]}
								barColor={COLOR_PALETTE[idx % COLOR_PALETTE.length]}
								direction={objective.lowerIsBetter ? 'min' : 'max'}
								options={{
									decimalPrecision: 2,
									showPreviousValue: false,
									aspectRatio: 'aspect-[11/2]'
								}}
							/>
						</div>
					</div>
				</div>
			{/each}
		{:else if $selectedPreference === 'Preferred solution'}
			<p class="mb-2 text-sm text-gray-500">Select one or multiple preferred solutions.</p>
			<!-- 			{#each objectives as item}
				<div class="mb-1">
					<span>{item.name}</span>
				</div>
			{/each} -->
		{:else}
			<p>Select a preference type to view options.</p>
		{/if}
	</Sidebar.Content>
	<Sidebar.Footer>
		<div class="items-right flex justify-end gap-2">
			<Button
				variant="default"
				size="sm"
				onclick={() => {
					selectedPreference.set(preference_types[0]);
					referencePointValues.set(problem.objectives.map((obj: any) => obj.ideal));
					onIterate?.(selectedPreference, referencePointValues);
				}}
			>
				Iterate
			</Button>
			<Button
				variant="secondary"
				size="sm"
				onclick={() => {
					selectedPreference.set(preference_types[0]);
					referencePointValues.set(problem.objectives.map((obj: any) => obj.ideal));
					onFinish?.(referencePointValues);
				}}
			>
				Finish
			</Button>
		</div>
	</Sidebar.Footer>
	<Sidebar.Rail />
</Sidebar.Root>
