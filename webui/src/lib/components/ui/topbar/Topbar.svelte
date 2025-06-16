<script lang="ts">
	import CircleUser from '@lucide/svelte/icons/user-circle';
	import Method from '@lucide/svelte/icons/brain-circuit';
	import Logo from '@lucide/svelte/icons/orbit';
	import Problem from '@lucide/svelte/icons/puzzle';
	import Archive from '@lucide/svelte/icons/archive';
	import HelpCircle from '@lucide/svelte/icons/circle-help';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
</script>

<div class="space-between flex flex-row">
	<!-- Right: Navigation -->
	<nav
		class="flex flex-1 flex-col justify-end gap-6 text-lg font-medium md:flex md:flex-row md:items-center md:gap-5 md:text-sm lg:gap-6"
	>
		<a
			href="/problem"
			class="text-primary-foreground hover:text-secondary flex items-center gap-1 transition-colors"
		>
			<Problem class="h-4 w-4" />
			Problems
		</a>
		<a
			href="/method"
			class="text-primary-foreground hover:text-secondary flex items-center gap-1 transition-colors"
		>
			<Method class="h-4 w-4" />
			Methods
		</a>
		<a
			href="/archive"
			class="text-primary-foreground hover:text-secondary flex items-center gap-1 transition-colors"
		>
			<Archive class="h-4 w-4" />
			Archive
		</a>
		<a
			href="/help"
			class="text-primary-foreground hover:text-secondary flex items-center gap-1 transition-colors"
		>
			<HelpCircle class="h-4 w-4" />
			Help
		</a>
		<DropdownMenu.Root>
			<DropdownMenu.Trigger>
				<span
					class="text-primary-foreground hover:text-secondary flex items-center gap-1 transition-colors"
				>
					<CircleUser class="h-4 w-4" />
					User
				</span>
			</DropdownMenu.Trigger>
			<DropdownMenu.Content align="end">
				<DropdownMenu.Label>My Account</DropdownMenu.Label>
				<DropdownMenu.Separator />
				<DropdownMenu.Item>Settings</DropdownMenu.Item>
				<DropdownMenu.Item>Support</DropdownMenu.Item>
				<DropdownMenu.Separator />
				<DropdownMenu.Item>Logout</DropdownMenu.Item>
			</DropdownMenu.Content>
		</DropdownMenu.Root>
	</nav>
</div>
