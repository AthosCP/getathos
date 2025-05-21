<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { auth } from '$lib/auth';

  export let active: string = 'dashboard';
  export let links: { label: string; href: string; id: string }[] = [
    { label: 'Dashboard', href: '/dashboard', id: 'dashboard' },
    { label: 'Usuarios', href: '/users', id: 'users' },
    { label: 'Políticas', href: '/policies', id: 'policies' },
    { label: 'Navegación', href: '/navigation', id: 'navigation' },
    { label: 'Alertas', href: '/alerts', id: 'alerts' }
  ];

  let isProfileMenuOpen = false;
  let userEmail = '';

  onMount(() => {
    const userRaw = localStorage.getItem('user');
    if (userRaw) {
      const user = JSON.parse(userRaw);
      userEmail = user.email;
    }
  });

  function toggleProfileMenu() {
    isProfileMenuOpen = !isProfileMenuOpen;
  }

  function handleLogout() {
    auth.logout();
    goto('/login', { replaceState: true });
  }

  // Cerrar el menú cuando se hace click fuera
  function handleClickOutside(event: MouseEvent) {
    const target = event.target as HTMLElement;
    if (!target.closest('.profile-menu')) {
      isProfileMenuOpen = false;
    }
  }

  onMount(() => {
    document.addEventListener('click', handleClickOutside);
    return () => {
      document.removeEventListener('click', handleClickOutside);
    };
  });
</script>

<nav class="bg-black shadow-sm mb-0">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div class="flex justify-between h-16 items-center">
      <div class="flex items-center">
        <div class="flex-shrink-0 flex items-center">
          <a href="/dashboard" class="flex items-center">
            <!-- Typo logo con efecto glow -->
            <img 
              src="/images/typo.png" 
              alt="Athos" 
              class="h-32 w-auto glow-effect -my-8"
              style="filter: drop-shadow(0 0 10px #00a1ff);"
            />
          </a>
        </div>
        <div class="ml-6 flex h-16">
          {#each links as link}
            <a
              href={link.href}
              class="inline-flex items-center px-4 h-full {active === link.id ? 'border-b-2 border-[#00a1ff] text-[#00a1ff] font-bold bg-black' : 'border-b-2 border-transparent text-gray-300 hover:text-white'}"
            >
              {link.label}
            </a>
          {/each}
        </div>
      </div>
      <div class="flex items-center space-x-4">
        <!-- Profile dropdown -->
        <div class="relative profile-menu">
          <button
            type="button"
            class="text-[#3b4dff] hover:text-white focus:outline-none p-2 hidden sm:block"
            title="Perfil de Usuario"
            on:click={toggleProfileMenu}
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
          </button>

          {#if isProfileMenuOpen}
            <div
              class="origin-top-right absolute right-0 mt-2 w-56 rounded-md shadow-lg py-1 bg-black border border-[#3b4dff] ring-1 ring-[#3b4dff] ring-opacity-5 focus:outline-none z-50"
              role="menu"
              aria-orientation="vertical"
              aria-labelledby="user-menu-button"
              tabindex="-1"
            >
              <div class="px-4 py-3 text-sm text-gray-300 border-b border-[#3b4dff]">
                <span class="block text-xs text-[#3b4dff] mb-1">Usuario actual</span>
                <span class="block truncate">{userEmail}</span>
              </div>
              <a
                href="#"
                class="block px-4 py-2 text-sm text-gray-500 cursor-not-allowed opacity-50"
                role="menuitem"
                tabindex="-1"
                on:click|preventDefault={() => {}}
              >
                <div class="flex items-center">
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                  </svg>
                  Cambiar contraseña
                </div>
              </a>
              <button
                on:click={handleLogout}
                class="block w-full text-left px-4 py-2 text-sm text-gray-300 hover:bg-[#1a1a1a] hover:text-white transition-colors duration-150"
                role="menuitem"
                tabindex="-1"
              >
                <div class="flex items-center">
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                  </svg>
                  Cerrar sesión
                </div>
              </button>
            </div>
          {/if}
        </div>
      </div>
    </div>
  </div>
</nav>

<style>
  .glow-effect {
    filter: drop-shadow(0 0 10px rgba(0, 161, 255, 0.8));
  }
  .profile-menu {
    position: relative;
  }
</style> 