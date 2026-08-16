<script lang="ts">
  import { onMount } from "svelte";
  import * as d3 from "d3";

  import type { ADMLog } from "$lib/adm/types";
  import { getObjectives } from "$lib/adm/adapters";

  export let log: ADMLog;
  export let selectedIteration: number;

  export let onSelect: (iteration: number) => void = () => {};

  export let width = 620;
  export let height = 280;

  type PreferencePoint = {
    iteration: number;
    phase: "learning" | "decision";
    referencePoint: number[];
    selectedVector: string;
    selectionRule: string;
  };

  let svgEl: SVGSVGElement;

  let tooltipVisible = false;
  let tooltipX = 0;
  let tooltipY = 0;

  let tooltipData: PreferencePoint | null = null;

  $: objectives = getObjectives(log);

  $: preferences = log.iterations.map((iteration) => ({
    iteration: iteration.iteration,
    phase: iteration.phase,
    referencePoint:
      iteration.preference_information.reference_point,
    selectedVector:
      iteration.preference_information.selected_reference_vector,
    selectionRule:
      iteration.preference_information.selection_rule
  })) satisfies PreferencePoint[];

  function draw() {
    if (!svgEl) return;

    const svg = d3.select(svgEl);

    svg.selectAll("*").remove();

    const margin = {
      top: 28,
      right: 30,
      bottom: 24,
      left: 30
    };

    const innerWidth =
      width - margin.left - margin.right;

    const innerHeight =
      height - margin.top - margin.bottom;

    if (
      preferences.length === 0 ||
      objectives.length === 0
    ) {
      svg
        .attr("viewBox", `0 0 ${width} ${height}`)
        .append("text")
        .attr("x", width / 2)
        .attr("y", height / 2)
        .attr("text-anchor", "middle")
        .attr("fill", "#8a91a3")
        .attr("font-size", 12)
        .text("No ADM preference data available.");

      return;
    }

    /*
     * ----------------------------------------------------
     * X scale — one axis per objective
     * ----------------------------------------------------
     */

    const x = d3
      .scalePoint<number>()
      .domain(d3.range(objectives.length))
      .range([0, innerWidth]);

    /*
     * ----------------------------------------------------
     * Y scales — one scale per objective
     *
     * Use preference history to determine the range.
     * If you later want consistent scaling with the
     * solution plots, replace these domains with ideal/nadir.
     * ----------------------------------------------------
     */

    const yScales = objectives.map((_, objectiveIndex) => {
      const values = preferences.map(
        (d) => d.referencePoint[objectiveIndex]
      );

      let minValue = d3.min(values) ?? 0;
      let maxValue = d3.max(values) ?? 1;

      /*
       * Include zero because many ADM reference points
       * in your experiments contain zero components.
       */
      minValue = Math.min(0, minValue);

      if (minValue === maxValue) {
        maxValue = minValue + 1;
      }

      const padding =
        (maxValue - minValue) * 0.08;

      return d3
        .scaleLinear()
        .domain([
          Math.max(0, minValue - padding),
          maxValue + padding
        ])
        .nice()
        .range([innerHeight, 0]);
    });

    /*
     * ----------------------------------------------------
     * Colors
     * ----------------------------------------------------
     */

    const learningColor = "#7357df";
    const learningMuted = "#c9bff5";

    const decisionColor = "#e4772e";
    const decisionMuted = "#f3c39e";

    function lineColor(d: PreferencePoint) {
      const isSelected =
        d.iteration === selectedIteration;

      if (d.phase === "learning") {
        return isSelected
          ? learningColor
          : learningMuted;
      }

      return isSelected
        ? decisionColor
        : decisionMuted;
    }

    /*
     * ----------------------------------------------------
     * Root
     * ----------------------------------------------------
     */

    const root = svg
      .attr("viewBox", `0 0 ${width} ${height}`)
      .attr("preserveAspectRatio", "xMidYMid meet")
      .append("g")
      .attr(
        "transform",
        `translate(${margin.left},${margin.top})`
      );

    /*
     * ----------------------------------------------------
     * Axis background guides
     * ----------------------------------------------------
     */

    root
      .append("g")
      .selectAll("line")
      .data(objectives)
      .join("line")
      .attr(
        "x1",
        (_, index) => x(index) ?? 0
      )
      .attr(
        "x2",
        (_, index) => x(index) ?? 0
      )
      .attr("y1", 0)
      .attr("y2", innerHeight)
      .attr("stroke", "#d8dce6")
      .attr("stroke-width", 1);

    /*
     * ----------------------------------------------------
     * Line generator
     * ----------------------------------------------------
     */

    const line = d3
      .line<number>()
      .defined((d) => Number.isFinite(d))
      .x((_, index) => x(index) ?? 0)
      .y(
        (value, index) =>
          yScales[index](value)
      )
      .curve(d3.curveLinear);

    /*
     * Draw non-selected first
     * ----------------------------------------------------
     */

    const orderedPreferences = [
      ...preferences.filter(
        (d) => d.iteration !== selectedIteration
      ),
      ...preferences.filter(
        (d) => d.iteration === selectedIteration
      )
    ];

    const preferenceGroup = root
      .append("g")
      .attr("class", "preference-lines");

    const paths = preferenceGroup
      .selectAll("path")
      .data(orderedPreferences)
      .join("path")
      .attr(
        "d",
        (d) => line(d.referencePoint)
      )
      .attr("fill", "none")
      .attr(
        "stroke",
        (d) => lineColor(d)
      )
      .attr(
        "stroke-width",
        (d) =>
          d.iteration === selectedIteration
            ? 3
            : 1.4
      )
      .attr(
        "stroke-opacity",
        (d) =>
          d.iteration === selectedIteration
            ? 1
            : 0.55
      )
      .style("cursor", "pointer")
      .on(
        "mouseenter",
        function (event, d) {
          d3.select(this)
            .attr("stroke-width", 3)
            .attr("stroke-opacity", 1);

          tooltipData = d;

          const bounds =
            svgEl.getBoundingClientRect();

          tooltipX =
            event.clientX - bounds.left + 12;

          tooltipY =
            event.clientY - bounds.top + 10;

          tooltipVisible = true;
        }
      )
      .on(
        "mousemove",
        function (event) {
          const bounds =
            svgEl.getBoundingClientRect();

          tooltipX =
            event.clientX - bounds.left + 12;

          tooltipY =
            event.clientY - bounds.top + 10;
        }
      )
      .on(
        "mouseleave",
        function (_event, d) {
          d3.select(this)
            .attr(
              "stroke-width",
              d.iteration === selectedIteration
                ? 3
                : 1.4
            )
            .attr(
              "stroke-opacity",
              d.iteration === selectedIteration
                ? 1
                : 0.55
            );

          tooltipVisible = false;
        }
      )
      .on(
        "click",
        (_event, d) => {
          onSelect(d.iteration);
        }
      );

    /*
     * ----------------------------------------------------
     * Axis ticks
     * ----------------------------------------------------
     */

    const axisGroups = root
      .selectAll(".objective-axis")
      .data(
        objectives.map((objective, index) => ({
          objective,
          index
        }))
      )
      .join("g")
      .attr("class", "objective-axis")
      .attr(
        "transform",
        (d) =>
          `translate(${x(d.index)},0)`
      );

    axisGroups.each(function (d) {
      const axis = d3
        .axisLeft(
          yScales[d.index]
        )
        .ticks(4)
        .tickSize(3)
        .tickFormat((value) => {
          const number =
            Number(value);

          if (
            Math.abs(number) <
              0.01 &&
            number !== 0
          ) {
            return d3.format(
              ".1e"
            )(number);
          }

          return d3.format(
            ".2f"
          )(number);
        });

      d3.select(this)
        .call(axis);
    });

    axisGroups
      .select(".domain")
      .attr("stroke", "#aeb4c1");

    axisGroups
      .selectAll(".tick line")
      .attr("stroke", "#bfc4cf");

    axisGroups
      .selectAll(".tick text")
      .attr("fill", "#8991a2")
      .attr("font-size", 8);

    /*
     * Axis labels
     */

    axisGroups
      .append("text")
      .attr("y", -13)
      .attr("text-anchor", "middle")
      .attr("fill", "#272d3b")
      .attr("font-size", 11)
      .attr("font-weight", 700)
      .text((d) => d.objective);

    /*
     * ----------------------------------------------------
     * Selected interaction markers
     * ----------------------------------------------------
     */

    const selected =
      preferences.find(
        (d) =>
          d.iteration === selectedIteration
      );

    if (selected) {
      root
        .append("g")
        .selectAll("circle")
        .data(
          selected.referencePoint.map(
            (value, index) => ({
              value,
              index
            })
          )
        )
        .join("circle")
        .attr(
          "cx",
          (d) => x(d.index) ?? 0
        )
        .attr(
          "cy",
          (d) =>
            yScales[d.index](d.value)
        )
        .attr("r", 4)
        .attr(
          "fill",
          selected.phase === "learning"
            ? learningColor
            : decisionColor
        )
        .attr("stroke", "white")
        .attr("stroke-width", 1.5);
    }
  }

  onMount(() => {
    draw();
  });

  $: if (
    svgEl &&
    selectedIteration &&
    preferences.length
  ) {
    draw();
  }
