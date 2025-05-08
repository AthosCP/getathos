<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import AdminNavbar from '$lib/AdminNavbar.svelte';

  type Tenant = { 
    id: string; 
    name: string; 
    description: string; 
    users_count: number;
    created_at: string;
    status: string;
  };

  type DashboardStats = {
    total_clients: number;
    total_users: number;
    active_clients: number;
    active_users: number;
    recent_clients: Tenant[];
  };

  let stats: DashboardStats = {
    total_clients: 0,
    total_users: 0,
    active_clients: 0,
    active_users: 0,
    recent_clients: []
  };
  let loading = true;
  let error = '';

  async function loadDashboardData() {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        goto('/login');
        return;
      }

      const response = await fetch('http://localhost:5001/api/admin/dashboard', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      const data = await response.json();
      if (data.success) {
        stats = data.data;
      } else {
        error = data.error || 'Error al cargar datos';
      }
    } catch (e) {
      error = 'Error de conexión';
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    const userRaw = localStorage.getItem('user');
    if (!userRaw) {
      goto('/login');
      return;
    }
    const user = JSON.parse(userRaw);
    if (user.role !== 'admin') {
      goto('/login');
      return;
    }
    loadDashboardData();
  });
</script>

<AdminNavbar active="dashboard" />

<div class="min-h-screen bg-gray-100">
  <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
    {#if loading}
      <div class="text-center">Cargando...</div>
    {:else if error}
      <div class="text-red-500 text-center">{error}</div>
    {:else}
      <!-- Métricas principales -->
      <div class="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <!-- Total Clientes -->
        <div class="bg-white overflow-hidden shadow rounded-lg">
          <div class="px-4 py-5 sm:p-6">
            <dt class="text-sm font-medium text-gray-500 truncate">
              Total Clientes
            </dt>
            <dd class="mt-1 text-3xl font-semibold text-gray-900">
              {stats.total_clients}
            </dd>
          </div>
        </div>

        <!-- Total Usuarios -->
        <div class="bg-white overflow-hidden shadow rounded-lg">
          <div class="px-4 py-5 sm:p-6">
            <dt class="text-sm font-medium text-gray-500 truncate">
              Total Usuarios
            </dt>
            <dd class="mt-1 text-3xl font-semibold text-gray-900">
              {stats.total_users}
            </dd>
          </div>
        </div>

        <!-- Clientes Activos -->
        <div class="bg-white overflow-hidden shadow rounded-lg">
          <div class="px-4 py-5 sm:p-6">
            <dt class="text-sm font-medium text-gray-500 truncate">
              Clientes Activos
            </dt>
            <dd class="mt-1 text-3xl font-semibold text-gray-900">
              {stats.active_clients}
            </dd>
          </div>
        </div>

        <!-- Usuarios Activos -->
        <div class="bg-white overflow-hidden shadow rounded-lg">
          <div class="px-4 py-5 sm:p-6">
            <dt class="text-sm font-medium text-gray-500 truncate">
              Usuarios Activos
            </dt>
            <dd class="mt-1 text-3xl font-semibold text-gray-900">
              {stats.active_users}
            </dd>
          </div>
        </div>
      </div>

      <!-- Clientes Recientes -->
      <div class="mt-8">
        <div class="bg-white shadow overflow-hidden sm:rounded-lg">
          <div class="px-4 py-5 sm:px-6">
            <h3 class="text-lg leading-6 font-medium text-gray-900">
              Clientes Recientes
            </h3>
            <p class="mt-1 max-w-2xl text-sm text-gray-500">
              Últimos clientes registrados en la plataforma
            </p>
          </div>
          <div class="border-t border-gray-200">
            <ul class="divide-y divide-gray-200">
              {#each stats.recent_clients as client}
                <li class="px-4 py-4">
                  <div class="flex items-center justify-between">
                    <div>
                      <p class="text-sm font-medium text-gray-900">{client.name}</p>
                      <p class="text-sm text-gray-500">{client.description}</p>
                    </div>
                    <div class="flex items-center space-x-4">
                      <div class="text-sm text-gray-500">
                        {client.users_count} usuarios
                      </div>
                      <div class="text-sm">
                        <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full {client.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}">
                          {client.status === 'active' ? 'Activo' : 'Pendiente'}
                        </span>
                      </div>
                    </div>
                  </div>
                </li>
              {/each}
            </ul>
          </div>
        </div>
      </div>
    {/if}
  </main>
</div> 