<script lang="ts">
	import { Topbar } from '$lib/components/ui/topbar';
	import ParallelCoordinates from '$lib/components/visualizations/parallel-coordinates/parallel-coordinates.svelte';
	import ExpRankingBarchart from '$lib/components/visualizations/barchart/exp-ranking-barchart.svelte';
	import { Combobox } from '$lib/components/ui/combobox';
	import * as Tabs from '$lib/components/ui/tabs/index.js';

	type ObjectiveValues = Record<string, number>;
	type TradeoffMatrix = Record<string, Record<string, number>>;
	type PhaseData = {
		solver_results?: unknown;
		solution_result_index?: number;
		tradeoffs_matrix?: unknown;
		preferences?: unknown;
		current_objectives?: unknown;
		num_desired?: number;
	};

	type MethodAction = {
		state_id: number | null;
		problem_id: number | null;
		date_time: string | null;
		phase: string | null;
		kind: string | null;
		phase_data?: PhaseData;
	};

	type MethodSummary = {
		method: string;
		total_actions: number;
		problem_ids: number[];
		phase_counts: Record<string, number>;
		first_action_at: string | null;
		last_action_at: string | null;
		duration_seconds: number | null;
		actions: MethodAction[];
	};

	type UserSummary = {
		user_id: number;
		username: string;
		preferred_method: string;
		problem_objective_names?: Record<string, Record<string, string>>;
		problem_count: number;
		total_actions: number;
		first_action_at: string | null;
		last_action_at: string | null;
		duration_seconds: number | null;
		methods: Record<string, MethodSummary>;
	};

	type GroupSummary = {
		experiment_group: number | null;
		group_label: string;
		user_count: number;
		preferred_method_counts: Record<string, number>;
		average_duration_seconds: number | null;
		users: UserSummary[];
	};

	type AnalystPageData = {
		user: {
			username: string;
			role: string;
		};
		groups: GroupSummary[];
	};

	const METHOD_ORDER = ['nimbus', 'xnimbus'];

	let { data }: { data: AnalystPageData } = $props();
	const groups = $derived(data.groups ?? []);

	function getGroupKey(group: GroupSummary): string {
		return group.experiment_group === null ? 'unassigned' : String(group.experiment_group);
	}

	function formatDuration(seconds: number | null | undefined): string {
		if (seconds === null || seconds === undefined) {
			return 'No timing data';
		}

		const rounded = Math.round(seconds);
		const hours = Math.floor(rounded / 3600);
		const minutes = Math.floor((rounded % 3600) / 60);
		const remainingSeconds = rounded % 60;

		if (hours > 0) {
			return `${hours}h ${minutes}m ${remainingSeconds}s`;
		}

		if (minutes > 0) {
			return `${minutes}m ${remainingSeconds}s`;
		}

		return `${remainingSeconds}s`;
	}

	function formatDateTime(value: string | null | undefined): string {
		if (!value) {
			return 'No timestamp';
		}

		const parsed = new Date(value);
		if (Number.isNaN(parsed.getTime())) {
			return value;
		}

		return parsed.toLocaleString();
	}

	function formatPreferredMethod(method: string): string {
		if (method === 'xnimbus') {
			return 'XNIMBUS';
		}

		if (method === 'nimbus') {
			return 'NIMBUS';
		}

		if (method === 'unspecified') {
			return 'Unspecified';
		}

		return method;
	}

	function formatPreferredCounts(counts: Record<string, number>): string {
		const entries = Object.entries(counts);
		if (entries.length === 0) {
			return 'No preferences recorded';
		}

		return entries
			.map(([method, count]) => `${formatPreferredMethod(method)}: ${count}`)
			.join(' | ');
	}

	function getMethodSummaries(user: UserSummary | null): MethodSummary[] {
		if (!user) {
			return [];
		}

		const seen = new Set<string>();
		const orderedMethods = [...METHOD_ORDER, ...Object.keys(user.methods)].filter((method) => {
			if (seen.has(method)) {
				return false;
			}

			seen.add(method);
			return true;
		});

		return orderedMethods
			.map((method) => user.methods[method])
			.filter((summary): summary is MethodSummary => Boolean(summary));
	}

	function getObjectiveLabel(symbol: string, problemId?: number | null): string {
		const trimmed = symbol.trim();
		const fromProblemProperties =
			problemId !== null && problemId !== undefined
				? selectedUser?.problem_objective_names?.[String(problemId)]?.[trimmed]
				: undefined;

		if (fromProblemProperties) {
			return fromProblemProperties;
		}

		const objectiveMatch = /^f[_\s-]?(\d+)$/i.exec(trimmed);

		if (objectiveMatch) {
			return `Objective ${objectiveMatch[1]}`;
		}

		return trimmed
			.replace(/[_-]+/g, ' ')
			.replace(/\s+/g, ' ')
			.replace(/\b\w/g, (char) => char.toUpperCase());
	}

	function isRecord(value: unknown): value is Record<string, unknown> {
		return typeof value === 'object' && value !== null && !Array.isArray(value);
	}

	function asObjectiveValues(value: unknown): ObjectiveValues | null {
		if (!isRecord(value)) {
			return null;
		}

		const output: ObjectiveValues = {};
		for (const [key, raw] of Object.entries(value)) {
			if (typeof raw === 'number' && Number.isFinite(raw)) {
				output[key] = raw;
			}
		}

		return Object.keys(output).length > 0 ? output : null;
	}

	function getActionCandidates(action: MethodAction): ObjectiveValues[] {
		const phaseData = action.phase_data ?? {};
		const solverResults = phaseData.solver_results;

		if (Array.isArray(solverResults)) {
			return solverResults
				.map((item) => {
					if (!isRecord(item)) {
						return null;
					}

					return asObjectiveValues(item.optimal_objectives);
				})
				.filter((item): item is ObjectiveValues => item !== null);
		}

		if (isRecord(solverResults)) {
			const single = asObjectiveValues(solverResults.optimal_objectives);
			return single ? [single] : [];
		}

		return [];
	}

	function getObjectiveSymbols(candidates: ObjectiveValues[]): string[] {
		const symbols = new Set<string>();
		for (const candidate of candidates) {
			for (const key of Object.keys(candidate)) {
				symbols.add(key);
			}
		}
		return Array.from(symbols);
	}

	function getParallelDimensions(candidates: ObjectiveValues[], problemId?: number | null) {
		const symbols = getObjectiveSymbols(candidates);
		return symbols.map((symbol) => {
			const values = candidates
				.map((candidate) => candidate[symbol])
				.filter((value): value is number => typeof value === 'number' && Number.isFinite(value));
			const min = values.length > 0 ? Math.min(...values) : undefined;
			const max = values.length > 0 ? Math.max(...values) : undefined;

			return {
				symbol,
				name: getObjectiveLabel(symbol, problemId),
				min,
				max,
				direction: 'min' as const
			};
		});
	}

	function getSelectedCandidateIndex(action: MethodAction, candidateCount: number): number | null {
		if (candidateCount === 0) {
			return null;
		}

		const index = action.phase_data?.solution_result_index;
		if (typeof index === 'number' && index >= 0 && index < candidateCount) {
			return index;
		}

		return 0;
	}

	function getSelectedAction(methodSummary: MethodSummary): MethodAction | null {
		if (methodSummary.actions.length === 0) {
			return null;
		}

		const selectedStateId = selectedActionByMethod[methodSummary.method];
		if (selectedStateId === null || selectedStateId === undefined) {
			return methodSummary.actions[0];
		}

		return (
			methodSummary.actions.find((action) => action.state_id === selectedStateId) ??
			methodSummary.actions[0]
		);
	}

	function getTradeoffMatrixForAction(action: MethodAction): TradeoffMatrix | null {
		const tradeoffRaw = action.phase_data?.tradeoffs_matrix;
		const candidates = getActionCandidates(action);
		const selectedCandidate = getSelectedCandidateIndex(action, candidates.length) ?? 0;

		if (Array.isArray(tradeoffRaw)) {
			const entry = tradeoffRaw[selectedCandidate] ?? tradeoffRaw[0];
			return isRecord(entry) ? (entry as TradeoffMatrix) : null;
		}

		if (isRecord(tradeoffRaw)) {
			return tradeoffRaw as TradeoffMatrix;
		}

		return null;
	}

	function getTradeoffObjectiveOptions(matrix: TradeoffMatrix | null, problemId?: number | null) {
		if (!matrix) {
			return [];
		}

		return Object.keys(matrix).map((symbol) => ({
			label: getObjectiveLabel(symbol, problemId),
			value: symbol
		}));
	}

	function getTradeoffBars(
		matrix: TradeoffMatrix | null,
		objectiveSymbol: string | null,
		problemId?: number | null
	) {
		if (!matrix || !objectiveSymbol || !matrix[objectiveSymbol]) {
			return [];
		}

		return Object.entries(matrix[objectiveSymbol])
			.filter(([symbol]) => symbol !== objectiveSymbol)
			.sort(([, a], [, b]) => Math.abs(b) - Math.abs(a))
			.map(([symbol, value]) => ({
				name: getObjectiveLabel(symbol, problemId),
				symbol,
				value,
				direction: 'min' as const
			}));
	}

	function onActionRowClick(method: string, action: MethodAction) {
		selectedActionByMethod = {
			...selectedActionByMethod,
			[method]: action.state_id
		};

		const matrix = getTradeoffMatrixForAction(action);
		const firstObjective = matrix ? Object.keys(matrix)[0] : null;
		selectedObjectiveByMethod = {
			...selectedObjectiveByMethod,
			[method]: firstObjective
		};
		selectedTradeoffByMethod = {
			...selectedTradeoffByMethod,
			[method]: null
		};
	}

	function onObjectiveSelection(method: string, value: string) {
		selectedObjectiveByMethod = {
			...selectedObjectiveByMethod,
			[method]: value || null
		};
		selectedTradeoffByMethod = {
			...selectedTradeoffByMethod,
			[method]: null
		};
	}

	function onTradeoffSelection(method: string, value: string) {
		selectedTradeoffByMethod = {
			...selectedTradeoffByMethod,
			[method]: value || null
		};
	}

	function formatMetricMap(
		values: unknown,
		problemId?: number | null
	): Array<{ key: string; value: string }> {
		if (!isRecord(values)) {
			return [];
		}

		return Object.entries(values).map(([key, value]) => ({
			key: getObjectiveLabel(key, problemId),
			value:
				typeof value === 'number' && Number.isFinite(value)
					? value.toFixed(4)
					: String(value)
		}));
	}

	function areRecordValuesEqual<T extends string | number | null>(
		left: Record<string, T>,
		right: Record<string, T>
	): boolean {
		const leftKeys = Object.keys(left);
		const rightKeys = Object.keys(right);

		if (leftKeys.length !== rightKeys.length) {
			return false;
		}

		for (const key of leftKeys) {
			if (left[key] !== right[key]) {
				return false;
			}
		}

		return true;
	}

	let selectedGroupKey = $state<string | null>(null);
	let selectedUserId = $state<number | null>(null);
	let selectedMethodTab = $state<string | null>(null);
	let selectedActionByMethod = $state<Record<string, number | null>>({});
	let selectedObjectiveByMethod = $state<Record<string, string | null>>({});
	let selectedTradeoffByMethod = $state<Record<string, string | null>>({});

	const selectedGroup = $derived(
		groups.find((group) => getGroupKey(group) === selectedGroupKey) ?? null
	);
	const selectedUser = $derived(
		selectedGroup?.users.find((user) => user.user_id === selectedUserId) ??
			selectedGroup?.users[0] ??
			null
	);

	$effect(() => {
		if (groups.length > 0 && selectedGroupKey === null) {
			selectedGroupKey = getGroupKey(groups[0]);
		}

		if (!selectedGroup) {
			selectedUserId = null;
			return;
		}

		const stillSelected = selectedGroup.users.some((user) => user.user_id === selectedUserId);
		if (!stillSelected) {
			selectedUserId = selectedGroup.users[0]?.user_id ?? null;
		}
	});

	$effect(() => {
		const methodSummaries = getMethodSummaries(selectedUser);
		const nextSelectedActions: Record<string, number | null> = { ...selectedActionByMethod };
		const nextSelectedObjectives: Record<string, string | null> = { ...selectedObjectiveByMethod };
		let hasActionChanges = false;
		let hasObjectiveChanges = false;

		for (const methodSummary of methodSummaries) {
			if (methodSummary.actions.length === 0) {
				continue;
			}

			if (!(methodSummary.method in nextSelectedActions)) {
				nextSelectedActions[methodSummary.method] = methodSummary.actions[0].state_id;
				hasActionChanges = true;
			}

			const selectedStateId = nextSelectedActions[methodSummary.method];
			const selectedAction =
				methodSummary.actions.find((action) => action.state_id === selectedStateId) ??
				methodSummary.actions[0];
			if (!selectedAction) {
				continue;
			}

			if (!(methodSummary.method in nextSelectedObjectives)) {
				const matrix = getTradeoffMatrixForAction(selectedAction);
				nextSelectedObjectives[methodSummary.method] = matrix ? Object.keys(matrix)[0] : null;
				hasObjectiveChanges = true;
			}
		}

		if (
			hasActionChanges &&
			!areRecordValuesEqual(selectedActionByMethod, nextSelectedActions)
		) {
			selectedActionByMethod = nextSelectedActions;
		}

		if (
			hasObjectiveChanges &&
			!areRecordValuesEqual(selectedObjectiveByMethod, nextSelectedObjectives)
		) {
			selectedObjectiveByMethod = nextSelectedObjectives;
		}
	});

	$effect(() => {
		const methods = getMethodSummaries(selectedUser).map((summary) => summary.method);

		if (methods.length === 0) {
			if (selectedMethodTab !== null) {
				selectedMethodTab = null;
			}
			return;
		}

		if (!selectedMethodTab || !methods.includes(selectedMethodTab)) {
			selectedMethodTab = methods[0];
		}
	});
