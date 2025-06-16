<script lang="ts">
	import '../../app.css';
	import { Input } from '$lib/components/ui/input/index.js';
	import GalleryVerticalEndIcon from '@lucide/svelte/icons/orbit';
	import main_image from '$lib/assets/main.jpg';
	import SuperDebug, { type Infer, type SuperValidated, superForm } from 'sveltekit-superforms';
	import { zodClient } from 'sveltekit-superforms/adapters';
	import { loginSchema, type LoginSchema } from '$lib/core/user_and_login';
	import { toast } from 'svelte-sonner';
	import * as Form from '$lib/components/ui/form/index.js';
	import { login } from '$lib/core/user_and_login';
	import { goto } from '$app/navigation';

	export let data: { form: SuperValidated<Infer<LoginSchema>> };

	const form = superForm(data.form, {
		validators: zodClient(loginSchema),
		onUpdated: ({ form: f }) => {
			if (f.valid) {
				toast.success(`You submitted ${JSON.stringify(f.data, null, 2)}`);
			} else {
				toast.error('Please fix the errors in the form.');
			}
		}
	});

	const { form: formData, enhance } = form;

	let error = '';

	async function handleLogin(event: Event) {
		event.preventDefault();
		const { username, password } = $formData;
		if (!username || !password) {
			error = 'Username and password are required.';
			return;
		}
		const result = await login(username, password);
		if (result && result.access_token) {
			goto('/dashboard');
		} else {
			error = 'Login failed. Please check your credentials.';
		}
	}
</script>

<div class="grid min-h-svh lg:grid-cols-2">
	<div class="left-inner-shadow flex flex-col gap-4 p-6 md:p-10">
		<div class="flex justify-center gap-2 md:justify-start">
			<a href="##" class="flex items-center gap-2 font-medium">
				<div
					class="bg-primary text-primary-foreground flex size-6 items-center justify-center rounded-md"
				>
					<GalleryVerticalEndIcon class="size-4" />
				</div>
				DESDEO
			</a>
		</div>
		<div class="flex flex-1 items-center justify-center">
			<div class="w-full max-w-xs">
				<form method="POST" class="flex flex-col gap-6" on:submit|preventDefault={handleLogin}>
					<div class="flex flex-col items-center gap-2 text-center">
						<h1 class="text-2xl font-bold">Login to your account</h1>
						<p class="text-muted-foreground text-balance text-sm">
							Enter your username below to login to your account
						</p>
					</div>

					<div class="grid gap-6">
						<Form.Field {form} name="username" class="grid gap-3">
							<Form.Control>
								{#snippet children({ props })}
									<Form.Label>Username</Form.Label>
									<Input {...props} bind:value={$formData.username} />
								{/snippet}
							</Form.Control>
							<Form.FieldErrors />
						</Form.Field>
						<Form.Field {form} name="password" class="grid gap-3">
							<Form.Control>
								{#snippet children({ props })}
									<Form.Label>Password</Form.Label>
									<Input {...props} bind:value={$formData.password} type="password" />
								{/snippet}
							</Form.Control>
							<Form.FieldErrors />
						</Form.Field>
						<Form.Button type="submit" class="w-full">Login</Form.Button>
					</div>
					{#if error}
						<div class="text-red-600">{error}</div>
					{/if}
					<div class="text-center text-sm">
						Don&apos;t have an account?
						<a href="##" class="underline underline-offset-4"> Sign up </a>
						or
						<a href="/dashboard" class="underline underline-offset-4">
							explore DESDEO as a guest.
						</a>
					</div>
				</form>
			</div>
		</div>
	</div>
	<div class="bg-muted relative hidden lg:block">
		<img
			src={main_image}
			alt="placeholder"
			class="absolute inset-0 h-full w-full object-cover dark:brightness-[0.2] dark:grayscale"
		/>
		<div class="bg-primary-600 pointer-events-none absolute inset-0 opacity-20"></div>
	</div>
</div>
