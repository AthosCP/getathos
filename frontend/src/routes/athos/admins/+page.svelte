<script lang="ts">
  import { onMount } from 'svelte';
  import { API_URL } from '$lib/config';

  type Admin = {
    id?: string;
    name: string;
    email: string;
    role: string;
    max_clients?: number;
    password?: string;
    tenant_id?: string;
  };
  type Cliente = {
    id?: string;
    admin_id?: string;
  };

  type Tenant = {
    id?: string;
    name: string;
    description?: string;
    max_users?: number;
    status?: string;
  };

  let showCreateModal = false;
  let editingAdmin: Admin | null = null;
  let admins: Admin[] = [];
  let clientes: Cliente[] = [];
  let newAdmin: Admin = {
    name: '',
    email: '',
    role: 'admin',
    password: '',
    max_clients: 10
  };

  let error = '';
  let loading = false;

  async function fetchAdmins() {
    loading = true;
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_URL}/api/athos/admins`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      if (data.success) admins = data.data;
      else error = data.error || 'Error al cargar admins';
    } catch (e) {
      error = 'Error de conexión';
    } finally {
      loading = false;
    }
  }

  async function fetchClientes() {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_URL}/api/athos/clientes`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      if (data.success) clientes = data.data;
    } catch (e) {}
  }

  onMount(async () => {
    await fetchAdmins();
    await fetchClientes();
  });

  function openCreateModal() {
    editingAdmin = null;
    newAdmin = { name: '', email: '', role: 'admin', password: '', max_clients: 10 };
    error = '';
    showCreateModal = true;
  }

  function openEditModal(admin: Admin) {
    editingAdmin = admin;
    newAdmin = { ...admin };
    error = '';
    showCreateModal = true;
  }

  function resetModal() {
    showCreateModal = false;
    editingAdmin = null;
    newAdmin = { name: '', email: '', role: 'admin', password: '', max_clients: 10 };
    error = '';
  }

  async function createTenant() {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_URL}/api/athos/clientes`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(newTenant)
      });
      const data = await res.json();
      if (data.success) {
        return data.data.id;
      } else {
        error = data.error || 'Error al crear tenant';
        return null;
      }
    } catch (e) {
      error = 'Error de conexión';
      return null;
    }
  }

  async function saveAdmin() {
    error = '';
    const token = localStorage.getItem('token');
    try {
      // Solo crear el admin, el backend se encarga del resto
      const adminData = {
        ...newAdmin
      };
      const res = await fetch(`${API_URL}/api/athos/admins`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(adminData)
      });
      const data = await res.json();
      if (data.success) {
        await fetchAdmins();
        resetModal();
      } else {
        error = data.error || 'Error al guardar admin';
      }
    } catch (e) {
      error = 'Error de conexión';
    }
  }

  async function deleteAdmin(admin: Admin) {
    if (!confirm('¿Seguro que deseas eliminar este admin?')) return;
    const token = localStorage.getItem('token');
    try {
      const res = await fetch(`${API_URL}/api/athos/admins/${admin.id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      if (data.success) await fetchAdmins();
      else error = data.error || 'Error al eliminar admin';
    } catch (e) {
      error = 'Error de conexión';
    }
  }

  function countClientes(adminId: string) {
    return clientes.filter(c => c.admin_id === adminId).length;
  }
</script>

<div class="min-h-screen bg-gray-100">
  <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
    <div class="px-4 sm:px-0">
      <div class="flex justify-between items-center">
        <h1 class="text-2xl font-bold text-gray-900">Administradores</h1>
        <button
          on:click={openCreateModal}
          class="px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700"
        >
          Nuevo Admin
        </button>
      </div>
    </div>
    {#if loading}
      <div class="text-center mt-8">Cargando...</div>
    {:else}
      <div class="mt-8 flex flex-col">
        <div class="-my-2 -mx-4 overflow-x-auto sm:-mx-6 lg:-mx-8">
          <div class="inline-block min-w-full py-2 align-middle md:px-6 lg:px-8">
            <div class="overflow-hidden shadow ring-1 ring-black ring-opacity-5 md:rounded-lg">
              <table class="min-w-full divide-y divide-gray-300">
                <thead class="bg-gray-50">
                  <tr>
                    <th scope="col" class="py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900 sm:pl-6">Email</th>
                    <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Rol</th>
                    <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Clientes asignados</th>
                    <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Máx. clientes</th>
                    <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Acciones</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-200 bg-white">
                  {#each admins as admin}
                    <tr>
                      <td class="whitespace-nowrap py-4 pl-4 pr-3 text-sm font-medium text-gray-900 sm:pl-6">{admin.email}</td>
                      <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500">{admin.role}</td>
                      <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500">{countClientes(admin.id || '')}</td>
                      <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500">{admin.max_clients ?? '-'}</td>
                      <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                        <button class="text-indigo-600 hover:text-indigo-900 mr-2" on:click={() => openEditModal(admin)}>Editar</button>
                        <button class="text-red-600 hover:text-red-900" on:click={() => deleteAdmin(admin)}>Eliminar</button>
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
    <div class="bg-white rounded-lg shadow-xl max-w-md w-full p-6 relative" on:click|stopPropagation>
      <h3 class="text-lg leading-6 font-medium text-gray-900 mb-4">{editingAdmin ? 'Editar Administrador' : 'Nuevo Administrador'}</h3>
      {#if error}
        <div class="text-red-500 text-center mb-2">{error}</div>
      {/if}
      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700">Email del Admin</label>
          <input type="email" bind:value={newAdmin.email} class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700">Contraseña</label>
          <input type="password" bind:value={newAdmin.password} class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700">Máx. clientes</label>
          <input type="number" min="1" bind:value={newAdmin.max_clients} class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm" />
        </div>
      </div>
      <div class="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse mt-6">
        <button type="button" on:click={saveAdmin} class="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-indigo-600 text-base font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:ml-3 sm:w-auto sm:text-sm">{editingAdmin ? 'Guardar' : 'Crear'}</button>
        <button type="button" on:click={resetModal} class="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm">Cancelar</button>
      </div>
    </div>
  </div>
{/if} 