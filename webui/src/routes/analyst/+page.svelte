<script lang="ts">
	import { Topbar } from '$lib/components/ui/topbar';

	let { data } = $props();
</script>

<div class="flex min-h-screen w-full flex-col">
	<Topbar />

	<main class="mx-auto flex max-w-5xl flex-col items-center gap-6 px-4 py-8">
		<div class="space-y-6 text-center">
	<h1 class="text-2xl font-semibold">Analyst Workspace</h1>
	<p class="text-muted-foreground mt-2">
		This page is restricted to users with the analyst role.
	</p>
	<div class="mt-4 rounded-md border p-4">
		<p>Welcome, {data.user.username}.</p>
		<p class="text-muted-foreground text-sm">Role: {data.user.role}</p>
	</div>
</div>
    </main>
</div>
