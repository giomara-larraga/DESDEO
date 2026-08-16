<div class="legend">
  <span><i class="selected"></i> Selected vector</span>
  <span><i class="roi"></i> ROI / max assigned</span>
  <span><i class="size"></i> Size = assigned solutions</span>
</div>

<style>
  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    margin-bottom: 0.75rem;
    font-size: 0.8rem;
    color: #475569;
  }

  i {
    display: inline-block;
    width: 12px;
    height: 12px;
    border-radius: 999px;
    margin-right: 0.3rem;
    vertical-align: middle;
  }

  .selected {
    background: #7c3aed;
  }

  .roi {
    background: #ef4444;
  }

  .size {
    background: #22c55e;
  }
</style>