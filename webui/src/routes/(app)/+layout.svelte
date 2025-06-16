<script lang="ts">
	import Topbar from '$lib/components/ui/topbar/Topbar.svelte';
	import '../../app.css';
	let { children } = $props();
</script>

<div class="flex min-h-screen w-full flex-col">
	<Topbar />

	<main class="mx-auto flex flex-col items-center gap-6 text-center">
		{@render children()}
	</main>
</div>
