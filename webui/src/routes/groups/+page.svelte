<script lang="ts">
	/**
	 * +page.svelte
	 *
	 * @description
	 * This page displays a list of user groups in DESDEO and allows users to view and interact with the problem associated with each group.
	 * It features a data table for group selection and a tabbed interface for viewing problem details within each group.
	 * Each table supports detailed dialogs for mathematical formulations, and the UI is responsive to the selected group and its problem.
	 *
	 * @props
	 * @property {Object} data - Contains lists of groups and their associated problems.
	 * @property {ProblemInfo[]} data.problemList - List of problems associated with groups.
	 * @property {GroupInfo[]} data.groupList - List of user groups.
	 *
	 * @features
	 * - DataTable for selecting a group, showing the group name and associated problem.
	 * - Tabbed interface for viewing problem details within the group.
	 * - Responsive UI: shows a message if no groups are available, or if no group is selected.
	 * - Uses Svelte runes mode for reactivity.
	 *
	 * @dependencies
	 * - DataTable: Custom data table component for groups.
	 * - Tabs, Table, Dialog: UI components.
	 * - MathExpressionRenderer: Renders math expressions.
	 * - OpenAPI-generated ProblemInfo type.
	 * - methodSelection: Svelte store for the currently selected problem and method.
	 */

	import * as Tabs from '$lib/components/ui/tabs';
	import * as Table from '$lib/components/ui/table/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import * as Tooltip from '$lib/components/ui/tooltip/index.js';
	import { buttonVariants } from '$lib/components/ui/button';
	import { methodSelection } from '../../stores/methodSelection';
	import { auth } from '../../stores/auth';
	import { goto } from '$app/navigation';
	import Play from '@lucide/svelte/icons/play';

	import type {
		GroupPublic,
		GroupSessionPublic,
		ProblemInfo
	} from '$lib/gen/endpoints/DESDEOFastAPI';

	import type { PageProps } from './$types';
	import MathExpressionRenderer from '$lib/components/ui/MathExpressionRenderer/MathExpressionRenderer.svelte';

	let { data }: PageProps = $props();

	let groupList = $derived(data.groupList);
	let sessionRows = $derived(data.sessionRows);

	let selectedGroup = $state<GroupPublic | undefined>(undefined);
	let selectedGroupSession = $state<GroupSessionPublic | undefined>(undefined);
	let selectedProblem = $state<ProblemInfo | undefined>(undefined);
	
	function getUserRole(group: GroupPublic, userId: number | undefined): string {
		if (userId === undefined) return '';

		if (userId === group.owner_id) {
			return 'Owner';
		}

		if ((group.users ?? []).some((member) => member.id === userId)) {
			return 'DM';
		}

		return '';
	}

	function getParticipantCount(group: GroupPublic): number {
		const participantIds = new Set((group.users ?? []).map((member) => member.id));
		participantIds.add(group.owner_id);

		return participantIds.size;
	}

	async function openGroupSession(
		groupSession: GroupSessionPublic,
		problem: ProblemInfo
	): Promise<void> {
		methodSelection.setProblem(problem.id);

		switch (groupSession.method) {
			case 'gnimbus':
				await goto(
						`/interactive_methods/GNIMBUS` +
						`?group_session=${groupSession.id}`
					);
				break;

			case 'gdm-score-bands':
				await goto(
					`/interactive_methods/GDM-SCORE-bands?group_session=${groupSession.id}`
				);
				break;

			default:
				throw new Error(
					`Unsupported group method: ${groupSession.method}`
				);
		}
	}
</script>

<svelte:head>
	<title>Groups | DESDEO</title>
	<meta name="description" content="a list of user groups in DESDEO" />
</svelte:head>

