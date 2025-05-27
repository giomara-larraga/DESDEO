<script lang="ts">
	import Topbar from '$lib/components/ui/topbar/Topbar.svelte';
</script>

<div class="flex min-h-screen w-full flex-col">
	<Topbar />

	<main
		class="flex min-h-[calc(100vh_-_theme(spacing.16))] flex-1 flex-col gap-4 bg-teal-50 bg-white p-4 md:gap-8 md:p-10"
	>
		This is an example of how to use the Topbar in a layout.
	</main>
</div>
