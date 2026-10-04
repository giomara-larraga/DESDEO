<script lang="ts">
	/**
	 * ShapHeatmap.svelte
	 * --------------------------------
	 * Renders a SHAP-values heatmap as a responsive SVG.
	 *
	 * Rows    = objective outcomes  (output symbols, e.g. "f1")
	 * Columns = reference-point aspirations (input symbols, e.g. "z_f1")
	 * Color   = blue for improving effects, red for impairing effects
	 * Text    = SHAP value formatted to 2 decimal places
	 */
	import type { ProblemInfo } from '$lib/types';

	interface Props {
		/** shap_values[output_symbol][input_symbol] = float */
		shapValues: Record<string, Record<string, number>>;
		problem: ProblemInfo;
	}

	let { shapValues, problem }: Props = $props();

	// ── Derived matrix dimensions ────────────────────────────────────────────
	const rowSymbols = $derived(Object.keys(shapValues));
	const colSymbols = $derived(rowSymbols.length > 0 ? Object.keys(shapValues[rowSymbols[0]]) : []);

	// symbol → display name
	const objNameMap = $derived(
		Object.fromEntries(problem.objectives.map((o) => [o.symbol, o.name ?? o.symbol]))
	);

	const rowLabels = $derived(rowSymbols.map((s) => objNameMap[s] ?? s));
	// input symbols are "z_<output_symbol>" – strip prefix then look up name
	const colLabels = $derived(
		colSymbols.map((s) => {
			const sym = s.startsWith('z_') ? s.slice(2) : s;
			return objNameMap[sym] ?? sym;
		})
	);

	// ── Color intensity scale ────────────────────────────────────────────────
	const allValues = $derived(rowSymbols.flatMap((r) => colSymbols.map((c) => shapValues[r][c])));
	//const absMax = $derived(Math.max(1e-9, ...allValues.map(Math.abs)));

	// ── SVG layout constants ─────────────────────────────────────────────────
	const CELL = 52;
	const LABEL_W = 88; // left margin for row labels
	const TOP_MARGIN = 42; // top margin for rotated column labels

	const svgWidth = $derived(LABEL_W + colSymbols.length * CELL);
	const svgHeight = $derived(TOP_MARGIN + rowSymbols.length * CELL + 8);

	// ── Helpers ───────────────────────────────────────────────────────────────
	function fmt(v: number): string {
		return v.toFixed(2);
	}

	function cellIsImproving(row: string, col: string): boolean {
		const maximize = objMaximizeMap[row] ?? false;
		const value = shapValues[row][col];
		return maximize ? value > 0 : value < 0;
	}

	function cellFill(row: string, col: string): string {
		const value = shapValues[row][col];
		const intensity = Math.min(1, Math.abs(value) / absMax);
		const channel = Math.round(245 - intensity * 110);
		return cellIsImproving(row, col)
			? `rgb(${channel}, ${channel + 5}, 255)`
			: `rgb(255, ${channel}, ${channel})`;
	}

	/** Use white text on strongly-coloured cells, dark text on pale ones */
	function textFill(row: string, col: string): string {
		const normalised = Math.abs(shapValues[row][col]) / absMax;
		return normalised > 0.55 ? 'white' : '#111827';
	}

	/** Truncate a label that is too long for a cell */
	function truncate(label: string, max = 10): string {
		return label.length > max ? label.slice(0, max - 1) + '…' : label;
	}

	// symbol → maximize flag
	const objMaximizeMap = $derived(
		Object.fromEntries(problem.objectives.map((o) => [o.symbol, o.maximize ?? false]))
	);

	/**
	 * For a given output symbol, return the aspiration to relax first:
	 * most impairing, or least improving if none are impairing.
	 */
	function relaxFirstCol(rowSym: string): string {
		const maximize = objMaximizeMap[rowSym] ?? false;
		const row = shapValues[rowSym];
		let best = colSymbols[0];
		for (const col of colSymbols) {
			if (maximize ? row[col] < row[best] : row[col] > row[best]) best = col;
		}
		return best;
	}

	/** True when the diagonal cell has the wrong sign (aspiration impairs its own objective) */
	function diagonalImpairs(rowSym: string): boolean {
		const diagCol = `z_${rowSym}`;
		if (!(diagCol in shapValues[rowSym])) return false;
		const maximize = objMaximizeMap[rowSym] ?? false;
		const v = shapValues[rowSym][diagCol];
		// impairs = aspiration pushes in the wrong direction
		// minimise → positive SHAP on diagonal is bad; maximise → negative is bad
		return maximize ? v < 0 : v > 0;
	}

	function contributionScore(row: string, col: string): number {
		const rawValue = Number(shapValues[row]?.[col] ?? 0);

		if (!Number.isFinite(rawValue)) {
			return 0;
		}

		const maximize = objMaximizeMap[normalizeSymbol(row)] ?? false;

		return maximize ? rawValue : -rawValue;
	}

	function normalizeSymbol(symbol: string): string {
		return symbol.startsWith('z_') ? symbol.slice(2) : symbol;
	}

	function contributionType(row: string, col: string): 'supportive' | 'limiting' | 'neutral' {
		const value = contributionScore(row, col);

		if (Math.abs(value) <= 1e-10) {
			return 'neutral';
		}

		return value > 0 ? 'supportive' : 'limiting';
	}

	const allContributionScores = $derived(
		rowSymbols.flatMap((row) => colSymbols.map((col) => contributionScore(row, col)))
	);

	const absMax = $derived(Math.max(1e-9, ...allContributionScores.map(Math.abs)));

	function cellColor(row: string, col: string): string {
		const type = contributionType(row, col);

		if (type === 'supportive') {
			return '#0C7BDC';
		}

		if (type === 'limiting') {
			return '#DC3220';
		}

		return '#9CA3AF';
	}

	function cellOpacity(row: string, col: string): number {
		const value = contributionScore(row, col);

		if (Math.abs(value) <= 1e-10) {
			return 0.16;
		}

		const normalized = Math.abs(value) / absMax;

		return 0.15 + normalized * 0.85;
	}
	// SVG coordinates computed here so they can be used in templates without {@const}
	const axisX = 7;
	const axisY = $derived(TOP_MARGIN + (rowSymbols.length * CELL) / 2);
