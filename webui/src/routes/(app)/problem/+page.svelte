<script lang="ts">
	import DataTable from './components/data-table.svelte';
	import { data } from './data/problems.js';
</script>

<div>
	<h1 class="text-primary mb-2 text-pretty pt-4 text-lg font-semibold lg:text-xl">
		Optimization Problems
	</h1>
	<p class="text-center text-lg text-gray-700">
		Explore the optimization problems available in DESDEO or add a new one.
	</p>
	<div class="mt-4 grid grid-cols-2 gap-8 sm:grid-cols-1 lg:grid-cols-2">
		<div class="w-full"><DataTable {data} /></div>
		<div class="w-full">grr</div>
	</div>
</div>
