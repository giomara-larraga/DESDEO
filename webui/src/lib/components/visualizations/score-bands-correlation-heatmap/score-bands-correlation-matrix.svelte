<script lang="ts">
	let {
		dimensions,
		matrix,
		descriptiveNames = {}
	}: {
		dimensions: string[];
		matrix: (number | null)[][] | null;
		descriptiveNames?: Record<string, string>;
	} = $props();

	function cellColor(value: number | null): string {
		if (value === null || !Number.isFinite(value)) {
			return '#e5e7eb';
		}

		const opacity = 0.12 + 0.7 * Math.abs(value);

		return value >= 0 ? `rgba(37, 99, 235, ${opacity})` : `rgba(220, 38, 38, ${opacity})`;
	}

	function textColor(value: number | null): string {
		return value !== null && Math.abs(value) > 0.65 ? '#ffffff' : '#111827';
	}
</script>

{#if matrix && dimensions.length > 0}
	<div class="w-full overflow-x-auto">
		<table class="border-separate border-spacing-1 text-xs">
			<thead>
				<tr>
					<th></th>

					{#each dimensions as name}
						<th class="min-w-14 px-2 py-1 text-center">
							{descriptiveNames[name] ?? name}
						</th>
					{/each}
				</tr>
			</thead>

			<tbody>
				{#each matrix as row, i}
					<tr>
						<th class="pr-2 text-left font-medium whitespace-nowrap">
							{descriptiveNames[dimensions[i]] ?? dimensions[i]}
						</th>

						{#each row as value, j}
							<td
								class="h-12 min-w-14 rounded text-center font-medium"
								style={`
									background-color: ${cellColor(value)};
									color: ${textColor(value)};
								`}
								title={`${descriptiveNames[dimensions[i]] ?? dimensions[i]} vs ${descriptiveNames[dimensions[j]] ?? dimensions[j]}`}
							>
								{value === null || !Number.isFinite(value) ? 'N/A' : value.toFixed(2)}
							</td>
						{/each}
					</tr>
				{/each}
			</tbody>
		</table>
	</div>

	<div class="mt-3 flex items-center justify-center gap-4 text-xs">
		<div class="flex items-center gap-1">
			<span class="h-3 w-3 rounded bg-red-600"></span>
			<span>Negative correlation</span>
		</div>

		<div class="flex items-center gap-1">
			<span class="h-3 w-3 rounded bg-blue-600"></span>
			<span>Positive correlation</span>
		</div>
	</div>
{:else}
	<p class="text-muted-foreground text-sm">
		Correlation data are not available for this iteration.
	</p>
{/if}
