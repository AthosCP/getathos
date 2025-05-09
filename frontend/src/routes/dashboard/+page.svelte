<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import Navbar from '$lib/Navbar.svelte';
  import { API_URL } from '$lib/config';

  interface UserConfig {
    extension_enabled: boolean;
    blocked_domains: string[];
    allowed_domains: string[];
    user: {
      email: string;
      role: string;
    };
  }

  let userData: UserConfig | null = null;
  let loading = true;
  let error = '';

  async function loadUserData() {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        goto('/login');
        return;
      }

      const response = await fetch(`${API_URL}/api/config`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      const data = await response.json();
      if (data.success) {
        userData = data.data;
      } else {
        error = data.error || 'Error al cargar datos';
      }
    } catch (e) {
      error = 'Error de conexión';
    } finally {
      loading = false;
    }
  }

  function handleLogout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    goto('/login');
  }

  onMount(() => {
    const userRaw = localStorage.getItem('user');
    if (!userRaw) {
      goto('/login');
      return;
    }
    loadUserData();
  });
</script>

<Navbar active="dashboard" />

<div class="min-h-screen bg-gray-100">
  <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
    {#if loading}
      <div class="text-center">Cargando...</div>
    {:else if error}
      <div class="text-red-500 text-center">{error}</div>
    {:else}
      <div class="bg-white shadow overflow-hidden sm:rounded-lg">
        <div class="px-4 py-5 sm:px-6">
          <h3 class="text-lg leading-6 font-medium text-gray-900">
            Dashboard
          </h3>
          <p class="mt-1 max-w-2xl text-sm text-gray-500">
            Información de tu cuenta y configuración
          </p>
        </div>
        <div class="border-t border-gray-200">
          <dl>
            <div class="bg-gray-50 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
              <dt class="text-sm font-medium text-gray-500">
                Estado de la Extensión
              </dt>
              <dd class="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                {userData?.extension_enabled ? 'Activa' : 'Inactiva'}
              </dd>
            </div>
            <div class="bg-white px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
              <dt class="text-sm font-medium text-gray-500">
                Sitios Bloqueados
              </dt>
              <dd class="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                {userData?.blocked_domains?.length || 0} sitios
              </dd>
            </div>
            <div class="bg-gray-50 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
              <dt class="text-sm font-medium text-gray-500">
                Sitios Permitidos
              </dt>
              <dd class="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                {userData?.allowed_domains?.length || 0} sitios
              </dd>
            </div>
          </dl>
        </div>
      </div>
    {/if}
  </main>
</div> 