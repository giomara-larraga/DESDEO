<script lang="ts">
	import DataTable from './components/data-table.svelte';
	import { data } from './data/problems.js';
	import * as Tabs from '$lib/components/ui/tabs';
	import type { Problem } from './data/schemas';

	let selectedProblem: Problem;
</script>

<div class="px-8">
	<h1 class="primary mb-2 text-pretty pt-4 text-left text-lg font-semibold lg:text-xl">
		Optimization Problems
	</h1>
	<p class="text-md text-justify text-gray-700">
		Here you can select one of the problems available in DESDEO to start optimizing. According to
		the selected problem, you will be able to select the most suitable method according to the types
		of preferences you want to utilize.
	</p>
	<div class="mt-4 grid grid-cols-2 gap-8 sm:grid-cols-1 lg:grid-cols-2">
		<div class="w-full">
			<DataTable {data} on:select={(e) => (selectedProblem = e.detail)} />
		</div>
		<div class="w-full">
			<Tabs.Root value="general" class="w-full">
				<Tabs.List class="w-full">
					<Tabs.Trigger value="general">General</Tabs.Trigger>
					<Tabs.Trigger value="objectives">Objectives</Tabs.Trigger>
					<Tabs.Trigger value="variables">Variables</Tabs.Trigger>
					<Tabs.Trigger value="constraints">Constraints</Tabs.Trigger>
				</Tabs.List>
				<Tabs.Content value="general" class="w-full">
					{#if selectedProblem}
						General information of the {selectedProblem.name} problem
					{:else}
						Select a problem to see details.
					{/if}
				</Tabs.Content>
				<Tabs.Content value="objectives" class="w-full">
					{#if selectedProblem}
						The problem has {selectedProblem.objectives} objective functions.
					{:else}
						Select a problem to see details.
					{/if}
				</Tabs.Content>
				<Tabs.Content value="variables" class="w-full">
					{#if selectedProblem}
						The problem has {selectedProblem.variables} variables.
					{:else}
						Select a problem to see details.
					{/if}
				</Tabs.Content>
				<Tabs.Content value="constraints" class="w-full"
					>This problem has [X] constraints.</Tabs.Content
				>
			</Tabs.Root>
		</div>
	</div>
</div>
