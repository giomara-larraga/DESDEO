<script lang="ts">
	import ConfigPanel from './config-panel.svelte';
	import HistoryBrowser from './history-browser.svelte';

	type Phase = 'learning' | 'consensus';

	type RestartPhase =
	| 'learning'
	| 'consensus'
	| 'decision';

	type Props = {
		phase: Phase;
		isOwner: boolean;
		isDecisionMaker: boolean;

		problemName: string;
		learningTimeLabel?: string;

		clusterIds: number[];
		clusterColors: Record<number, string>;
		clusterVisibilityMap: Record<number, boolean>;
		onVisibilityChange: (
			clusterId: number,
			visible: boolean
		) => void;

		showBands: boolean;
		showMedians: boolean;
		canToggleBands: boolean;
		canToggleMedians: boolean;
		onShowBandsChange: (value: boolean) => void;
		onShowMediansChange: (value: boolean) => void;

		currentConfig: any;
		latestIteration: number | null;
		totalVoters: number;
		onRecalculate: (config: any) => void;

		history: any[];
		currentIterationId: number | null;
		onRevertToIteration: (iterationId: number) => void;

		onRestartToPhase:
			(
				phase: RestartPhase
			) => void | Promise<void>;

		canRestartToPhase:
			(
				phase: RestartPhase
			) => boolean;

		isRestarting?: boolean;
		};

	let {
		phase,
		isOwner,
		isDecisionMaker,
		problemName,
		learningTimeLabel = 'Not started',

		clusterIds,
		clusterColors,
		clusterVisibilityMap,
		onVisibilityChange,

		showBands,
		showMedians,
		canToggleBands,
		canToggleMedians,
		onShowBandsChange,
		onShowMediansChange,

		currentConfig,
		latestIteration,
		totalVoters,
		onRecalculate,

		history,
		currentIterationId,
		onRevertToIteration,
		onRestartToPhase,
		canRestartToPhase,
		isRestarting = false
	}: Props = $props();

	function checkboxValue(event: Event): boolean {
		return (event.currentTarget as HTMLInputElement).checked;
	}
</script>

<aside class="space-y-4">
	{#if phase === 'learning'}
		<section class="rounded-lg border bg-card shadow-sm">
			<header class="border-b px-4 py-3">
				<h2 class="text-sm font-semibold">
					How to explore
				</h2>
			</header>

			<div class="space-y-4 p-4 text-sm">
				<div
					class="
						rounded-md border border-blue-200
						bg-blue-50 px-3 py-2 text-blue-900
					"
				>
					<div class="text-xs font-medium">
						Time remaining
					</div>

					<div class="mt-1 text-sm">
						{learningTimeLabel}
					</div>
				</div>

				{#if isDecisionMaker}
					<div>
						<div class="font-medium">
							1. Explore bands
						</div>

						<p class="text-muted-foreground">
							Click a band to inspect it privately.
						</p>
					</div>

					<div>
						<div class="font-medium">
							2. Save preferences
						</div>

						<p class="text-muted-foreground">
							Bookmark interesting bands for yourself.
						</p>
					</div>

					<div>
						<div class="font-medium">
							3. Finish exploring
						</div>

						<p class="text-muted-foreground">
							Mark yourself finished when ready.
						</p>
					</div>
				{:else if isOwner}
					<p class="text-muted-foreground">
						Monitor the learning phase while decision
						makers explore the available bands.
					</p>
				{/if}
			</div>
		</section>
	{:else}
		<section class="rounded-lg border bg-card shadow-sm">
			<header class="border-b px-4 py-3">
				<h2 class="text-sm font-semibold">
					Data & Settings
				</h2>
			</header>

			<div class="space-y-4 p-4">
				<div>
					<div class="text-xs text-muted-foreground">
						Input data
					</div>

					<div class="mt-1 text-sm font-medium">
						{problemName}
					</div>
				</div>

				<div class="space-y-2">
					<div class="text-sm font-medium">
						Visualization options
					</div>

					<label class="flex items-center gap-2 text-sm">
						<input
							type="checkbox"
							checked={showBands}
							disabled={!canToggleBands}
							class="
								checkbox checkbox-primary
								checkbox-sm
							"
							onchange={(event) =>
								onShowBandsChange(
									checkboxValue(event)
								)}
						/>

						Show bands
					</label>

					<label class="flex items-center gap-2 text-sm">
						<input
							type="checkbox"
							checked={showMedians}
							disabled={!canToggleMedians}
							class="
								checkbox checkbox-primary
								checkbox-sm
							"
							onchange={(event) =>
								onShowMediansChange(
									checkboxValue(event)
								)}
						/>

						Show medians
					</label>
				</div>
			</div>
		</section>
	{/if}

	<section class="rounded-lg border bg-card shadow-sm">
		<header class="border-b px-4 py-3">
			<h2 class="text-sm font-semibold">
				Visible clusters
			</h2>
		</header>

		<div class="space-y-3 p-4">
			{#each clusterIds as clusterId}
				<label
					class="
						flex items-center justify-between
						gap-2 text-sm
					"
				>
					<span class="flex items-center gap-2">
						<span
							class="h-3 w-3 rounded-full"
							style:background-color={
								clusterColors[clusterId] ??
								'#64748b'
							}
						></span>

						Cluster {clusterId}
					</span>

					<input
						type="checkbox"
						checked={
							clusterVisibilityMap[
								clusterId
							] !== false
						}
						class="
							checkbox checkbox-primary
							checkbox-sm
						"
						onchange={(event) =>
							onVisibilityChange(
								clusterId,
								checkboxValue(event)
							)}
					/>
				</label>
			{/each}
		</div>
	</section>

	{#if phase === 'consensus' && isOwner}
		<ConfigPanel
			{currentConfig}
			{latestIteration}
			{totalVoters}
			onRecalculate={onRecalculate}
			isVisible={true}
		/>

	{/if}

	{#if isOwner}
		<HistoryBrowser
			{history}
			{currentIterationId}
			onRevertToIteration={onRevertToIteration}
			{isOwner}
			{onRestartToPhase}
			{canRestartToPhase}
			isRestartingPhase={isRestarting}
		/>
	{/if}

	{#if phase === 'consensus' && isDecisionMaker}
		<section class="rounded-lg border bg-card shadow-sm">
			<div class="p-4 text-sm text-muted-foreground">
				Select a visible band in the chart or table,
				then cast your vote from the voting panel.
			</div>
		</section>
	{/if}
</aside>