</script>

<div class="w-full">
	<div class="mb-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-gray-500">
		<span class="inline-flex items-center gap-1.5">
			<span class="h-2.5 w-2.5 rounded-sm bg-[#0C7BDC]"></span>
			Supportive
		</span>

		<span class="inline-flex items-center gap-1.5">
			<span class="h-2.5 w-2.5 rounded-sm bg-[#DC3220]"></span>
			Limiting
		</span>

		<span>Darker = larger contribution</span>
	</div>

	<svg
		viewBox={`0 0 ${svgWidth} ${svgHeight}`}
		preserveAspectRatio="xMidYMin meet"
		class="block h-auto w-full"
		aria-label="SHAP values heatmap"
	>
		<!-- ── Column headers (rotated -45°) ──────────────────────────────── -->
		{#each colSymbols as col, ci}
			{@const cx = LABEL_W + ci * CELL + CELL / 2}

			<text
				x={cx}
				y={TOP_MARGIN - 10}
				text-anchor="middle"
				dominant-baseline="middle"
				font-size="10"
				fill="#374151"
			>
				<title>{colLabels[ci]}</title>
				{truncate(colLabels[ci], 11)}
			</text>
		{/each}

		<!-- ── Column axis title ──────────────────────────────────────────── -->
		<text
			x={LABEL_W + (colSymbols.length * CELL) / 2}
			y={9}
			text-anchor="middle"
			dominant-baseline="middle"
			font-size="9"
			fill="#6B7280"
			font-weight="500"
		>
			Desired values
		</text>

		<!-- ── Rows ──────────────────────────────────────────────────────── -->
		{#each rowSymbols as row, ri}
			{@const cy = TOP_MARGIN + ri * CELL + CELL / 2}
			{@const best = relaxFirstCol(row)}
			{@const impairs = diagonalImpairs(row)}

			<!-- Row label – amber if diagonal impairs -->
			<text
				x={LABEL_W - 6}
				y={cy}
				text-anchor="end"
				dominant-baseline="middle"
				font-size="10"
				fill={'#374151'}
				font-weight={'normal'}
			>
				<title
					>{rowLabels[ri]}{impairs
						? ' ⚠ this aspiration is making the outcome harder to improve'
						: ''}</title
				>
				{truncate(rowLabels[ri], 11)}
			</text>

			<!-- Cells -->
			{#each colSymbols as col, ci}
				{@const rx = LABEL_W + ci * CELL}
				{@const ry = TOP_MARGIN + ri * CELL}
				{@const isDiag = false}
				{@const isBest = col === best}

				<rect
					x={rx}
					y={ry}
					width={CELL}
					height={CELL}
					fill={cellColor(row, col)}
					fill-opacity={cellOpacity(row, col)}
					stroke="white"
					stroke-width="2"
					rx="3"
				/>

				{@const value = contributionScore(row, col)}

				<text
					x={rx + CELL / 2}
					y={ry + CELL / 2}
					text-anchor="middle"
					dominant-baseline="middle"
					font-size="10"
					fill={textFill(row, col)}
					pointer-events="none"
				>
					{value > 0 ? '+' : ''}{value.toFixed(2)}
				</text>

				<!-- Best-lever star -->
				<!-- 				{#if isBest && !isDiag}
					<text
						x={rx + CELL - 5}
						y={ry + 10}
						font-size="9"
						fill={textFill(row, col)}
						text-anchor="middle"
						pointer-events="none"
					>★</text>
				{/if} -->

				<!-- Diagonal corner triangle (small top-left notch) -->
				{#if isDiag}
					<polygon
						points="{rx + 2},{ry + 2} {rx + 14},{ry + 2} {rx + 2},{ry + 14}"
						fill={impairs ? '#f59e0b' : '#111827'}
						opacity="0.85"
						pointer-events="none"
					/>
				{/if}
			{/each}
		{/each}

		<!-- ── Row axis title (rotated) ──────────────────────────────────── -->
		<text
			x={14}
			y={axisY}
			transform={`rotate(-90,14,${axisY})`}
			text-anchor="middle"
			dominant-baseline="middle"
			font-size="9"
			fill="#6B7280"
			font-weight="500"
		>
			Achieved values
		</text>
	</svg>
</div>
