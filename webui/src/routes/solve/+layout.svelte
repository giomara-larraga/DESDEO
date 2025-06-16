<script lang="ts">
	import AppSidebar from './preferences-sidebar.svelte';
	import AdvancedSidebar from './advanced-sidebar.svelte';
	import Logo from '@lucide/svelte/icons/orbit';
	import * as Resizable from '$lib/components/ui/resizable/index.js';

	import * as Breadcrumb from '$lib/components/ui/breadcrumb/index.js';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import Topbar from '$lib/components/ui/topbar/Topbar.svelte';
	import '../../app.css';
	import * as Menubar from '$lib/components/ui/menubar/index.js';
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
	<Sidebar.Provider
		class="flex min-h-[calc(100vh-3rem)]"
		style="--sidebar-width: 20rem; --sidebar-width-mobile: 20rem;"
	>
		<AppSidebar />
		<Sidebar.Inset class="bg-muted/50">
			<Resizable.PaneGroup direction="vertical">
				<Resizable.Pane class="p-2">
					<div class="flex items-center justify-between">
						<span>Alternatives</span>
						<Menubar.Root>
							<Menubar.Menu>
								<Menubar.Trigger>View</Menubar.Trigger>
								<Menubar.Content>
									<Menubar.Item>
										Current iteration<Menubar.Shortcut>⌘T</Menubar.Shortcut>
									</Menubar.Item>
									<Menubar.Item>
										Best candidates <Menubar.Shortcut>⌘N</Menubar.Shortcut>
									</Menubar.Item>
									<Menubar.Item>All solutions</Menubar.Item>
								</Menubar.Content>
							</Menubar.Menu>
							<Menubar.Menu>
								<Menubar.Trigger>Plot</Menubar.Trigger>
								<Menubar.Content>
									<Menubar.Item>
										Parallel coordinates <Menubar.Shortcut>⌘Z</Menubar.Shortcut>
									</Menubar.Item>
									<Menubar.Item>
										Bar charts <Menubar.Shortcut>⇧⌘Z</Menubar.Shortcut>
									</Menubar.Item>

									<Menubar.Item>Petal diagram</Menubar.Item>
									<Menubar.Item>Spider chart</Menubar.Item>
									<Menubar.Item>Scatter plot</Menubar.Item>
								</Menubar.Content>
							</Menubar.Menu>
							<Menubar.Menu>
								<Menubar.Trigger>Save</Menubar.Trigger>
								<Menubar.Content>
									<Menubar.Separator />
									<Menubar.Item inset>
										Reload <Menubar.Shortcut>⌘R</Menubar.Shortcut>
									</Menubar.Item>
									<Menubar.Item inset>
										Force Reload <Menubar.Shortcut>⇧⌘R</Menubar.Shortcut>
									</Menubar.Item>
									<Menubar.Separator />
									<Menubar.Item inset>Toggle Fullscreen</Menubar.Item>
									<Menubar.Separator />
									<Menubar.Item inset>Hide Sidebar</Menubar.Item>
								</Menubar.Content>
							</Menubar.Menu>
						</Menubar.Root>
					</div>
				</Resizable.Pane>
				<Resizable.Handle />
				<Resizable.Pane class="p-2">
					<span>Best candidates</span>
				</Resizable.Pane>
			</Resizable.PaneGroup>
		</Sidebar.Inset>
		<AdvancedSidebar />
	</Sidebar.Provider>
</main>