</script>

<div class="flex min-h-screen w-full flex-col">
	<Topbar />

	<main class="mx-auto flex w-full max-w-7xl flex-col gap-8 px-4 py-8">
		<section class="grid gap-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm lg:grid-cols-[1.5fr_1fr]">
			<div class="space-y-3">
				<p class="text-xs font-semibold uppercase tracking-[0.3em] text-slate-500">
					Analyst Workspace
				</p>
				<h1 class="text-3xl font-semibold text-slate-900">Experiment group results</h1>
				<p class="max-w-3xl text-sm leading-6 text-slate-600">
					Compare participation by experiment group, inspect preferred methods, and review
					the recorded action sequence for each participant across NIMBUS and XNIMBUS.
				</p>
			</div>
			<div class="rounded-xl border border-slate-200 bg-slate-50 p-4">
				<p class="text-sm font-medium text-slate-500">Signed in as</p>
				<p class="mt-1 text-lg font-semibold text-slate-900">{data.user.username}</p>
				<p class="text-sm text-slate-600">Role: {data.user.role}</p>
				<p class="mt-4 text-sm text-slate-600">Tracked groups: {groups.length}</p>
			</div>
		</section>

		{#if groups.length === 0}
			<section class="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center text-slate-600">
				No experiment results were found for any group.
			</section>
		{:else}
			<section class="space-y-4">
				<div class="flex items-center justify-between gap-4">
					<h2 class="text-xl font-semibold text-slate-900">Group overview</h2>
					<p class="text-sm text-slate-500">Select a group to inspect its users and actions.</p>
				</div>

				<div class="grid gap-4 lg:grid-cols-3">
					{#each groups as group}
						<button
							type="button"
							class={`rounded-2xl border p-5 text-left transition ${selectedGroupKey === getGroupKey(group) ? 'border-slate-900 bg-slate-900 text-white shadow-lg' : 'border-slate-200 bg-white text-slate-900 hover:border-slate-400 hover:shadow-sm'}`}
							onclick={() => {
								selectedGroupKey = getGroupKey(group);
							}}
						>
							<div class="flex items-start justify-between gap-3">
								<div>
									<p class={`text-xs font-semibold uppercase tracking-[0.25em] ${selectedGroupKey === getGroupKey(group) ? 'text-slate-300' : 'text-slate-500'}`}>
										{group.group_label}
									</p>
									<h3 class="mt-2 text-2xl font-semibold">{group.user_count}</h3>
									<p class={`text-sm ${selectedGroupKey === getGroupKey(group) ? 'text-slate-300' : 'text-slate-600'}`}>
										Users in this group
									</p>
								</div>
								<div class={`rounded-full px-3 py-1 text-xs font-medium ${selectedGroupKey === getGroupKey(group) ? 'bg-white/10 text-white' : 'bg-slate-100 text-slate-600'}`}>
									Avg time {formatDuration(group.average_duration_seconds)}
								</div>
							</div>

							<div class="mt-5 grid gap-3 sm:grid-cols-2">
								<div>
									<p class={`text-xs uppercase tracking-[0.25em] ${selectedGroupKey === getGroupKey(group) ? 'text-slate-300' : 'text-slate-500'}`}>
										Preferred methods
									</p>
									<p class={`mt-2 text-sm leading-6 ${selectedGroupKey === getGroupKey(group) ? 'text-slate-100' : 'text-slate-700'}`}>
										{formatPreferredCounts(group.preferred_method_counts)}
									</p>
								</div>
								<div>
									<p class={`text-xs uppercase tracking-[0.25em] ${selectedGroupKey === getGroupKey(group) ? 'text-slate-300' : 'text-slate-500'}`}>
										Selection
									</p>
									<p class={`mt-2 text-sm ${selectedGroupKey === getGroupKey(group) ? 'text-slate-100' : 'text-slate-700'}`}>
										Open user list and action summaries
									</p>
								</div>
							</div>
						</button>
					{/each}
				</div>
			</section>

			{#if selectedGroup}
				<section class="grid gap-6 lg:grid-cols-[320px_minmax(0,1fr)]">
					<div class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
						<div class="flex items-center justify-between gap-3">
							<div>
								<p class="text-xs font-semibold uppercase tracking-[0.25em] text-slate-500">
									{selectedGroup.group_label}
								</p>
								<h2 class="mt-2 text-xl font-semibold text-slate-900">Participants</h2>
							</div>
							<div class="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
								{selectedGroup.user_count} users
							</div>
						</div>

						<div class="mt-5 space-y-3">
							{#each selectedGroup.users as participant}
								<button
									type="button"
									class={`w-full rounded-xl border p-4 text-left transition ${selectedUserId === participant.user_id ? 'border-slate-900 bg-slate-900 text-white' : 'border-slate-200 bg-slate-50 text-slate-900 hover:border-slate-400 hover:bg-white'}`}
									onclick={() => {
										selectedUserId = participant.user_id;
									}}
								>
									<div class="flex items-start justify-between gap-3">
										<div>
											<p class="text-base font-semibold">{participant.username}</p>
											<p class={`mt-1 text-sm ${selectedUserId === participant.user_id ? 'text-slate-300' : 'text-slate-600'}`}>
												Preferred: {formatPreferredMethod(participant.preferred_method)}
											</p>
										</div>
										<div class={`rounded-full px-2 py-1 text-xs font-medium ${selectedUserId === participant.user_id ? 'bg-white/10 text-white' : 'bg-slate-200 text-slate-700'}`}>
											{participant.total_actions} actions
										</div>
									</div>
									<p class={`mt-3 text-xs uppercase tracking-[0.2em] ${selectedUserId === participant.user_id ? 'text-slate-300' : 'text-slate-500'}`}>
										Elapsed time
									</p>
									<p class={`mt-1 text-sm ${selectedUserId === participant.user_id ? 'text-slate-100' : 'text-slate-700'}`}>
										{formatDuration(participant.duration_seconds)}
									</p>
								</button>
							{/each}
						</div>
					</div>

					{#if selectedUser}
						<div class="space-y-6">
							<section class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
								<div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
									<div>
										<p class="text-xs font-semibold uppercase tracking-[0.25em] text-slate-500">
											User summary
										</p>
										<h2 class="mt-2 text-2xl font-semibold text-slate-900">
											{selectedUser.username}
										</h2>
										<p class="mt-2 text-sm text-slate-600">
											Preferred method: {formatPreferredMethod(selectedUser.preferred_method)}
										</p>
									</div>
									<div class="grid gap-3 sm:grid-cols-3">
										<div class="rounded-xl bg-slate-50 p-4">
											<p class="text-xs uppercase tracking-[0.2em] text-slate-500">Problems</p>
											<p class="mt-2 text-2xl font-semibold text-slate-900">
												{selectedUser.problem_count}
											</p>
										</div>
										<div class="rounded-xl bg-slate-50 p-4">
											<p class="text-xs uppercase tracking-[0.2em] text-slate-500">Actions</p>
											<p class="mt-2 text-2xl font-semibold text-slate-900">
												{selectedUser.total_actions}
											</p>
										</div>
										<div class="rounded-xl bg-slate-50 p-4">
											<p class="text-xs uppercase tracking-[0.2em] text-slate-500">Elapsed</p>
											<p class="mt-2 text-lg font-semibold text-slate-900">
												{formatDuration(selectedUser.duration_seconds)}
											</p>
										</div>
									</div>
								</div>

								<div class="mt-6 grid gap-4 sm:grid-cols-2">
									<div class="rounded-xl border border-slate-200 p-4">
										<p class="text-xs uppercase tracking-[0.2em] text-slate-500">First action</p>
										<p class="mt-2 text-sm text-slate-800">
											{formatDateTime(selectedUser.first_action_at)}
										</p>
									</div>
									<div class="rounded-xl border border-slate-200 p-4">
										<p class="text-xs uppercase tracking-[0.2em] text-slate-500">Last action</p>
										<p class="mt-2 text-sm text-slate-800">
											{formatDateTime(selectedUser.last_action_at)}
										</p>
									</div>
								</div>
							</section>

							<section class="space-y-4">
								<h3 class="text-xl font-semibold text-slate-900">Method actions</h3>
								{#if getMethodSummaries(selectedUser).length > 0}
									<Tabs.Root value={selectedMethodTab ?? getMethodSummaries(selectedUser)[0].method} class="space-y-4">
										<Tabs.List class="w-full">
											{#each getMethodSummaries(selectedUser) as methodSummary}
												<Tabs.Trigger value={methodSummary.method} onclick={() => (selectedMethodTab = methodSummary.method)}>
													{formatPreferredMethod(methodSummary.method)}
												</Tabs.Trigger>
											{/each}
										</Tabs.List>

										{#each getMethodSummaries(selectedUser) as methodSummary}
											<Tabs.Content value={methodSummary.method} class="space-y-0">
												<div class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
										<div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
											<div>
												<p class="text-xs font-semibold uppercase tracking-[0.25em] text-slate-500">
													{formatPreferredMethod(methodSummary.method)}
												</p>
												<h4 class="mt-2 text-xl font-semibold text-slate-900">
													{methodSummary.total_actions} recorded actions
												</h4>
											</div>
											<div class="rounded-full bg-slate-100 px-3 py-1 text-sm font-medium text-slate-700">
												{formatDuration(methodSummary.duration_seconds)}
											</div>
										</div>

										<div class="mt-5 grid gap-4 sm:grid-cols-3">
											<div class="rounded-xl bg-slate-50 p-4">
												<p class="text-xs uppercase tracking-[0.2em] text-slate-500">Problems touched</p>
												<p class="mt-2 text-sm text-slate-800">
													{methodSummary.problem_ids.length > 0 ? methodSummary.problem_ids.join(', ') : 'No problems'}
												</p>
											</div>
											<div class="rounded-xl bg-slate-50 p-4">
												<p class="text-xs uppercase tracking-[0.2em] text-slate-500">First action</p>
												<p class="mt-2 text-sm text-slate-800">
													{formatDateTime(methodSummary.first_action_at)}
												</p>
											</div>
											<div class="rounded-xl bg-slate-50 p-4">
												<p class="text-xs uppercase tracking-[0.2em] text-slate-500">Last action</p>
												<p class="mt-2 text-sm text-slate-800">
													{formatDateTime(methodSummary.last_action_at)}
												</p>
											</div>
										</div>

										<div class="mt-5">
											<p class="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
												Phase breakdown
											</p>
											<div class="mt-3 flex flex-wrap gap-2">
												{#if Object.keys(methodSummary.phase_counts).length > 0}
													{#each Object.entries(methodSummary.phase_counts) as [phase, count]}
														<span class="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">
															{phase}: {count}
														</span>
													{/each}
												{:else}
													<span class="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-500">
														No phases recorded
													</span>
												{/if}
											</div>
										</div>

										<div class="mt-5 overflow-x-auto rounded-xl border border-slate-200">
											<table class="min-w-full divide-y divide-slate-200 text-sm">
												<thead class="bg-slate-50 text-left text-slate-500">
													<tr>
														<th class="px-4 py-3 font-medium">State ID</th>
														<th class="px-4 py-3 font-medium">Problem</th>
														<th class="px-4 py-3 font-medium">Phase</th>
														<th class="px-4 py-3 font-medium">Kind</th>
														<th class="px-4 py-3 font-medium">Timestamp</th>
													</tr>
												</thead>
												<tbody class="divide-y divide-slate-200 bg-white text-slate-800">
													{#if methodSummary.actions.length > 0}
														{@const selectedAction = getSelectedAction(methodSummary)}
														{#each methodSummary.actions as action}
															<tr
																class={`cursor-pointer transition ${selectedAction && selectedAction.state_id === action.state_id ? 'bg-sky-50' : 'hover:bg-slate-50'}`}
																onclick={() => onActionRowClick(methodSummary.method, action)}
															>
																<td class="px-4 py-3">{action.state_id ?? '—'}</td>
																<td class="px-4 py-3">{action.problem_id ?? '—'}</td>
																<td class="px-4 py-3">{action.phase ?? '—'}</td>
																<td class="px-4 py-3">{action.kind ?? '—'}</td>
																<td class="px-4 py-3">{formatDateTime(action.date_time)}</td>
															</tr>
														{/each}
													{:else}
														<tr>
															<td colspan="5" class="px-4 py-6 text-center text-slate-500">
																No actions recorded for this method.
															</td>
														</tr>
													{/if}
												</tbody>
											</table>
										</div>

										{#if getSelectedAction(methodSummary)}
											{@const selectedAction = getSelectedAction(methodSummary)!}
											{@const candidates = getActionCandidates(selectedAction)}
											{@const selectedCandidateIndex = getSelectedCandidateIndex(selectedAction, candidates.length)}
											{@const dimensions = getParallelDimensions(candidates, selectedAction.problem_id)}
											{@const tradeoffMatrix = getTradeoffMatrixForAction(selectedAction)}
											{@const objectiveOptions = getTradeoffObjectiveOptions(tradeoffMatrix, selectedAction.problem_id)}
											{@const selectedObjectiveSymbol = selectedObjectiveByMethod[methodSummary.method] ?? (objectiveOptions.length > 0 ? objectiveOptions[0].value : null)}
											{@const selectedTradeoffSymbol = selectedTradeoffByMethod[methodSummary.method] ?? null}
											{@const tradeoffBars = getTradeoffBars(tradeoffMatrix, selectedObjectiveSymbol, selectedAction.problem_id)}

											<div class="mt-6 space-y-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
												<div class="flex items-center justify-between gap-3">
													<h5 class="text-sm font-semibold uppercase tracking-[0.2em] text-slate-700">
														Selected iteration details
													</h5>
													<p class="text-xs text-slate-600">
														State {selectedAction.state_id ?? '—'} | {selectedAction.phase ?? 'unknown'}
													</p>
												</div>

												<div class="grid gap-4 lg:grid-cols-2">
													<div class="rounded-lg border border-slate-200 bg-white p-3">
														<p class="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
															Preferences
														</p>
														<div class="mt-2 space-y-1 text-sm text-slate-700">
															{#if formatMetricMap(selectedAction.phase_data?.current_objectives, selectedAction.problem_id).length > 0}
																{#each formatMetricMap(selectedAction.phase_data?.current_objectives, selectedAction.problem_id) as metric}
																	<p>{metric.key}: {metric.value}</p>
																{/each}
															{:else}
																<p>No objective snapshot for this state.</p>
															{/if}
														</div>
													</div>

													<div class="rounded-lg border border-slate-200 bg-white p-3">
														<p class="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
															Iteration info
														</p>
														<p class="mt-2 text-sm text-slate-700">
															Desired solutions: {selectedAction.phase_data?.num_desired ?? '—'}
														</p>
														<p class="mt-1 text-sm text-slate-700">
															Selected solution index: {selectedCandidateIndex ?? '—'}
														</p>
														<p class="mt-1 text-sm text-slate-700">
															Candidates available: {candidates.length}
														</p>
													</div>
												</div>

												<div class="rounded-lg border border-slate-200 bg-white p-3">
													<p class="mb-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
														Iteration solutions (parallel coordinates)
													</p>
													{#if candidates.length > 0 && dimensions.length > 0}
														<div class="h-70">
															<ParallelCoordinates
																data={candidates}
																dimensions={dimensions}
																selectedIndex={selectedCandidateIndex}
																options={{
																	showAxisLabels: true,
																	highlightOnHover: true,
																	strokeWidth: 2,
																	opacity: 0.35,
																	enableBrushing: false
																}}
																lineLabels={Object.fromEntries(candidates.map((_, index) => [String(index), `Solution ${index + 1}`]))}
															/>
														</div>
													{:else}
														<p class="text-sm text-slate-600">No solver results were stored for this action.</p>
													{/if}
												</div>

												<div class="rounded-lg border border-slate-200 bg-white p-3">
													<p class="mb-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
														Tradeoffs ranking
													</p>
													{#if objectiveOptions.length > 0}
														<div class="mb-3">
															<Combobox
																placeholder="Select objective"
																options={objectiveOptions}
																defaultSelected={selectedObjectiveSymbol ?? objectiveOptions[0].value}
																onChange={(event) => onObjectiveSelection(methodSummary.method, event.value)}
															/>
														</div>
													{/if}

													{#if tradeoffBars.length > 0 && selectedObjectiveSymbol}
														<ExpRankingBarchart
															data={tradeoffBars}
															options={{ showLabels: false }}
															selected_objective_symbol={selectedObjectiveSymbol}
															selectedBarSymbol={selectedTradeoffSymbol}
															onSelect={(event) => onTradeoffSelection(methodSummary.method, event.value)}
														/>
													{:else}
														<p class="text-sm text-slate-600">No tradeoff matrix available for this action.</p>
													{/if}
												</div>
											</div>
										{/if}
												</div>
											</Tabs.Content>
										{/each}
									</Tabs.Root>
								{:else}
									<div class="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-6 text-center text-slate-600">
										No method actions are available for this user.
									</div>
								{/if}
							</section>
						</div>
					{:else}
						<section class="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center text-slate-600">
							This group has no users with recorded experiment actions.
						</section>
					{/if}
				</section>
			{/if}
		{/if}
	</main>
</div>
