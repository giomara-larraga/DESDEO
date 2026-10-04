<script lang="ts">
	import Dialogs from '$lib/components/custom/dialogs/Dialogs.svelte';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import '../../../app.css';
	let { children } = $props();
</script>

<main class="min-h-[calc(100dvh-3rem)] min-w-0">
	{@render children()}
</main>
<Dialogs />
