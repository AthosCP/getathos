<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import Navbar from '$lib/Navbar.svelte';

  interface User {
    id: string;
    email: string;
    role: string;
    status: string;
    created_at: string;
    last_login: string;
    tenant_id: string;
  }

  let users: User[] = [];
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

      const response = await fetch('http://localhost:5001/api/users', {
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

  async function createUser() {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('http://localhost:5001/api/users', {
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
      const response = await fetch(`http://localhost:5001/api/users/${selectedUser.id}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(selectedUser)
      });

      const data = await response.json();
      if (data.success) {
        users = users.map(u => u.id === selectedUser?.id ? data.data : u);
        showEditModal = false;
        selectedUser = null;
      } else {
        error = data.error || 'Error al actualizar usuario';
      }
    } catch (e) {
      error = 'Error de conexión';
    }
  }

  async function deleteUser(userId: string) {
    if (!confirm('¿Estás seguro de que deseas eliminar este usuario?')) return;

    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`http://localhost:5001/api/users/${userId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      const data = await response.json();
      if (data.success) {
        users = users.filter(u => u.id !== userId);
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
    loadUsers();
  });
</script>

<Navbar active="users" />

<div class="min-h-screen bg-gray-100">
  <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
    {#if loading}
      <div class="text-center">Cargando...</div>
    {:else if error}
      <div class="text-red-500 text-center">{error}</div>
    {:else}
      <div class="flex justify-between items-center mb-4">
        <h2 class="text-2xl font-bold">Mis Usuarios Asegurados</h2>
        <button
          on:click={() => showCreateModal = true}
          class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
        >
          Crear Nuevo Usuario
        </button>
      </div>
      <div class="bg-white shadow overflow-hidden sm:rounded-lg">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Email
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Rol
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Estado
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Acciones
              </th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            {#each users as user}
              <tr>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {user.email}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {user.role}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {user.status}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                  <button
                    on:click={() => {
                      selectedUser = { ...user };
                      showEditModal = true;
                    }}
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
    {/if}
  </main>
</div>

{#if showCreateModal}
  <div class="fixed z-10 inset-0 overflow-y-auto">
    <div class="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
      <div class="fixed inset-0 transition-opacity" aria-hidden="true" on:click={() => showCreateModal = false}>
        <div class="absolute inset-0 bg-gray-500 opacity-75"></div>
      </div>
      <div class="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full relative">
        <button
          class="absolute top-2 right-2 text-gray-400 hover:text-gray-600 text-2xl font-bold focus:outline-none"
          on:click={() => showCreateModal = false}
          aria-label="Cerrar"
        >
          ×
        </button>
        <div class="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
          <h3 class="text-lg leading-6 font-medium text-gray-900 mb-4">
            Crear Nuevo Usuario
          </h3>
          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700">Email</label>
              <input
                type="email"
                bind:value={newUser.email}
                class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700">Contraseña</label>
              <input
                type="password"
                bind:value={newUser.password}
                class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700">Rol</label>
              <select
                bind:value={newUser.role}
                class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              >
                <option value="user">Usuario</option>
                <option value="admin">Administrador</option>
              </select>
            </div>
          </div>
        </div>
        <div class="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
          <button
            on:click={createUser}
            class="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-indigo-600 text-base font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:ml-3 sm:w-auto sm:text-sm"
          >
            Crear
          </button>
          <button
            on:click={() => showCreateModal = false}
            class="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
          >
            Cancelar
          </button>
        </div>
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
                <option value="admin">Administrador</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700">Estado</label>
              <select
                bind:value={selectedUser.status}
                class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              >
                <option value="active">Activo</option>
                <option value="inactive">Inactivo</option>
              </select>
            </div>
          </div>
        </div>
        <div class="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
          <button
            on:click={updateUser}
            class="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-indigo-600 text-base font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:ml-3 sm:w-auto sm:text-sm"
          >
            Guardar
          </button>
          <button
            on:click={() => {
              showEditModal = false;
              selectedUser = null;
            }}
            class="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
          >
            Cancelar
          </button>
        </div>
      </div>
    </div>
  </div>
{/if} 