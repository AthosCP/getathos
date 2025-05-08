<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import AdminNavbar from '$lib/AdminNavbar.svelte';

  type User = {
    id: string;
    email: string;
    role: string;
    status: string;
    created_at: string;
    last_login: string;
    tenant_id: string;
    tenant_name: string;
  };

  type Client = {
    id: string;
    name: string;
  };

  let users: User[] = [];
  let clients: Client[] = [];
  let loading = true;
  let error = '';
  let showCreateModal = false;
  let showEditModal = false;
  let selectedUser: User | null = null;
  let newUser = {
    email: '',
    password: '',
    role: 'user',
    tenant_id: ''
  };

  async function loadUsers() {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        goto('/login');
        return;
      }

      const response = await fetch('http://localhost:5001/api/admin/users', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      const data = await response.json();
      if (data.success) {
        users = data.data;
      } else {
        error = data.error || 'Error al cargar usuarios';
      }
    } catch (e) {
      error = 'Error de conexión';
    } finally {
      loading = false;
    }
  }

  async function loadClients() {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('http://localhost:5001/api/admin/clients', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      const data = await response.json();
      if (data.success) {
        clients = data.data.map((c: any) => ({ id: c.id, name: c.name }));
      }
    } catch (e) {
      console.error('Error al cargar clientes:', e);
    }
  }

  async function createUser() {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('http://localhost:5001/api/admin/users', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(newUser)
      });

      const data = await response.json();
      if (data.success) {
        users = [...users, data.data];
        showCreateModal = false;
        newUser = {
          email: '',
          password: '',
          role: 'user',
          tenant_id: ''
        };
      } else {
        error = data.error || 'Error al crear usuario';
      }
    } catch (e) {
      error = 'Error de conexión';
    }
  }

  async function updateUser() {
    if (!selectedUser) return;
    
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`http://localhost:5001/api/admin/users/${selectedUser.id}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(selectedUser)
      });

      const data = await response.json();
      if (data.success) {
        users = users.map(u => u.id === selectedUser.id ? data.data : u);
        showEditModal = false;
      } else {
        error = data.error || 'Error al actualizar usuario';
      }
    } catch (e) {
      error = 'Error de conexión';
    }
  }

  async function deleteUser(id: string) {
    if (!confirm('¿Estás seguro de que deseas eliminar este usuario?')) return;

    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`http://localhost:5001/api/admin/users/${id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      const data = await response.json();
      if (data.success) {
        users = users.filter(u => u.id !== id);
      } else {
        error = data.error || 'Error al eliminar usuario';
      }
    } catch (e) {
      error = 'Error de conexión';
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
    loadUsers();
    loadClients();
  });
</script>

<AdminNavbar active="users" />

<div class="min-h-screen bg-gray-100">
  <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
    <div class="px-4 sm:px-0">
      <div class="flex justify-between items-center">
        <h1 class="text-2xl font-bold text-gray-900">Gestión de Usuarios</h1>
        <button
          on:click={() => showCreateModal = true}
          class="px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700"
        >
          Nuevo Usuario
        </button>
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
                    <th scope="col" class="py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900 sm:pl-6">Email</th>
                    <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Rol</th>
                    <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Cliente</th>
                    <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Estado</th>
                    <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Último Acceso</th>
                    <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Acciones</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-200 bg-white">
                  {#each users as user}
                    <tr>
                      <td class="whitespace-nowrap py-4 pl-4 pr-3 text-sm font-medium text-gray-900 sm:pl-6">
                        {user.email}
                      </td>
                      <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                        {user.role === 'admin' ? 'Administrador' : user.role === 'client' ? 'Cliente' : 'Usuario'}
                      </td>
                      <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500">{user.tenant_name}</td>
                      <td class="whitespace-nowrap px-3 py-4 text-sm">
                        <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full {user.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}">
                          {user.status === 'active' ? 'Activo' : 'Pendiente'}
                        </span>
                      </td>
                      <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                        {user.last_login ? new Date(user.last_login).toLocaleString() : 'Nunca'}
                      </td>
                      <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                        <button
                          on:click={() => { selectedUser = user; showEditModal = true; }}
                          class="text-indigo-600 hover:text-indigo-900 mr-4"
                        >
                          Editar
                        </button>
                        <button
                          on:click={() => deleteUser(user.id)}
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
  <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity z-40" on:click={() => { showCreateModal = false; error = ''; }}></div>
  <!-- Modal -->
  <div class="fixed z-50 inset-0 flex items-center justify-center">
    <div class="bg-white rounded-lg shadow-xl max-w-lg w-full p-6 relative" on:click|stopPropagation>
      <h3 class="text-lg leading-6 font-medium text-gray-900 mb-4">Nuevo Usuario</h3>
      {#if error}
        <div class="text-red-500 text-center mb-2">{error}</div>
      {/if}
      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700">Email</label>
          <input type="email" bind:value={newUser.email} class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700">Contraseña</label>
          <input type="password" bind:value={newUser.password} class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700">Rol</label>
          <select bind:value={newUser.role} class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm">
            <option value="user">Usuario</option>
            <option value="client">Cliente</option>
            <option value="admin">Administrador</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700">Cliente</label>
          <select bind:value={newUser.tenant_id} class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm">
            <option value="">Seleccionar cliente</option>
            {#each clients as client}
              <option value={client.id}>{client.name}</option>
            {/each}
          </select>
        </div>
      </div>
      <div class="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse mt-6">
        <button type="button" on:click={createUser} class="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-indigo-600 text-base font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:ml-3 sm:w-auto sm:text-sm">Crear</button>
        <button type="button" on:click={() => { showCreateModal = false; error = ''; }} class="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm">Cancelar</button>
      </div>
    </div>
  </div>
{/if}

{#if showEditModal && selectedUser}
  <div class="fixed z-10 inset-0 overflow-y-auto">
    <div class="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
      <div class="fixed inset-0 transition-opacity" aria-hidden="true">
        <div class="absolute inset-0 bg-gray-500 opacity-75"></div>
      </div>
      <div class="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
        <div class="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
          <h3 class="text-lg leading-6 font-medium text-gray-900 mb-4">
            Editar Usuario
          </h3>
          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700">Email</label>
              <input
                type="email"
                bind:value={selectedUser.email}
                disabled
                class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 bg-gray-50 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700">Rol</label>
              <select
                bind:value={selectedUser.role}
                class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              >
                <option value="user">Usuario</option>
                <option value="client">Cliente</option>
                <option value="admin">Administrador</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700">Cliente</label>
              <select
                bind:value={selectedUser.tenant_id}
                class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              >
                <option value="">Seleccionar cliente</option>
                {#each clients as client}
                  <option value={client.id}>{client.name}</option>
                {/each}
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700">Estado</label>
              <select
                bind:value={selectedUser.status}
                class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              >
                <option value="active">Activo</option>
                <option value="pending">Pendiente</option>
              </select>
            </div>
          </div>
        </div>
        <div class="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
          <button
            type="button"
            on:click={updateUser}
            class="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-indigo-600 text-base font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:ml-3 sm:w-auto sm:text-sm"
          >
            Guardar
          </button>
          <button
            type="button"
            on:click={() => showEditModal = false}
            class="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
          >
            Cancelar
          </button>
        </div>
      </div>
    </div>
  </div>
{/if} 