<script lang="ts">
	import Dialogs from '$lib/components/custom/dialogs/Dialogs.svelte';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import '../../../app.css';
	let { children } = $props();
</script>

<main class="flex p-2 min-h-[calc(100vh-3rem)]">
	<!-- 3rem = 12 * 0.25rem (h-12) -->

			{@render children()}

</main>
<Dialogs />
