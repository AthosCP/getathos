<script>
  import { page } from '$app/stores';
</script>

<div class="min-h-screen flex items-center justify-center bg-gray-50">
  <div class="max-w-md w-full space-y-8 p-8">
    <div class="text-center">
      <h1 class="text-4xl font-bold text-red-600 mb-4">
        {$page.status}
      </h1>
      <p class="text-gray-600 text-lg">
        {$page.error?.message || 'Ha ocurrido un error'}
      </p>
      <a href="/" class="mt-4 inline-block text-indigo-600 hover:text-indigo-500">
        Volver al inicio
      </a>
    </div>
  </div>
</div> 