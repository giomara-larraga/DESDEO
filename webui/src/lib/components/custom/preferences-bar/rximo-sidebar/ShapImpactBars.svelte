<script lang="ts">
  export let drivers: { name: string; value: number; own?: boolean }[] = [];

  $: maxAbs = Math.max(...drivers.map((d) => Math.abs(d.value)), 0.0001);
</script>

<div class="bars">
  {#each drivers.slice(0, 5) as driver}
    <div class="row">
      <div class="label">
        {driver.name}
        {#if driver.own}
          <span>(own)</span>
        {/if}
      </div>

      <div class="track">
        <div class="zero"></div>

        {#if driver.value < 0}
          <div
            class="bar negative"
            style={`right: 50%; width: ${(Math.abs(driver.value) / maxAbs) * 50}%;`}
          ></div>
        {:else}
          <div
            class="bar positive"
            style={`left: 50%; width: ${(Math.abs(driver.value) / maxAbs) * 50}%;`}
          ></div>
        {/if}
      </div>

      <strong class:positive={driver.value > 0} class:negative={driver.value < 0}>
        {driver.value >= 0 ? '+' : ''}{driver.value.toFixed(2)}
      </strong>
    </div>
  {/each}

  <div class="axis">
    <span>Hurts</span>
    <span>Helps</span>
  </div>
</div>

<style>
  .bars {
    display: flex;
    flex-direction: column;
    gap: 0.45rem;
  }

  .row {
    display: grid;
    grid-template-columns: 5.8rem 1fr 3rem;
    gap: 0.45rem;
    align-items: center;
    font-size: 0.75rem;
  }

  .label {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .label span {
    color: #64748b;
  }

  .track {
    position: relative;
    height: 0.8rem;
    background: #edf2f7;
    border-radius: 999px;
    overflow: hidden;
  }

  .zero {
    position: absolute;
    left: 50%;
    top: 0;
    bottom: 0;
    width: 1px;
    background: #64748b;
    opacity: 0.5;
  }

  .bar {
    position: absolute;
    top: 0;
    bottom: 0;
  }

  .positive {
    color: #059669;
  }

  .negative {
    color: #dc2626;
  }

  .bar.positive {
    background: #22c55e;
  }

  .bar.negative {
    background: #ef4444;
  }

  .axis {
    display: flex;
    justify-content: space-between;
    color: #64748b;
    font-size: 0.7rem;
    padding-left: 5.8rem;
    padding-right: 3rem;
  }
</style>