<template>
  <router-view />
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'

function handleKeydown(e: KeyboardEvent) {
  // Ctrl+K / Cmd+K: focus search box
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault()
    const searchInput = document.querySelector('.header-search input, .hero-search-input input') as HTMLInputElement
    if (searchInput) searchInput.focus()
  }
}

onMounted(() => document.addEventListener('keydown', handleKeydown))
onUnmounted(() => document.removeEventListener('keydown', handleKeydown))
</script>