<div class="px-8">
	<h1 class="primary mb-2 pt-4 text-left text-lg font-semibold text-pretty lg:text-xl">
		User Groups
	</h1>
	<p class="text-md text-justify text-gray-700">
		Here you can view your DESDEO groups and their decision-making sessions.
		A group can have multiple sessions, and each session is associated with
		an optimization problem and a decision-making method.
	</p>
	{#if groupList.length === 0}
		<p class="text-gray-600">You are not a member of any groups yet.</p>
	{:else if sessionRows.length === 0}
		<p class="mt-4 text-gray-600">
			Your groups do not have any decision-making sessions yet.
		</p>
	{:else}
		<div class="mt-4 grid grid-cols-2 gap-8 sm:grid-cols-1 lg:grid-cols-2">
			<div class="w-full">
				<Table.Root>
					<Table.Caption>List of your DESDEO groups</Table.Caption>
					<Table.Header>
						<Table.Row>
							<Table.Head class="font-semibold">Group</Table.Head>
							<Table.Head class="font-semibold">Problem</Table.Head>
							<Table.Head class="font-semibold">Method</Table.Head>
							<Table.Head class="font-semibold">Your Role</Table.Head>
							<Table.Head class="font-semibold">Participants</Table.Head>
							<Table.Head class="font-semibold">Open</Table.Head>
						</Table.Row>
					</Table.Header>
					<Table.Body>
	{#each sessionRows as row}
		<Table.Row
			class={selectedGroupSession?.id === row.groupSession.id
				? 'bg-gray-100'
				: ''}
			onclick={() => {
				selectedGroup = row.group;
				selectedGroupSession = row.groupSession;
				selectedProblem = row.problem;
			}}
			role="button"
			tabindex={0}
		>
			<Table.Cell class="text-justify">
				{row.group.name}
			</Table.Cell>

			<Table.Cell class="text-justify">
				{row.problem.name}
			</Table.Cell>

			<Table.Cell class="text-justify">
				{row.groupSession.method}
			</Table.Cell>

			<Table.Cell class="text-justify">
				{getUserRole(row.group, $auth?.user?.id)}
			</Table.Cell>

			<Table.Cell class="text-justify">
				{getParticipantCount(row.group)} participants
			</Table.Cell>

			<Table.Cell>
				<Tooltip.Provider>
					<Tooltip.Root>
						<Tooltip.Trigger
							class={buttonVariants({
								variant: 'outline',
								size: 'icon',
								class: 'text-secondary-foreground flex h-8 w-8 cursor-pointer p-0'
							})}
							onclick={async (event) => {
								event.stopPropagation();

								selectedGroup = row.group;
								selectedGroupSession = row.groupSession;
								selectedProblem = row.problem;

								methodSelection.setProblem(row.problem.id);

								await openGroupSession(row.groupSession, row.problem);
							}}
						>
							<Play />
						</Tooltip.Trigger>

						<Tooltip.Content>
							<p>Open group session</p>
						</Tooltip.Content>
					</Tooltip.Root>
				</Tooltip.Provider>
			</Table.Cell>
		</Table.Row>
	{/each}
</Table.Body>
				</Table.Root>
			</div>
			<div class="w-full">
				<Tabs.Root value="general" class="w-full">
					<Tabs.List class="w-full">
						<Tabs.Trigger value="general">General</Tabs.Trigger>
						<Tabs.Trigger value="objectives">Objectives</Tabs.Trigger>
						<Tabs.Trigger value="variables">Variables</Tabs.Trigger>
						<Tabs.Trigger value="constraints">Constraints</Tabs.Trigger>
						<Tabs.Trigger value="extra">Extra Functions</Tabs.Trigger>
					</Tabs.List>

					<!-- General Tab -->
					<Tabs.Content value="general" class="w-full">
						{#if selectedProblem}
							<div class="my-4 rounded-lg border border-gray-200 bg-gray-50 p-4 shadow-sm">
								<div class="grid w-full grid-cols-2 gap-x-4 gap-y-2 text-justify">
									<div class="col-span-2 flex">
										<div class="w-40 font-semibold">Description</div>
										<div class="flex-1">{selectedProblem.description ?? '—'}</div>
									</div>
									<div class="col-span-2 border-b border-gray-300"></div>
									<div class="col-span-2 flex">
										<div class="w-40 font-semibold">Domain</div>
										<div class="flex-1">{selectedProblem.variable_domain ?? '—'}</div>
									</div>
									<div class="col-span-2 border-b border-gray-300"></div>
									<div class="col-span-2 flex items-center">
										<div class="w-40 font-semibold">Characteristics</div>
										<div class="flex flex-wrap gap-2">
											{#if selectedProblem.is_linear}
												<span
													class="inline-block rounded bg-blue-100 px-2 py-1 text-xs font-semibold text-blue-800"
													>Linear</span
												>
											{/if}
											{#if selectedProblem.is_convex}
												<span
													class="inline-block rounded bg-green-100 px-2 py-1 text-xs font-semibold text-green-800"
													>Convex</span
												>
											{/if}
											{#if selectedProblem.is_twice_differentiable}
												<span
													class="inline-block rounded bg-purple-100 px-2 py-1 text-xs font-semibold text-purple-800"
													>Twice Differentiable</span
												>
											{/if}
											{#if !selectedProblem.is_linear && !selectedProblem.is_convex && !selectedProblem.is_twice_differentiable}
												<span
													class="inline-block rounded bg-gray-100 px-2 py-1 text-xs font-semibold text-gray-800"
													>None</span
												>
											{/if}
										</div>
									</div>
									<div class="col-span-2 border-b border-gray-300"></div>
								</div>
							</div>
						{:else}
							Select a problem to see details.
						{/if}
					</Tabs.Content>

					<!-- Objectives Tab -->
					<Tabs.Content value="objectives" class="w-full">
						{#if selectedProblem}
							{#if selectedProblem.objectives && Array.isArray(selectedProblem.objectives) && selectedProblem.objectives.length}
								<div class="my-4 rounded-lg border border-gray-200 bg-gray-50 p-4 shadow-sm">
									<Table.Root>
										<Table.Caption>
											List of objective functions for {selectedProblem.name}.
										</Table.Caption>
										<Table.Header>
											<Table.Row>
												<Table.Head class="font-semibold">Name</Table.Head>
												<Table.Head class="font-semibold">Type</Table.Head>
												<Table.Head class="font-semibold">Direction</Table.Head>
												<Table.Head class="font-semibold">Ideal</Table.Head>
												<Table.Head class="font-semibold">Nadir</Table.Head>
												<Table.Head class="font-semibold">Formulation</Table.Head>
											</Table.Row>
										</Table.Header>
										<Table.Body>
											{#each selectedProblem.objectives as obj}
												<Table.Row>
													<Table.Cell class="text-justify"
														>{(obj.symbol || obj.name) ?? '_'}</Table.Cell
													>
													<Table.Cell class="text-justify">{obj.objective_type ?? '—'}</Table.Cell>
													<Table.Cell class="text-justify"
														>{obj.maximize ? 'Maximize' : 'Minimize'}</Table.Cell
													>
													<Table.Cell class="text-justify">{obj.ideal ?? '—'}</Table.Cell>
													<Table.Cell class="text-justify">{obj.nadir ?? '—'}</Table.Cell>
													<Table.Cell class="text-justify">
														<Dialog.Root>
															<Dialog.Trigger
																class={buttonVariants({ variant: 'outline' })}
																disabled={!obj.func}
															>
																View Details
															</Dialog.Trigger>
															<Dialog.Content
																class="max-h-[80vh] w-full max-w-4xl overflow-x-auto overflow-y-auto"
															>
																<Dialog.Header>
																	<Dialog.Title>Objective Formulation</Dialog.Title>
																	<Dialog.Description>
																		View the formulation of the {obj.symbol || obj.name} objective below.
																	</Dialog.Description>
																</Dialog.Header>
																<div class="grid gap-4 py-4">
																	<div>
																		<MathExpressionRenderer func={obj.func} />
																	</div>
																</div>
															</Dialog.Content>
														</Dialog.Root>
													</Table.Cell>
												</Table.Row>
											{/each}
										</Table.Body>
									</Table.Root>
								</div>
							{:else}
								<p>No objective functions details available.</p>
							{/if}
						{:else}
							Select a problem to see details.
						{/if}
					</Tabs.Content>

					<!-- Variables Tab -->
					<Tabs.Content value="variables" class="w-full">
						{#if selectedProblem}
							{#if selectedProblem.variables && Array.isArray(selectedProblem.variables) && selectedProblem.variables.length <= 10}
								<div class="my-4 rounded-lg border border-gray-200 bg-gray-50 p-4 shadow-sm">
									<Table.Root>
										<Table.Caption>List of variables for {selectedProblem.name}.</Table.Caption>
										<Table.Header>
											<Table.Row>
												<Table.Head class="font-semibold">Name</Table.Head>
												<Table.Head class="font-semibold">Lower Bound</Table.Head>
												<Table.Head class="font-semibold">Upper Bound</Table.Head>
												<Table.Head class="font-semibold">Type</Table.Head>
											</Table.Row>
										</Table.Header>
										<Table.Body>
											{#each selectedProblem.variables as variable}
												<Table.Row>
													<Table.Cell class="text-justify"
														>{(variable.symbol || variable.name) ?? '—'}</Table.Cell
													>
													<Table.Cell class="text-justify">{variable.lowerbound ?? '—'}</Table.Cell>
													<Table.Cell class="text-justify">{variable.upperbound ?? '—'}</Table.Cell>
													<Table.Cell class="text-justify"
														>{variable.variable_type ?? '—'}</Table.Cell
													>
												</Table.Row>
											{/each}
										</Table.Body>
									</Table.Root>
								</div>
							{:else if selectedProblem.variables && Array.isArray(selectedProblem.variables)}
								<div class="my-4 rounded-lg border border-gray-200 bg-gray-50 p-4 shadow-sm">
									<p class="mb-2 font-medium text-gray-700">
										This problem has
										<span class="font-bold">{selectedProblem.variables.length}</span> variables:
									</p>
									<ul class="ml-2 flex flex-col gap-2">
										<li class="flex items-center gap-2">
											<span
												class="inline-block rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold text-blue-800"
											>
												{selectedProblem.variables.filter((v) => v.variable_type === 'integer')
													.length}
											</span>
											<span class="text-gray-700">integer</span>
										</li>
										<li class="flex items-center gap-2">
											<span
												class="inline-block rounded-full bg-green-100 px-3 py-1 text-xs font-semibold text-green-800"
											>
												{selectedProblem.variables.filter((v) => v.variable_type === 'binary')
													.length}
											</span>
											<span class="text-gray-700">binary</span>
										</li>
										<li class="flex items-center gap-2">
											<span
												class="inline-block rounded-full bg-purple-100 px-3 py-1 text-xs font-semibold text-purple-800"
											>
												{selectedProblem.variables.filter((v) => v.variable_type === 'real').length}
											</span>
											<span class="text-gray-700">real</span>
										</li>
									</ul>
									<p class="mb-2 text-sm text-gray-600 italic">
										Only a summary is shown because this problem has more than 10 variables.
									</p>
								</div>
							{:else}
								<p>No variable details available.</p>
							{/if}
						{:else}
							Select a problem to see details.
						{/if}
					</Tabs.Content>

					<!-- Constraints Tab -->
					<Tabs.Content value="constraints" class="w-full">
						{#if selectedProblem}
							{#if selectedProblem.constraints && Array.isArray(selectedProblem.constraints) && selectedProblem.constraints.length}
								<div class="my-4 rounded-lg border border-gray-200 bg-gray-50 p-4 shadow-sm">
									<Table.Root>
										<Table.Caption>
											List of constraints for {selectedProblem.name}.
										</Table.Caption>
										<Table.Header>
											<Table.Row>
												<Table.Head class="font-semibold">Name</Table.Head>
												<Table.Head class="font-semibold">Type</Table.Head>
												<Table.Head class="font-semibold">Convex</Table.Head>
												<Table.Head class="font-semibold">Linear</Table.Head>
												<Table.Head class="font-semibold">Twice Differentiable</Table.Head>
												<Table.Head class="font-semibold">Formulation</Table.Head>
											</Table.Row>
										</Table.Header>
										<Table.Body>
											{#each selectedProblem.constraints as constraint}
												<Table.Row>
													<Table.Cell class="text-justify"
														>{(constraint.symbol || constraint.name) ?? '—'}</Table.Cell
													>
													<Table.Cell class="text-justify">{constraint.cons_type ?? '—'}</Table.Cell
													>
													<Table.Cell class="text-justify"
														>{constraint.is_convex ? 'Yes' : 'No'}</Table.Cell
													>
													<Table.Cell class="text-justify"
														>{constraint.is_linear ? 'Yes' : 'No'}</Table.Cell
													>
													<Table.Cell class="text-justify"
														>{constraint.is_twice_differentiable ? 'Yes' : 'No'}</Table.Cell
													>
													<Table.Cell class="text-justify">
														<Dialog.Root>
															<Dialog.Trigger
																class={buttonVariants({ variant: 'outline' })}
																disabled={!constraint.func}
															>
																View Details
															</Dialog.Trigger>
															<Dialog.Content
																class="max-h-[80vh] w-full max-w-4xl overflow-x-auto overflow-y-auto"
															>
																<Dialog.Header>
																	<Dialog.Title>Constraint Formulation</Dialog.Title>
																	<Dialog.Description>
																		View the formulation of the {(constraint.symbol ||
																			constraint.name) ??
																			'—'} constraint below.
																	</Dialog.Description>
																</Dialog.Header>
																<div class="grid gap-4 py-4">
																	<div>
																		<MathExpressionRenderer func={constraint.func} />
																	</div>
																</div>
															</Dialog.Content>
														</Dialog.Root>
													</Table.Cell>
												</Table.Row>
											{/each}
										</Table.Body>
									</Table.Root>
								</div>
							{:else}
								<p>No constraint details available.</p>
							{/if}
						{:else}
							Select a problem to see details.
						{/if}
					</Tabs.Content>

					<!-- Extra Functions Tab -->
					<Tabs.Content value="extra" class="w-full">
						{#if selectedProblem}
							{#if selectedProblem.extra_funcs && Array.isArray(selectedProblem.extra_funcs) && selectedProblem.extra_funcs.length}
								<div class="my-4 rounded-lg border border-gray-200 bg-gray-50 p-4 shadow-sm">
									<Table.Root>
										<Table.Caption>
											List of extra functions for {selectedProblem.name}.
										</Table.Caption>
										<Table.Header>
											<Table.Row>
												<Table.Head class="font-semibold">Name</Table.Head>
												<Table.Head class="font-semibold">Formulation</Table.Head>
											</Table.Row>
										</Table.Header>
										<Table.Body>
											{#each selectedProblem.extra_funcs as obj}
												<Table.Row>
													<Table.Cell class="text-justify"
														>{(obj.symbol || obj.name) ?? '—'}</Table.Cell
													>
													<Table.Cell class="text-justify">
														<Dialog.Root>
															<Dialog.Trigger
																class={buttonVariants({ variant: 'outline' })}
																disabled={!obj.func}
															>
																View Details
															</Dialog.Trigger>
															<Dialog.Content
																class="max-h-[80vh] w-full max-w-4xl overflow-x-auto overflow-y-auto"
															>
																<Dialog.Header>
																	<Dialog.Title>Extra Function Formulation</Dialog.Title>
																	<Dialog.Description>
																		View the formulation of the {(obj.symbol || obj.name) ?? '—'} extra
																		function below.
																	</Dialog.Description>
																</Dialog.Header>
																<div class="grid gap-4 py-4">
																	<div>
																		<MathExpressionRenderer func={obj.func} />
																	</div>
																</div>
															</Dialog.Content>
														</Dialog.Root>
													</Table.Cell>
												</Table.Row>
											{/each}
										</Table.Body>
									</Table.Root>
								</div>
							{:else}
								<p>No extra function details available.</p>
							{/if}
						{:else}
							Select a problem to see details.
						{/if}
					</Tabs.Content>
				</Tabs.Root>
			</div>
		</div>
	{/if}
</div>