</script>


<div class="preference-trajectory">

  <div class="chart-wrapper">

    <svg bind:this={svgEl}></svg>

    {#if
      tooltipVisible &&
      tooltipData
    }

      <div
        class="tooltip"
        style:left={`${tooltipX}px`}
        style:top={`${tooltipY}px`}
      >

        <div class="tooltip-header">

          <strong>
            Interaction
            {tooltipData.iteration}
          </strong>

          <span
            class:learning={
              tooltipData.phase ===
              "learning"
            }
            class:decision={
              tooltipData.phase ===
              "decision"
            }
            class="phase"
          >
            {tooltipData.phase}
          </span>

        </div>

        <div class="tooltip-meta">
          <span>
            ADM vector
          </span>

          <b>
            {tooltipData.selectedVector}
          </b>
        </div>

        <div class="tooltip-values">

          {#each tooltipData.referencePoint as value, index}

            <div>

              <span>
                {objectives[index]}
              </span>

              <strong>
                {value.toFixed(4)}
              </strong>

            </div>

          {/each}

        </div>

        <div class="tooltip-rule">
          {
            tooltipData.selectionRule
          }
        </div>

      </div>

    {/if}

  </div>


  <div class="footer">

    <div class="legend">

      <span>
        <i class="learning-line"></i>
        Learning
      </span>

      <span>
        <i class="decision-line"></i>
        Decision
      </span>

      <span>
        <i class="selected-point"></i>
        Selected interaction
      </span>

    </div>

    <span class="hint">
      Hover to inspect · click to select
    </span>

  </div>

</div>


<style>
  .preference-trajectory {
    width: 100%;
    min-width: 0;
  }

  .chart-wrapper {
    position: relative;
    width: 100%;
  }

  svg {
    display: block;
    width: 100%;
    height: auto;
    overflow: visible;
  }

  /*
   * Tooltip
   */

  .tooltip {
    position: absolute;
    z-index: 20;

    min-width: 205px;
    max-width: 270px;

    padding:
      0.6rem
      0.7rem;

    pointer-events: none;

    border:
      1px solid
      #e1e4ec;

    border-radius:
      8px;

    background:
      rgba(
        255,
        255,
        255,
        0.98
      );

    box-shadow:
      0 8px 28px
      rgb(15 23 42 / 0.13);
  }

  .tooltip-header {
    display: flex;
    align-items: center;
    justify-content: space-between;

    gap: 0.6rem;

    margin-bottom:
      0.5rem;
  }

  .tooltip-header strong {
    color: #2b3140;

    font-size: 0.69rem;
  }

  .phase {
    padding:
      0.16rem
      0.34rem;

    border-radius:
      4px;

    font-size:
      0.53rem;

    font-weight:
      700;

    text-transform:
      capitalize;
  }

  .phase.learning {
    color: #6042d1;
    background: #eee9ff;
  }

  .phase.decision {
    color: #d76d26;
    background: #fff0e5;
  }

  .tooltip-meta {
    display: flex;
    justify-content: space-between;

    margin-bottom:
      0.4rem;

    color: #7d8495;

    font-size:
      0.61rem;
  }

  .tooltip-meta b {
    color: #5f43d8;
  }

  .tooltip-values {
    display: grid;

    grid-template-columns:
      repeat(
        auto-fit,
        minmax(58px, 1fr)
      );

    gap: 0.25rem;
  }

  .tooltip-values div {
    padding:
      0.3rem
      0.35rem;

    border-radius:
      4px;

    background:
      #f7f8fb;

    text-align:
      center;
  }

  .tooltip-values span {
    display: block;

    color: #959cab;

    font-size:
      0.52rem;
  }

  .tooltip-values strong {
    color: #333949;

    font-size:
      0.59rem;

    font-variant-numeric:
      tabular-nums;
  }

  .tooltip-rule {
    margin-top:
      0.5rem;

    padding-top:
      0.4rem;

    border-top:
      1px solid
      #edf0f5;

    color: #8b92a3;

    font-size:
      0.56rem;

    overflow-wrap:
      anywhere;
  }

  /*
   * Footer
   */

  .footer {
    display: flex;
    align-items: center;
    justify-content: space-between;

    gap: 0.75rem;

    margin-top:
      0.25rem;
  }

  .legend {
    display: flex;
    flex-wrap: wrap;

    gap: 0.8rem;
  }

  .legend span {
    display: flex;
    align-items: center;

    gap: 0.3rem;

    color: #747c8e;

    font-size:
      0.61rem;
  }

  .legend i {
    display: inline-block;
  }

  .learning-line,
  .decision-line {
    width: 17px;
    height: 2px;

    border-radius:
      2px;
  }

  .learning-line {
    background: #7357df;
  }

  .decision-line {
    background: #e4772e;
  }

  .selected-point {
    width: 7px;
    height: 7px;

    border-radius:
      50%;

    background: #6546e8;

    box-shadow:
      0 0 0 2px white,
      0 0 0 3px #6546e8;
  }

  .hint {
    color: #9aa1b0;

    font-size:
      0.57rem;

    white-space:
      nowrap;
  }

  @media (
    max-width: 620px
  ) {

    .footer {
      align-items: flex-start;
      flex-direction: column;
    }

  }
</style>