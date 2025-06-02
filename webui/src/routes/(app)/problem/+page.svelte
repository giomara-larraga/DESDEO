<script lang="ts">
	import DataTable from './components/data-table.svelte';
	import { data } from './data/problems.js';
	import * as Tabs from '$lib/components/ui/tabs';
	import type { Problem } from './data/schemas';
	import * as Table from '$lib/components/ui/table/index.js';

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
						<div class="my-4 rounded-lg border border-gray-200 bg-gray-50 p-4 shadow-sm">
							<div class="grid w-full grid-cols-2 gap-x-4 gap-y-2 text-justify">
								<!-- Description row -->
								<div class="col-span-2 flex">
									<div class="w-40 font-semibold">Description</div>
									<div class="flex-1">{selectedProblem.description ?? '—'}</div>
								</div>
								<div class="col-span-2 border-b border-gray-300"></div>

								<!-- Characteristics row -->
								<div class="col-span-2 flex items-center">
									<div class="w-40 font-semibold">Characteristics</div>
									<div class="flex flex-wrap gap-2">
										{#if selectedProblem.isLinear}
											<span
												class="inline-block rounded bg-blue-100 px-2 py-1 text-xs font-semibold text-blue-800"
												>Linear</span
											>
										{/if}
										{#if selectedProblem.isConvex}
											<span
												class="inline-block rounded bg-green-100 px-2 py-1 text-xs font-semibold text-green-800"
												>Convex</span
											>
										{/if}
										{#if selectedProblem.isTwiceDifferentiable}
											<span
												class="inline-block rounded bg-purple-100 px-2 py-1 text-xs font-semibold text-purple-800"
												>Twice Differentiable</span
											>
										{/if}
										{#if selectedProblem.isSurrogateAvailable}
											<span
												class="inline-block rounded bg-yellow-100 px-2 py-1 text-xs font-semibold text-yellow-800"
												>Surrogate Available</span
											>
										{/if}
										{#if !selectedProblem.isLinear && !selectedProblem.isConvex && !selectedProblem.isTwiceDifferentiable && !selectedProblem.isSurrogateAvailable}
											<span
												class="inline-block rounded bg-gray-100 px-2 py-1 text-xs font-semibold text-gray-800"
												>None</span
											>
										{/if}
									</div>
								</div>
								<div class="col-span-2 border-b border-gray-300"></div>

								<!-- List of solutions row -->
								<div class="col-span-2 flex">
									<div class="w-40 font-semibold">Available solutions</div>
									<div class="flex-1">
										{#if selectedProblem.solutions?.length}
											<ul class="list-inside list-disc">
												{#each selectedProblem.solutions as solution}
													<li>{solution.id ?? solution.createdByName ?? solution}</li>
												{/each}
											</ul>
										{:else}
											—
										{/if}
									</div>
								</div>
							</div>
						</div>
					{:else}
						Select a problem to see details.
					{/if}
				</Tabs.Content>
				<Tabs.Content value="objectives" class="w-full">
					{#if selectedProblem}
						<!-- Objectives Table -->
						{#if selectedProblem.objectives && Array.isArray(selectedProblem.objectives) && selectedProblem.objectives.length}
							<div class="my-4 rounded-lg border border-gray-200 bg-gray-50 p-4 shadow-sm">
								<Table.Root>
									<Table.Caption
										>List of objective functions for {selectedProblem.name}.</Table.Caption
									>
									<Table.Header>
										<Table.Row>
											<Table.Head class="font-semibold">Name</Table.Head>
											<Table.Head class="font-semibold">Direction</Table.Head>
											<Table.Head class="font-semibold">Ideal</Table.Head>
											<Table.Head class="font-semibold">Nadir</Table.Head>
										</Table.Row>
									</Table.Header>
									<Table.Body>
										{#each selectedProblem.objectives as obj, i}
											<Table.Row>
												<Table.Cell class="text-justify">{obj.name ?? '—'}</Table.Cell>
												<Table.Cell class="text-justify">{obj.direction ?? '—'}</Table.Cell>
												<Table.Cell class="text-justify">{obj.ideal ?? '—'}</Table.Cell>
												<Table.Cell class="text-justify">{obj.nadir ?? '—'}</Table.Cell>
											</Table.Row>
										{/each}
									</Table.Body>
								</Table.Root>
							</div>
						{:else}
							<p>No objective functions details available.</p>
						{/if}
					{:else}
						Select a problem to see details.
					{/if}
				</Tabs.Content>
				<Tabs.Content value="variables" class="w-full">
					{#if selectedProblem}
						<!-- Variables Table -->
						{#if selectedProblem.variables && Array.isArray(selectedProblem.variables) && selectedProblem.variables.length <= 10}
							<div class="my-4 rounded-lg border border-gray-200 bg-gray-50 p-4 shadow-sm">
								<Table.Root>
									<Table.Caption>List of variables for {selectedProblem.name}.</Table.Caption>
									<Table.Header>
										<Table.Row>
											<Table.Head class="font-semibold">Name</Table.Head>
											<Table.Head class="font-semibold">Lower Bound</Table.Head>
											<Table.Head class="font-semibold">Upper Bound</Table.Head>
											<Table.Head class="font-semibold">Type</Table.Head>
										</Table.Row>
									</Table.Header>
									<Table.Body>
										{#each selectedProblem.variables as variable}
											<Table.Row>
												<Table.Cell class="text-justify">{variable.name ?? '—'}</Table.Cell>
												<Table.Cell class="text-justify">{variable.lower ?? '—'}</Table.Cell>
												<Table.Cell class="text-justify">{variable.upper ?? '—'}</Table.Cell>
												<Table.Cell class="text-justify">{variable.type ?? '—'}</Table.Cell>
											</Table.Row>
										{/each}
									</Table.Body>
								</Table.Root>
							</div>
						{:else if selectedProblem.variables && Array.isArray(selectedProblem.variables)}
							<div class="my-4 rounded-lg border border-gray-200 bg-gray-50 p-4 shadow-sm">
								<p class="mb-2 font-medium text-gray-700">
									This problem has
									<span class="font-bold">{selectedProblem.variables.length}</span> variables:
								</p>
								<ul class="ml-2 flex flex-col gap-2">
									<li class="flex items-center gap-2">
										<span
											class="inline-block rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold text-blue-800"
										>
											{selectedProblem.variables.filter((v) => v.type === 'integer').length}
										</span>
										<span class="text-gray-700">integer</span>
									</li>
									<li class="flex items-center gap-2">
										<span
											class="inline-block rounded-full bg-green-100 px-3 py-1 text-xs font-semibold text-green-800"
										>
											{selectedProblem.variables.filter((v) => v.type === 'binary').length}
										</span>
										<span class="text-gray-700">binary</span>
									</li>
									<li class="flex items-center gap-2">
										<span
											class="inline-block rounded-full bg-purple-100 px-3 py-1 text-xs font-semibold text-purple-800"
										>
											{selectedProblem.variables.filter((v) => v.type === 'continuous').length}
										</span>
										<span class="text-gray-700">continuous</span>
									</li>
								</ul>
								<p class="mb-2 text-sm italic text-gray-600">
									Only a summary is shown because this problem has more than 10 variables.
								</p>
							</div>
						{:else}
							<p>No variable details available.</p>
						{/if}
					{:else}
						Select a problem to see details.
					{/if}
				</Tabs.Content>
				<Tabs.Content value="constraints" class="w-full">
					{#if selectedProblem}
						{#if selectedProblem.constraints && Array.isArray(selectedProblem.constraints) && selectedProblem.constraints.length}
							<div class="my-4 rounded-lg border border-gray-200 bg-gray-50 p-4 shadow-sm">
								<Table.Root>
									<Table.Caption>
										List of constraints for {selectedProblem.name}.
									</Table.Caption>
									<Table.Header>
										<Table.Row>
											<Table.Head class="font-semibold">Name</Table.Head>
											<Table.Head class="font-semibold">Type</Table.Head>
											<Table.Head class="font-semibold">Simulated/Analytical</Table.Head>
											<Table.Head class="font-semibold">Convex</Table.Head>
											<Table.Head class="font-semibold">Expensive</Table.Head>
										</Table.Row>
									</Table.Header>
									<Table.Body>
										{#each selectedProblem.constraints as constraint}
											<Table.Row>
												<Table.Cell class="text-justify">{constraint.name ?? '—'}</Table.Cell>
												<Table.Cell class="text-justify">{constraint.type ?? '—'}</Table.Cell>
												<Table.Cell class="text-justify"
													>{constraint.simulated ? 'Simulated' : 'Analytical'}</Table.Cell
												>
												<Table.Cell class="text-justify"
													>{constraint.convex ? 'Yes' : 'No'}</Table.Cell
												>
												<Table.Cell class="text-justify"
													>{constraint.expensive ? 'Yes' : 'No'}</Table.Cell
												>
											</Table.Row>
										{/each}
									</Table.Body>
								</Table.Root>
							</div>
						{:else}
							<p>No constraint details available.</p>
						{/if}
					{:else}
						Select a problem to see details.
					{/if}
				</Tabs.Content>
			</Tabs.Root>
		</div>
	</div>
</div>
