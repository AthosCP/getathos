<script lang="ts">
  import Navbar from '$lib/Navbar.svelte';
  import { onMount } from 'svelte';
  import { auth } from '$lib/auth';
  import { goto } from '$app/navigation';
  import { API_URL } from '$lib/config';

  let alerts: any[] = [];
  let loading = true;
  let error = '';

  onMount(async () => {
    if (!auth.token) {
      goto('/login');
      return;
    }
    await loadAlerts();
  });

  async function loadAlerts() {
    try {
      const response = await fetch(`${API_URL}/api/alerts`, {
        headers: {
          'Authorization': `Bearer ${auth.token}`
        }
      });
      const data = await response.json();
      if (data.success) {
        alerts = data.data;
      } else {
        error = data.error || 'Error al cargar las alertas';
      }
    } catch (e) {
      error = 'Error de conexión';
    } finally {
      loading = false;
    }
  }
</script>

<Navbar active="alerts" />

<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
  <div class="py-6">
    <h1 class="text-2xl font-semibold text-gray-900">Alertas</h1>
    
    {#if loading}
      <div class="mt-4 text-center text-gray-500">
        Cargando alertas...
      </div>
    {:else if error}
      <div class="mt-4 text-center text-red-500">
        {error}
      </div>
    {:else if alerts.length === 0}
      <div class="mt-4 text-center text-gray-500">
        No hay alertas para mostrar
      </div>
    {:else}
      <div class="mt-4 grid gap-4">
        {#each alerts as alert}
          <div class="bg-white shadow rounded-lg p-4">
            <div class="flex items-center justify-between">
              <div>
                <h3 class="text-lg font-medium text-gray-900">{alert.title}</h3>
                <p class="mt-1 text-sm text-gray-500">{alert.description}</p>
              </div>
              <div class="flex items-center">
                <span class="px-2 py-1 text-xs font-medium rounded-full {alert.severity === 'high' ? 'bg-red-100 text-red-800' : alert.severity === 'medium' ? 'bg-yellow-100 text-yellow-800' : 'bg-green-100 text-green-800'}">
                  {alert.severity}
                </span>
              </div>
            </div>
            <div class="mt-2 text-sm text-gray-500">
              {new Date(alert.created_at).toLocaleString()}
            </div>
          </div>
        {/each}
      </div>
    {/if}
  </div>
</div> 