<script lang="ts">
	import AppSidebar from './preferences-sidebar.svelte';
	import AdvancedSidebar from './advanced-sidebar.svelte';
	import Logo from '@lucide/svelte/icons/orbit';

	import * as Breadcrumb from '$lib/components/ui/breadcrumb/index.js';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import Topbar from '$lib/components/ui/topbar/Topbar.svelte';
	import '../../app.css';
</script>

<header
	class="bg-primary sticky top-0 z-10 flex h-12 items-center justify-between gap-4 border-b px-4 md:px-6"
>
	<div class="flex items-center gap-2">
		<Separator orientation="vertical" class="bg-primary text-primary-foreground mr-2 h-4" />
		<a
			href="/"
			class="text-primary-foreground mr-4 flex items-center gap-2 text-lg font-semibold md:text-base"
		>
			<Logo class="h-6 w-6" />
			<span>DESDEO</span>
		</a>
	</div>
	<Topbar />
</header>

<main class="flex min-h-[calc(100vh-3rem)]">
	<!-- 3rem = 12 * 0.25rem (h-12) -->
	<Sidebar.Provider style="--sidebar-width: 20rem; --sidebar-width-mobile: 20rem;">
		<AppSidebar />
		<Sidebar.Inset>
			<div class="flex flex-1 flex-col gap-4 p-4">
				<div class="grid auto-rows-min gap-4 md:grid-cols-3">
					<div class="bg-muted/50 aspect-video rounded-xl"></div>
					<div class="bg-muted/50 aspect-video rounded-xl"></div>
					<div class="bg-muted/50 aspect-video rounded-xl"></div>
				</div>
				<div class="bg-muted/50 min-h-[100vh] flex-1 rounded-xl md:min-h-min"></div>
			</div>
		</Sidebar.Inset>
		<AdvancedSidebar />
	</Sidebar.Provider>
</main>
