<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { data } from '../problem/data/problems.js';
	import { methods } from './data.js';
	import { Button } from '$lib/components/ui/button';
	import * as Card from '$lib/components/ui/card/index.js';
	import Settings from '@lucide/svelte/icons/settings';
	import Play from '@lucide/svelte/icons/play';

	let problemId: string | null = null;
	let problem: any = null;
	let selectedVariantIdx: string | null = null;

	onMount(() => {
		problemId = $page.url.searchParams.get('problemId');
		if (problemId) {
			problem = data.find((p) => p.id === problemId);
		}
	});
</script>

<div class="px-8">
	<h1 class="primary mb-2 text-pretty pt-4 text-left text-lg font-semibold lg:text-xl">Methods</h1>

	{#if problem}
		<p class="text-md mb-2 text-justify text-gray-700">
			You are currently viewing methods suitable for the selected problem: <span
				class="font-semibold">{problem.name}</span
			>.
		</p>
		<Button variant="secondary" href="/problem">Change selected problem</Button>
	{:else}
		<p class="text-md mb-2 text-justify text-gray-700">
			You are seeing the list of methods available in DESDEO. Please select a problem if you want to
			use any of the methods.
		</p>
		<Button variant="secondary" href="/problem">Select a problem</Button>
	{/if}

	<div class="mt-4 grid grid-cols-3 gap-8 sm:grid-cols-1 lg:grid-cols-3">
		{#each methods as method}
			<Card.Root>
				<Card.Header class="flex items-start justify-between pb-1">
					<h2 class="text-lg font-semibold">{method.name}</h2>
				</Card.Header>
				<Card.Content class="text-left">
					{#if method.variants}
						<div class="mb-2">
							<span class="font-medium">Variants:</span>
							<table class="mt-2 min-w-full border text-sm">
								<thead>
									<tr class="bg-gray-100">
										<th class="px-2 py-1 text-left">Name</th>
										<th class="px-2 py-1 text-left">Preference Types</th>
										<th class="px-2 py-1 text-left">Problem Types</th>
									</tr>
								</thead>
								<tbody>
									{#each method.variants as variant, i}
										<tr
											class="cursor-pointer border-t hover:bg-gray-100 {selectedVariantIdx ===
											`${method.name}-${i}`
												? 'bg-gray-200'
												: ''}"
											on:click={() => (selectedVariantIdx = `${method.name}-${i}`)}
										>
											<td class="px-2 py-1">{variant.name}</td>
											<td class="px-2 py-1">
												{variant.preferencesType?.join(', ') ?? ''}
											</td>
											<td class="px-2 py-1">
												{variant.problemtypes?.join(', ') ?? ''}
											</td>
										</tr>
									{/each}
								</tbody>
							</table>
						</div>
					{:else}
						<div>
							{#if method.preferencesType}
								<span class="font-medium">Preference types:</span>
								<ul class="ml-4 list-inside list-disc">
									{#each method.preferencesType as type}
										<li>{type}</li>
									{/each}
								</ul>
							{/if}
							{#if method.problemtypes}
								<span class="font-medium">Problem types:</span>
								<ul class="ml-4 list-inside list-disc">
									{#each method.problemtypes as type}
										<li>{type}</li>
									{/each}
								</ul>
							{/if}
						</div>
					{/if}
				</Card.Content>
				<Card.Footer class="mt-auto flex items-center justify-end gap-2">
					{#if !method.variants}
						<Button
							variant="default"
							disabled={!problem}
							href={`/solve/${method.shortName}?problemId=${problemId}`}
						>
							<Play class="mr-1 inline" />
							Use {method.name}
						</Button>
					{:else}
						<Button
							variant="default"
							disabled={!problem ||
								selectedVariantIdx == null ||
								!selectedVariantIdx.startsWith(method.name)}
						>
							<Play class="mr-1 inline" />
							{#if selectedVariantIdx && selectedVariantIdx.startsWith(method.name)}
								Use {method.variants[+selectedVariantIdx.split('-')[1]].name}
							{:else}
								Select a variant
							{/if}
						</Button>
					{/if}
					<Button variant="ghost" size="icon" aria-label="Settings">
						<Settings class="size-4" strokeWidth={1} />
					</Button>
				</Card.Footer>
			</Card.Root>
		{/each}
	</div>
</div>
