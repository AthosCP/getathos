<script lang="ts">
  import { onMount } from 'svelte';
  import { API_URL } from '$lib/config';

  type Cliente = {
    id?: string;
    name: string;
    admin_id?: string;
    max_users?: number;
    role?: string;
  };

  type Admin = {
    id?: string;
    name: string;
    max_clients?: number;
    email: string;
  };

  let showCreateModal = false;
  let editingCliente: Cliente | null = null;
  let clientes: Cliente[] = [];
  let admins: Admin[] = [];
  let newCliente: Cliente = {
    name: '',
    max_users: 5
  };
  let error = '';
  let loading = false;
  let filtroNombre = '';
  let filtroAdmin = '';

  type FiltrosClientes = { name?: string; admin_id?: string };

  async function fetchClientes(filtros: FiltrosClientes = {}) {
    loading = true;
    try {
      const token = localStorage.getItem('token');
      const params = new URLSearchParams();
      if (filtros.name) params.append('name', filtros.name);
      if (filtros.admin_id) params.append('admin_id', filtros.admin_id);
      const url = `${API_URL}/api/athos/clientes${params.toString() ? '?' + params.toString() : ''}`;
      const res = await fetch(url, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      if (data.success) clientes = data.data;
      else error = data.error || 'Error al cargar clientes';
    } catch (e) {
      error = 'Error de conexión';
    } finally {
      loading = false;
    }
  }

  async function fetchAdmins() {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_URL}/api/athos/admins`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      if (data.success) admins = data.data;
    } catch (e) {}
  }

  onMount(async () => {
    await fetchClientes();
    await fetchAdmins();
  });

  function openCreateModal() {
    editingCliente = null;
    newCliente = { name: '', max_users: 5 };
    error = '';
    showCreateModal = true;
  }

  function openEditModal(cliente: Cliente) {
    editingCliente = cliente;
    newCliente = { ...cliente };
    error = '';
    showCreateModal = true;
  }

  function resetModal() {
    showCreateModal = false;
    editingCliente = null;
    newCliente = { name: '', max_users: 5 };
    error = '';
  }

  async function saveCliente() {
    error = '';
    const token = localStorage.getItem('token');
    try {
      let res, data;
      if (editingCliente) {
        res = await fetch(`${API_URL}/api/athos/clientes/${editingCliente.id}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify(newCliente)
        });
      } else {
        res = await fetch(`${API_URL}/api/athos/clientes`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify(newCliente)
        });
      }
      data = await res.json();
      if (data.success) {
        await fetchClientes();
        resetModal();
      } else {
        error = data.error || 'Error al guardar cliente';
      }
    } catch (e) {
      error = 'Error de conexión';
    }
  }

  async function deleteCliente(cliente: Cliente) {
    if (!confirm('¿Seguro que deseas eliminar este cliente?')) return;
    const token = localStorage.getItem('token');
    try {
      const res = await fetch(`${API_URL}/api/athos/clientes/${cliente.id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      if (data.success) await fetchClientes();
      else error = data.error || 'Error al eliminar cliente';
    } catch (e) {
      error = 'Error de conexión';
    }
  }

  function getAdminName(adminId: string | undefined) {
    if (!adminId) return '-';
    const admin = admins.find(a => a.id === adminId);
    return admin ? admin.email : '-';
  }

  function clientesFiltrados() {
    return clientes.filter(c =>
      (!filtroNombre || c.name.toLowerCase().includes(filtroNombre.toLowerCase())) &&
      (!filtroAdmin || c.admin_id === filtroAdmin)
    );
  }

  // Llamar a fetchClientes cada vez que cambian los filtros
  $: fetchClientes({
    name: filtroNombre,
    admin_id: filtroAdmin
  });
</script>

<div class="min-h-screen bg-gray-100">
  <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
    <div class="px-4 sm:px-0">
      <div class="flex justify-between items-center">
        <h1 class="text-2xl font-bold text-gray-900">Clientes</h1>
        <button
          on:click={openCreateModal}
          class="px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700"
        >
          Nuevo Cliente
        </button>
      </div>
      <div class="mt-4 flex flex-wrap gap-4 items-end">
        <div>
          <label class="block text-xs font-medium text-gray-700">Buscar por nombre</label>
          <input type="text" bind:value={filtroNombre} placeholder="Nombre" class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-1 px-2 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm" />
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-700">Administrador</label>
          <select bind:value={filtroAdmin} class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-1 px-2 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm">
            <option value="">Todos</option>
            {#each admins as admin}
              <option value={admin.id}>{admin.email}</option>
            {/each}
          </select>
        </div>
      </div>
    </div>

    {#if loading}
      <div class="text-center mt-8">Cargando...</div>
    {:else if error}
      <div class="text-red-500 text-center mt-8">{error}</div>
    {:else}
      <div class="mt-8 flex flex-col">
        <div class="-my-2 -mx-4 overflow-x-auto sm:-mx-6 lg:-mx-8">
          <div class="inline-block min-w-full py-2 align-middle md:px-6 lg:px-8">
            <div class="overflow-hidden shadow ring-1 ring-black ring-opacity-5 md:rounded-lg">
              <table class="min-w-full divide-y divide-gray-300">
                <thead class="bg-gray-50">
                  <tr>
                    <th scope="col" class="py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900 sm:pl-6">Nombre</th>
                    <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Rol</th>
                    <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Administrador</th>
                    <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Máx. usuarios</th>
                    <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Acciones</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-200 bg-white">
                  {#each clientes as cliente}
                    <tr>
                      <td class="whitespace-nowrap py-4 pl-4 pr-3 text-sm font-medium text-gray-900 sm:pl-6">
                        {cliente.name}
                      </td>
                      <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                        client
                      </td>
                      <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                        {getAdminName(cliente.admin_id)}
                      </td>
                      <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                        {cliente.max_users ?? '-'}
                      </td>
                      <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                        <button
                          on:click={() => openEditModal(cliente)}
                          class="text-indigo-600 hover:text-indigo-900 mr-4"
                        >
                          Editar
                        </button>
                        <button
                          on:click={() => deleteCliente(cliente)}
                          class="text-red-600 hover:text-red-900"
                        >
                          Eliminar
                        </button>
                      </td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    {/if}
  </main>
</div>

{#if showCreateModal}
  <!-- Overlay -->
  <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity z-40" on:click={resetModal}></div>
  <!-- Modal -->
  <div class="fixed z-50 inset-0 flex items-center justify-center">
    <div class="bg-white rounded-lg shadow-xl max-w-lg w-full p-6 relative" on:click|stopPropagation>
      <h3 class="text-lg leading-6 font-medium text-gray-900 mb-4">{editingCliente ? 'Editar Cliente' : 'Nuevo Cliente'}</h3>
      {#if error}
        <div class="text-red-500 text-center mb-2">{error}</div>
      {/if}
      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700">Nombre</label>
          <input type="text" bind:value={newCliente.name} class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700">Administrador</label>
          <select bind:value={newCliente.admin_id} class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm">
            <option value="">Seleccionar administrador</option>
            {#each admins as admin}
              <option value={admin.id}>{admin.email}</option>
            {/each}
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700">Máx. usuarios</label>
          <input type="number" min="1" bind:value={newCliente.max_users} class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm" />
        </div>
      </div>
      <div class="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse mt-6">
        <button type="button" on:click={saveCliente} class="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-indigo-600 text-base font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:ml-3 sm:w-auto sm:text-sm">{editingCliente ? 'Guardar' : 'Crear'}</button>
        <button type="button" on:click={resetModal} class="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm">Cancelar</button>
      </div>
    </div>
  </div>
{/if} 