<script lang="ts">
	import Topbar from '$lib/components/ui/topbar/Topbar.svelte';
	import Logo from '@lucide/svelte/icons/orbit';

	import '../../app.css';
	let { children } = $props();
</script>

<div class="flex min-h-screen w-full flex-col">
	<header class="bg-primary sticky top-0 flex h-14 items-center gap-4 border-b px-4 md:px-6">
		<a
			href="/"
			class="text-primary-foreground mr-4 flex items-center gap-2 text-lg font-semibold md:text-base"
		>
			<Logo class="h-6 w-6" />
			<span>DESDEO</span>
		</a>
		<Topbar />
	</header>

	<main class="mx-auto flex flex-col items-center gap-6 text-center">
		{@render children()}
	</main>
</div>
