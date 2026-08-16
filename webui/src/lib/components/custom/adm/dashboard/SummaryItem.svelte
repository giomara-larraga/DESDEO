<script lang="ts">
  
    export let label: string;
    export let value: string;
  
</script>


<div class="summary-item">
    <small>{label}</small>
    <strong>{value}</strong>
</div>

<style>
    :global(.summary-item) {
    padding: 0.55rem 0.7rem;
    border-right: 1px solid #eceef4;
    min-width: 0;
  }

  :global(.summary-item:last-child) {
    border-right: 0;
  }

  :global(.summary-item small) {
    display: block;
    color: #9097a8;
    font-size: 0.61rem;
    margin-bottom: 0.1rem;
  }

  :global(.summary-item strong) {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: #242b3b;
    font-size: 0.68rem;
  }
</style>