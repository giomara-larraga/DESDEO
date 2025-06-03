<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { data } from '../problem/data/problems.js';
  import { Button, buttonVariants } from '$lib/components/ui/button';


  let problemId: string | null = null;
  let problem: any = null;

  onMount(() => {
    problemId = $page.url.searchParams.get('problemId');
    if (problemId) {
      problem = data.find(p => p.id === problemId);
    }
  });
</script>



<div class="px-8">
	<h1 class="primary mb-2 text-pretty pt-4 text-left text-lg font-semibold lg:text-xl">
		Methods
	</h1>
	<p class="text-md text-justify text-gray-700 mb-4">
		This page shows the list of methods available in DESDEO. If you have already selected a problem, you can start solving it with the method  you select. 
	</p>
    <div>
        {#if problem}
            <p class="text-md text-justify text-gray-700">
                You are currently viewing methods suitable for the selected problem: <span class="font-semibold">{problem.name}</span>.
            </p>
            <Button
                variant="secondary"
                href="/problem">
                Change selected problem
            </Button>
        {:else}
            <p class="text-md text-justify text-gray-700">
                You are seeing the list of methods available in DESDEO. Please select a problem if you want to use any of the methods.
            </p>
        {/if}
    </div>
	<div class="mt-4 grid grid-cols-2 gap-8 sm:grid-cols-1 lg:grid-cols-2">
        
       
    </div>
</div>